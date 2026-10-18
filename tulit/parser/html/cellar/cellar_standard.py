from tulit.parser.html.html_parser import HTMLParser
import re
from tulit.parser.parser import LegalJSONValidator, create_html_normalizer
from tulit.parser.strategies.article_extraction import CellarStandardArticleStrategy

# Closing formula of a regulation, after its last article
_BINDING_FORMULA = 'This Regulation shall be binding in its entirety'


class CellarStandardHTMLParser(HTMLParser):
    """
    Parser for standard HTML format documents from EU Cellar.
    This format wraps content in <TXT_TE> tags with simple <p> structure,
    unlike the semantic XHTML format with class-based structure.
    """

    def __init__(self) -> None:
        super().__init__()
        # Use HTML-specific normalizer for consolidation markers
        self.normalizer = create_html_normalizer()
        # Initialize article extraction strategy
        self.article_strategy = CellarStandardArticleStrategy()

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content using strategy pattern."""
        return self.normalizer.normalize(text)

    def _extract_article_number(self, text):
        """
        Extract article number from text like 'Article 1' or 'Article 2'.
        Returns (article_num, remaining_text) or (None, text) if not found.
        """
        match = re.match(r'^Article\s+(\d+)\s*(.*)$', text, re.IGNORECASE)
        if match:
            return match.group(1), match.group(2)
        return None, text

    def get_preface(self) -> None:
        """
        Extract document title/preface.
        In standard HTML, this is typically in the metadata or first heading.
        """
        try:
            # Prefer the document's own title block: the paragraphs before
            # the enacting-authority formula ('THE COUNCIL …,')
            txt_te = self.root.find('txt_te') or self.root.find(
                lambda tag: tag.name and tag.name.upper() == 'TXT_TE')
            if txt_te:
                title_lines = []
                for p in txt_te.find_all('p')[:10]:
                    text = self._clean_text(p.get_text())
                    if not text:
                        continue
                    if re.match(r'^(THE [A-Z]|Having\s)', text):
                        break
                    title_lines.append(text)
                if title_lines:
                    self.preface = ' '.join(title_lines)
                    self._preface_texts = set(title_lines)
                    self.logger.info("Preface extracted from title block.")
                    return

            # Try to find in meta description
            meta_desc = self.root.find('meta', attrs={'name': 'DC.description'})
            if meta_desc and meta_desc.get('content'):
                self.preface = meta_desc.get('content').strip()
                self.logger.info("Preface extracted from meta description.")
                return

            # Try to find in h1 or strong tags
            h1 = self.root.find('h1')
            if h1:
                self.preface = self._clean_text(h1.get_text())
                self.logger.info("Preface extracted from h1.")
                return

            # Fallback to first strong tag
            strong = self.root.find('strong')
            if strong:
                self.preface = self._clean_text(strong.get_text())
                self.logger.info("Preface extracted from strong tag.")
                return

            self.preface = None
            self.logger.warning("No preface found.")
        except Exception as e:
            self.preface = None
            self.logger.error(f"Error extracting preface: {e}")

    def get_preamble(self) -> None:
        """
        Extract preamble content.

        This parser is specifically designed for EU Cellar Standard HTML format
        with TXT_TE tags. Files without TXT_TE tags are not supported and will
        cause the parser to fail.

        Raises:
            ValueError: If no TXT_TE tag is found in the document.
        """
        try:
            # Find the TXT_TE container (case-insensitive)
            txt_te = self.root.find('txt_te')
            if not txt_te:
                # Try uppercase
                txt_te = self.root.find(lambda tag: tag.name and tag.name.upper() == 'TXT_TE')

            if txt_te:
                # Standard HTML format with TXT_TE
                self.txt_te = txt_te
                self.preamble = txt_te
                self.is_consolidated = False
                self.logger.info("Preamble container found (standard format with TXT_TE).")
            else:
                # No TXT_TE found - this parser cannot handle this format
                error_msg = (
                    "No TXT_TE tag found. CellarStandardHTMLParser is designed specifically "
                    "for EU Cellar Standard HTML format with TXT_TE tags. "
                    "Use a different parser for this document format."
                )
                self.logger.error(error_msg)
                raise ValueError(error_msg)

        except ValueError:
            # Re-raise ValueError to signal unsupported format
            raise
        except Exception as e:
            self.preamble = None
            self.logger.error(f"Error extracting preamble: {e}")
            raise

    def get_formula(self) -> None:
        """
        Extract the formula (decision-making body statement).
        Usually starts with "THE COUNCIL", "THE COMMISSION", etc.
        """
        try:
            if not hasattr(self, 'txt_te') or not self.txt_te:
                self.formula = None
                return

            paragraphs = self.txt_te.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                # Look for common formula patterns
                if re.match(r'^(THE (COUNCIL|COMMISSION|EUROPEAN PARLIAMENT)|HAS ADOPTED)', text, re.IGNORECASE):
                    self.formula = self._clean_text(text)
                    self.logger.info(f"Formula extracted: {self.formula[:50]}...")
                    return

            self.formula = None
            self.logger.warning("No formula found.")
        except Exception as e:
            self.formula = None
            self.logger.error(f"Error extracting formula: {e}")

    def get_citations(self):
        """
        Extract citations (legal references).
        Usually contains phrases like "Having regard to".
        """
        try:
            if not hasattr(self, 'txt_te') or not self.txt_te:
                self.citations = []
                return

            self.citations = []
            paragraphs = self.txt_te.find_all('p')
            citation_idx = 0

            citation_re = re.compile(
                r'^(Having\s+\w+|Acting in accordance|After consult\w*|'
                r'In cooperation with|With the approval of|After approval|'
                r'In agreement with)', re.IGNORECASE)
            for p in paragraphs:
                text = self._clean_text(p.get_text())
                # citations live in the preamble only — stop at the final
                # formula or the first article
                if self._is_recitals_end(text):
                    break
                if citation_re.match(text):
                    citation_idx += 1
                    self.citations.append({
                        'eId': f'cit_{citation_idx}',
                        'text': text
                    })

            self.logger.info(f"Extracted {len(self.citations)} citations.")
        except Exception as e:
            self.citations = []
            self.logger.error(f"Error extracting citations: {e}")

    def _extract_table_recital(self, num_text: str, content_text: str):
        """Extract recital from table row if format matches."""
        if re.match(r'^\(?\d+\)?$', num_text):
            recital_num = re.sub(r'[()]', '', num_text)
            return {
                'eId': f'rct_{recital_num}',
                'text': content_text
            }
        return None

    def _extract_recitals_from_tables(self):
        """Extract recitals from table format."""
        recitals = []
        tables = self.txt_te.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) == 2:
                    num_text = self._clean_text(cols[0].get_text())
                    content_text = self._clean_text(cols[1].get_text())

                    recital = self._extract_table_recital(num_text, content_text)
                    if recital:
                        recitals.append(recital)
        return recitals

    def _is_recitals_start(self, text: str) -> bool:
        """Check if text marks start of recitals section."""
        return text.strip() == 'Whereas:'

    def _is_recitals_end(self, text: str) -> bool:
        """Check if text marks end of recitals section."""
        return bool(re.match(r'^(HAS ADOPTED|HAS DECIDED|HAVE ADOPTED|'
                             r'HAVE DECIDED|HAS AGREED|HAVE AGREED|Article|'
                             r'Sole Article|Done at)', text, re.IGNORECASE))

    def _extract_numbered_recital(self, text: str):
        """Extract numbered recital from text like '(1) Some text'."""
        match = re.match(r'^\((\d+)\)\s*(.+)$', text)
        if match:
            return {
                'eId': f'rct_{match.group(1)}',
                'text': match.group(2)
            }
        return None

    def _extract_recitals_from_paragraphs(self):
        """Extract recitals from paragraph format: 'Whereas:' followed by
        numbered '(N)' items, or (older acts) bare 'Whereas …' paragraphs.
        Unmarked lines inside the whereas block continue the previous
        recital."""
        recitals = []
        paragraphs = self.txt_te.find_all('p')
        in_recitals = False
        seen_preamble = False

        formula_re = re.compile(r'^THE [A-Z][A-Z ,]+,?$')
        citation_re = re.compile(r'^(Having\s+\w+|Acting in accordance|'
                                 r'After consult\w*|In cooperation with)',
                                 re.IGNORECASE)
        for p in paragraphs:
            text = self._clean_text(p.get_text())
            if not text:
                continue

            if self._is_recitals_start(text):
                in_recitals = True
                self.recitals_intro = text
                continue

            if in_recitals and self._is_recitals_end(text):
                break

            if not in_recitals and (formula_re.match(text) or citation_re.match(text)):
                seen_preamble = True
                continue

            bare = re.match(r'^Whereas[,:]?\s+(.+)$', text, re.DOTALL)
            if bare and not in_recitals:
                in_recitals = True
                recitals.append({'eId': f'rct_{len(recitals) + 1}',
                                 'text': bare.group(1).strip()})
                continue

            # decisions with narrative reasoning open the recitals with
            # '(1) …' directly, without any Whereas marker
            if not in_recitals and seen_preamble and re.match(r'^\(\d+\)\s', text):
                in_recitals = True

            if in_recitals:
                recital = self._extract_numbered_recital(text)
                if recital is None and bare:
                    recital = {'eId': f'rct_{len(recitals) + 1}',
                               'text': bare.group(1).strip()}
                if recital:
                    recitals.append(recital)
                elif recitals:
                    # continuation of the previous recital
                    recitals[-1]['text'] += '\n' + text
                else:
                    recitals.append({'eId': f'rct_{len(recitals) + 1}',
                                     'text': text})

        return recitals

    def get_recitals(self):
        """
        Extract recitals (whereas clauses).
        Usually starts with "Whereas:" followed by numbered items.
        """
        try:
            if not hasattr(self, 'txt_te') or not self.txt_te:
                self.recitals = []
                return

            self.recitals = self._extract_recitals_from_tables()

            if not self.recitals:
                self.recitals = self._extract_recitals_from_paragraphs()

            self.logger.info(f"Extracted {len(self.recitals)} recitals.")
        except Exception as e:
            self.recitals = []
            self.logger.error(f"Error extracting recitals: {e}")

    def get_preamble_final(self):
        """
        Extract final preamble statement (e.g., "HAS ADOPTED THIS DECISION:").
        """
        try:
            if not hasattr(self, 'txt_te') or not self.txt_te:
                self.preamble_final = None
                return

            paragraphs = self.txt_te.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                if re.match(r'^HAS (ADOPTED|DECIDED)', text, re.IGNORECASE):
                    self.preamble_final = self._clean_text(text)
                    self.logger.info("Preamble final extracted.")
                    return

            self.preamble_final = None
            self.logger.warning("No preamble final found.")
        except Exception as e:
            self.preamble_final = None
            self.logger.error(f"Error extracting preamble final: {e}")

    def get_body(self):
        """
        The body is the TXT_TE container itself.
        """
        try:
            if hasattr(self, 'txt_te'):
                self.body = self.txt_te
                self.logger.info("Body set to TXT_TE container.")
            else:
                self.body = None
                self.logger.warning("No body found.")
        except Exception as e:
            self.body = None
            self.logger.error(f"Error getting body: {e}")

    def get_chapters(self):
        """
        Extract chapters. In standard HTML, these might be section headings.
        For most documents, this may not apply.
        """
        # Standard HTML typically doesn't have explicit chapter structure
        self.chapters = []
        self.logger.info("Chapter extraction not applicable for standard HTML format.")

    def get_articles(self):
        """
        Extract articles from the document using CellarStandardArticleStrategy.

        This method delegates article extraction to the strategy pattern,
        reducing code duplication and improving testability.
        """
        try:
            if not hasattr(self, 'txt_te') or not self.txt_te:
                self.articles = []
                self.logger.warning("No container found for article extraction.")
                return

            # Use strategy for extraction. Only 'Done at' reliably marks
            # the signature: 'For the …' / 'Brussels,' openings also occur
            # in ordinary article prose and would truncate extraction
            self.articles = self.article_strategy.extract_articles(
                self.txt_te,
                stop_markers=['Done at', _BINDING_FORMULA]
            )

            self.logger.info(f"Extracted {len(self.articles)} articles.")

        except Exception as e:
            self.articles = []
            self.logger.error(f"Error extracting articles: {e}")

    def _process_article_start_standard(self, text: str, current_article, article_content):
        """Process start of new article in standard format."""
        article_num, remaining = self._extract_article_number(text)

        if article_num:
            if current_article:
                self._finalize_article(current_article, article_content)
                article_content.clear()

            current_article = {
                'eId': f'art_{article_num}',
                'num': f'Article {article_num}',
                'heading': remaining if remaining else None,
                'children': []
            }

        return current_article, article_content

    def _process_article_content_standard(self, text: str, current_article, article_content):
        """Process article content in standard format."""
        if self._should_stop_processing(text):
            if current_article:
                self._finalize_article(current_article, article_content)
            return None, True

        if text:
            article_content.append(text)

        return current_article, False

    def _extract_articles_standard(self):
        """Extract articles from standard HTML format (with TXT_TE tags)."""
        elements = self.txt_te.find_all(['p', 'table'], recursive=False)
        current_article = None
        article_content = []

        for element in elements:
            if element.name == 'table':
                self._process_table_element(element, current_article, article_content)
                continue

            text = self._clean_text(element.get_text())
            article_num, _ = self._extract_article_number(text)

            if article_num:
                current_article, article_content = self._process_article_start_standard(
                    text, current_article, article_content
                )
            elif current_article:
                current_article, should_break = self._process_article_content_standard(
                    text, current_article, article_content
                )
                if should_break:
                    break
            else:
                if self._should_stop_processing(text):
                    break

        if current_article:
            self._finalize_article(current_article, article_content)

    def _extract_table_text(self, table):
        """Extract text content from a table element."""
        rows = []
        for row in table.find_all('tr'):
            cells = [self._clean_text(cell.get_text()) for cell in row.find_all(['td', 'th'])]
            if any(cells):  # Only add non-empty rows
                rows.append(' | '.join(cells))
        return '\n'.join(rows) if rows else None

    def _is_signature_section(self, text):
        """Check if text is part of signature/conclusion section."""
        if not text:
            return False
        # Common signature patterns
        signature_patterns = [
            r'^Done at',
            r'^For the (Commission|Council|European Parliament)',
            r'^Member of the Commission',
            r'^President of the (Council|Commission|European Parliament)',
            r'^The President',
            r'^Brussels,',
        ]
        return any(re.match(pattern, text, re.IGNORECASE) for pattern in signature_patterns)

    def _is_footnote(self, text):
        """Check if text is a footnote reference."""
        if not text:
            return False
        # Footnotes typically start with (1), (2), etc. and contain OJ references
        return bool(re.match(r'^\(\d+\)\s+OJ\s+[A-Z]', text))

    def _is_article_number_style(self, style: str) -> bool:
        """Check if style indicates article number (italic, centered)."""
        return 'italic' in style and 'center' in style

    def _is_heading_style(self, style: str) -> bool:
        """Check if style indicates article heading (bold, centered)."""
        return 'bold' in style and 'center' in style

    def _process_table_element(self, element, current_article, article_content):
        """Process table element and add to article content."""
        if current_article:
            table_text = self._extract_table_text(element)
            if table_text:
                article_content.append(f"[TABLE]\n{table_text}")

    def _extract_article_heading(self, elements, current_index: int):
        """Extract article heading from next element if present."""
        if current_index + 1 < len(elements):
            next_elem = elements[current_index + 1]
            if next_elem.name == 'p':
                next_style = next_elem.get('style', '')
                if self._is_heading_style(next_style):
                    return self._clean_text(next_elem.get_text())
        return None

    def _create_new_article(self, article_num: str, heading: str):
        """Create new article dictionary."""
        return {
            'eId': f'art_{article_num}',
            'num': f'Article {article_num}',
            'heading': heading,
            'children': []
        }

    def _should_stop_processing(self, text: str) -> bool:
        """Check if text indicates end of articles section."""
        return self._is_signature_section(text) or self._is_footnote(text)

    def _process_article_content(self, text: str, style: str, current_article, article_content):
        """Process paragraph as article content."""
        if current_article['heading'] and text == current_article['heading']:
            return

        if text and 'center' not in style and 'italic' not in style:
            article_content.append(text)

    def _extract_articles_consolidated(self):
        """Extract articles from consolidated HTML format (styled paragraphs)."""
        elements = self.txt_te.find_all(['p', 'table'], recursive=False)
        current_article = None
        article_content = []

        for i, element in enumerate(elements):
            if element.name == 'table':
                self._process_table_element(element, current_article, article_content)
                continue

            text = self._clean_text(element.get_text())
            style = element.get('style', '')

            if self._is_article_number_style(style):
                article_num, remaining = self._extract_article_number(text)

                if article_num:
                    if current_article:
                        self._finalize_article(current_article, article_content)
                        article_content = []

                    heading = self._extract_article_heading(elements, i)
                    current_article = self._create_new_article(article_num, heading)

            elif current_article:
                if self._should_stop_processing(text):
                    self._finalize_article(current_article, article_content)
                    current_article = None
                    break

                self._process_article_content(text, style, current_article, article_content)
            else:
                if self._should_stop_processing(text):
                    break

        if current_article:
            self._finalize_article(current_article, article_content)

    def _finalize_article(self, article, paragraphs):
        """
        Process collected paragraphs for an article and add to articles list.
        Paragraphs are kept separate, but points within a paragraph are combined.
        """
        if not paragraphs:
            # No content paragraphs
            self.articles.append(article)
            return

        # If first paragraph looks like a title (short and no ending punctuation), use it as heading
        if len(paragraphs) > 0 and len(paragraphs[0]) < 100 and not paragraphs[0][-1] in '.!?':
            if not article['heading']:
                article['heading'] = paragraphs[0]
                paragraphs = paragraphs[1:]

        # Extract article number from eId (format: art_1 -> 1)
        article_num_match = re.search(r'art_(\d+)', article['eId'])
        article_num = int(article_num_match.group(1)) if article_num_match else 0

        # Group paragraphs: combine consecutive lettered/roman points, but keep numbered paragraphs separate
        grouped_paragraphs = []
        current_group = []

        for para_text in paragraphs:
            # Check if this is a lettered point: (a), (b), (c) or roman numerals: (i), (ii), (iii)
            is_letter_point = bool(re.match(r'^\s*\([a-z]\)\s+', para_text, re.IGNORECASE))
            is_roman_point = bool(re.match(r'^\s*\([ivxlcdm]+\)\s+', para_text, re.IGNORECASE))

            if (is_letter_point or is_roman_point) and current_group:
                # This is a continuation point - add to current group
                current_group.append(para_text)
            else:
                # This is a new paragraph (including numbered points like 1., 2.)
                if current_group:
                    # Save previous group
                    grouped_paragraphs.append('\n'.join(current_group))
                # Start new group
                current_group = [para_text]

        # Don't forget the last group
        if current_group:
            grouped_paragraphs.append('\n'.join(current_group))

        # Create children from grouped paragraphs
        for idx, para_text in enumerate(grouped_paragraphs, start=1):
            article['children'].append({
                'eId': f"{article_num:03d}.{idx:03d}",
                'text': para_text
            })

        self.articles.append(article)

    def _signature_block(self):
        """Locate the 'Done at …' signature block: returns (start, end)
        indices into the txt_te p/table flow, or (None, None). The block
        runs from 'Done at' through the short signature lines that follow
        (names, 'For the Council', 'The President')."""
        flow = self._flow_elements()
        start = None
        for i, (kind, text) in enumerate(flow):
            if kind == 'p' and re.match(r'^Done at', text, re.IGNORECASE):
                start = i
                break
        if start is None:
            return None, None
        # A regulation's binding formula closes the enacting terms, just before 'Done at'
        if start > 0 and flow[start - 1][0] == 'p' and \
                flow[start - 1][1].upper().startswith(_BINDING_FORMULA.upper()):
            start -= 1
        end = start + 1
        while end < len(flow):
            kind, text = flow[end]
            if kind != 'p' or len(text) > 90 or self._is_footnote(text) or \
                    self._is_attachment_header(text):
                break
            end += 1
        return start, end

    def _flow_elements(self):
        """The document flow as [(kind, cleaned_text), …] for the direct
        p/table sequence of the TXT_TE container (empty lines dropped)."""
        if getattr(self, '_flow_cache', None) is not None:
            return self._flow_cache
        flow = []
        if hasattr(self, 'txt_te') and self.txt_te:
            elements = self.txt_te.find_all(['p', 'table'], recursive=False)
            if not elements:
                elements = self.txt_te.find_all(['p', 'table'])
                elements = [e for e in elements if e.name == 'table' or
                            e.find_parent('table') is None]
            for el in elements:
                if el.name == 'table':
                    text = self._extract_table_text(el)
                    kind = 'table'
                else:
                    text = self._clean_text(el.get_text())
                    kind = 'p'
                if text:
                    flow.append((kind, text))
        self._flow_cache = flow
        return flow

    _ATTACHMENT_HEADER_RE = re.compile(
        r'^(ANNEX|APPENDIX|AGREEMENT|PROTOCOL|EXCHANGE OF LETTERS|'
        r'CONVENTION|JOINT DECLARATION|DECLARATION|FINAL ACT)\b[\w\s./-]*$')

    def _is_attachment_header(self, text: str) -> bool:
        """A short all-caps heading opening an annex/agreement block."""
        t = text.strip()
        return len(t) < 80 and bool(self._ATTACHMENT_HEADER_RE.match(t)) \
            and t == t.upper()

    def _capture_leftover_blocks(self):
        """Append any flow block not covered by an extracted component to
        a trailing attachment annex. A block is covered when every one of
        its lines appears in some extracted text."""
        import re as _re

        def _canon(s):
            # extraction strips recital markers; canonicalise both sides so
            # '(1) Whereas x' matches an extracted 'x'
            s = _re.sub(r'^\s*\(\d+\)\s*', '', s or '')
            s = _re.sub(r'^\s*Whereas[,:]?\s+', '', s, flags=_re.IGNORECASE)
            return _re.sub(r'[^0-9A-Za-z]', '', s)

        extracted = [self.preface, self.formula, self.preamble_final,
                     getattr(self, 'recitals_intro', None),
                     str(self.conclusions or '')]
        # preface/conclusions join several flow blocks — cover the
        # original per-block texts too
        extracted += list(getattr(self, '_preface_texts', []) or [])
        extracted += list(getattr(self, '_conclusion_texts', []) or [])
        extracted += [c.get('text') for c in (self.citations or []) if isinstance(c, dict)]
        extracted += [r.get('text') for r in (self.recitals or []) if isinstance(r, dict)]
        for a in list(self.articles or []) + list(self.annexes or []):
            extracted += [a.get('num'), a.get('heading')]
            extracted += [c.get('text') for c in a.get('children', [])]
        lines = set()
        for text in extracted:
            for line in str(text or '').split('\n'):
                for variant in (line, self._clean_text(line)):
                    key = _canon(variant)
                    if key:
                        lines.add(key)
        # Extraction may also join several flow blocks into one text (points
        # merged into their paragraph): a block inside such a text is covered
        joined = '|'.join(lines)

        leftovers = []
        for _, block in self._flow_elements():
            block_lines = [_canon(line) for line in block.split('\n')]
            block_lines = [line for line in block_lines if line]
            if block_lines and not all(line in lines or line in joined for line in block_lines):
                leftovers.append(block)
        if leftovers:
            n = len(self.annexes) + 1
            self.annexes.append({
                'eId': f'att_{n}',
                'num': None,
                'heading': None,
                'children': [{'eId': f'{n:03d}.{i:03d}', 'text': t}
                             for i, t in enumerate(leftovers, 1)],
            })

    def get_conclusions(self):
        """
        Extract the signature block ('Done at …' plus signatories).
        """
        try:
            start, end = self._signature_block()
            if start is None:
                self.conclusions = None
                self.logger.warning("No conclusions found.")
                return
            flow = self._flow_elements()
            self._conclusion_texts = [text for _, text in flow[start:end]]
            self.conclusions = ' '.join(self._conclusion_texts)
            self.logger.info("Conclusions extracted.")
        except Exception as e:
            self.conclusions = None
            self.logger.error(f"Error extracting conclusions: {e}")

    def get_annexes(self):
        """
        Extract annexes and attached texts (agreements, protocols,
        exchanges of letters) that follow the signature block, split on
        their headings. Footnote reference lists stay with the material
        they follow.
        """
        self.annexes = []
        try:
            flow = self._flow_elements()
            if not flow:
                return
            start, end = self._signature_block()
            if start is None:
                # no signature: attachments only when an explicit heading
                # follows the enacting terms
                tail = None
                for i, (kind, text) in enumerate(flow):
                    if kind == 'p' and self._is_attachment_header(text):
                        tail = i
                        break
                if tail is None:
                    return
                region = flow[tail:]
            else:
                region = flow[end:]
            if not region:
                return

            current = None
            for kind, text in region:
                if kind == 'p' and self._is_attachment_header(text):
                    current = {
                        'eId': f'anx_{len(self.annexes) + 1}',
                        'num': text,
                        'heading': None,
                        'children': [],
                    }
                    self.annexes.append(current)
                    continue
                if current is None:
                    current = {
                        'eId': f'att_{len(self.annexes) + 1}',
                        'num': None,
                        'heading': None,
                        'children': [],
                    }
                    self.annexes.append(current)
                current['children'].append({
                    'eId': f'{len(self.annexes):03d}.{len(current["children"]) + 1:03d}',
                    'text': text,
                })
        except Exception as e:
            self.logger.error(f"Error extracting annexes: {e}")

    def parse(self, file_path: str, **options) -> 'CellarStandardHTMLParser':
        """
        Parse a standard HTML document and extract all components.
        If the input is a directory, searches for HTML files.

        Parameters
        ----------
        file_path : str
            Path to the HTML file or directory containing HTML files
        **options : dict
            Optional configuration:
            - validate : bool - Whether to validate against LegalJSON schema (default: False)

        Returns
        -------
        CellarStandardHTMLParser
            Self for method chaining with parsed document.
        """
        validate = options.get('validate', False)
        from pathlib import Path

        # Check if input is a directory
        path = Path(file_path)
        if path.is_dir():
            # Search for HTML files in the directory
            html_files = list(path.glob('*.html'))

            if html_files:
                # Use the first HTML file found
                file_path = str(html_files[0])
                self.logger.info(f"Found HTML document: {html_files[0].name}")
            else:
                self.logger.error(f"No HTML files found in directory: {path}")
                return self

        try:
            # Load and parse HTML
            self._flow_cache = None
            self._preface_texts = set()
            self._conclusion_texts = []
            self.get_root(file_path)

            # Extract all components
            self.get_preface()
            self.get_preamble()
            self.get_formula()
            self.get_citations()
            self.get_recitals()
            self.get_preamble_final()
            self.get_body()
            self.get_chapters()
            self.get_articles()
            self.get_conclusions()
            self.get_annexes()

            # Non-legislative documents (merger decisions, resolutions,
            # notices) have no act structure at all: keep the whole flow
            # as a single pseudo-article so no text is lost
            if not self.articles and not self.recitals and \
                    not self.citations and not self.annexes:
                preface_texts = getattr(self, '_preface_texts', set())
                flow = [(k, t) for k, t in self._flow_elements()
                        if t not in preface_texts]
                if flow:
                    self.articles = [{
                        'eId': 'enacting_terms',
                        'num': None,
                        'heading': None,
                        'children': [{'eId': f'unp_{i}', 'text': t}
                                     for i, (_, t) in enumerate(flow, 1)],
                    }]

            # Lossless net: any flow block not routed to a component ends
            # up in a trailing attachment, so no document text is dropped
            self._capture_leftover_blocks()

            # Validate if requested — always against the canonical to_dict()
            # output, never a hand-rolled dict that can drift from the schema
            if validate:
                if not LegalJSONValidator().validate(self.to_dict()):
                    self.logger.warning("LegalJSON validation failed")

            return self

        except Exception as e:
            self.logger.error(f"Error parsing document: {e}")
            raise
