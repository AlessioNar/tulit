from tulit.parser.html.html_parser import HTMLParser
import json
import re
import argparse
# LegalJSON validation
from tulit.parser.parser import LegalJSONValidator
import logging
from typing import Optional, Any


class CellarHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()

    def _normalize_text(self, text: str) -> str:
        """
        Normalize Unicode quotation marks and other special characters to ASCII equivalents.
        
        Parameters
        ----------
        text : str
            The text to normalize
            
        Returns
        -------
        str
            Normalized text with ASCII characters
        """
        # Replace Unicode quotation marks with ASCII apostrophes
        text = text.replace('\u2018', "'")  # Left single quotation mark
        text = text.replace('\u2019', "'")  # Right single quotation mark
        text = text.replace('\u201c', '"')  # Left double quotation mark
        text = text.replace('\u201d', '"')  # Right double quotation mark
        # Replace non-breaking space with regular space
        text = text.replace('\xa0', ' ')
        return text

    def get_preface(self) -> None:
        """
        Extracts the preface text from the HTML, if available.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None
            The extracted preface is stored in the 'preface' attribute.
        """
        try:
            # elements consumed by structured components; the attachment
            # sweep must not capture them a second time
            self._consumed_ids = set()
            preface_element = self.root.find('div', class_='eli-main-title')
            if preface_element:
                self.preface = self._normalize_text(preface_element.get_text(separator=' ', strip=True))
                self._consumed_ids.add(id(preface_element))
                self.logger.info("Preface extracted successfully")
            else:
                self.preface = None
                self.logger.warning("No preface found")
        except Exception as e:
            self.logger.error(f"Error extracting preface: {e}", exc_info=True)
    
            
    def get_preamble(self) -> None:
        """
        Extracts the preamble text from the HTML, if available.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None
            The extracted preamble is stored in the 'preamble' attribute.
        """
        
        self.preamble = self.root.find('div', id=lambda x: bool(x) and x.startswith('pbl'))
        if self.preamble is None:
            return
        getattr(self, '_consumed_ids', set()).add(id(self.preamble))
        # Footnotes are dropped act-side by design; inline markers (the
        # anchor text) stay with the sentence that carries them
        for note in self.preamble.find_all('p', class_='oj-note'):
            note.decompose()

    def _preamble_loose_ps(self) -> list:
        """Paragraphs of the preamble that live outside cit_/rct_
        subdivisions (formula, 'Whereas:' intro, solemn forms, and — in
        decisions with narrative preambles — the numbered reasoning)."""
        loose = []
        for p in self.preamble.find_all('p'):
            if p.find_parent('div', id=lambda x: bool(x) and x.startswith(('cit_', 'rct_'))):
                continue
            text = self._normalize_text(' '.join(p.get_text(separator=' ', strip=True).split()))
            if text:
                loose.append(text)
        return loose

    def get_formula(self) -> None:
        """
        Extracts the formula from the HTML, if present.
        """
        if self.preamble is None:
            return
        loose = self._preamble_loose_ps()
        self.formula = loose[0] if loose else None

    def get_citations(self) -> None:
        """
        Extracts citations from the HTML: the cit_ subdivisions plus any
        loose solemn-form paragraphs between them ('Acting in accordance
        with…', 'After consulting…').
        """
        self.citations = []
        if self.preamble is None:
            return
        for citation in self.preamble.find_all('div', id=lambda x: bool(x) and x.startswith('cit_')):
            self.citations.append({
                'eId': citation.get('id'),
                'text': self._normalize_text(' '.join(citation.get_text(separator=' ', strip=True).split())),
            })
        loose = self._preamble_loose_ps()
        # first loose p is the formula, last is the final formula; what
        # remains (minus 'Whereas' intros and numbered narrative recitals)
        # belongs with the citations
        for text in loose[1:-1]:
            if re.match(r'^\(\d+\)', text) or re.match(r'^whereas\b', text, re.IGNORECASE):
                continue
            self.citations.append({
                'eId': f'cit_{len(self.citations) + 1}',
                'text': text,
            })

    def get_recitals(self) -> None:
        """
        Extracts recitals: the rct_ subdivisions plus, for acts with
        narrative preambles (e.g. State-aid decisions), the loose
        numbered '(N) …' paragraphs. The bare 'Whereas:' line becomes
        recitals_intro.
        """
        self.recitals = []
        self.recitals_intro = None
        if self.preamble is None:
            return
        for recital in self.preamble.find_all('div', id=lambda x: bool(x) and x.startswith('rct_')):
            text = recital.get_text()
            text = re.sub(r'\s+', ' ', text).strip()
            text = re.sub(r'^\(\d+\)', '', text).strip()
            self.recitals.append({
                'eId': recital.get('id'),
                'text': self._normalize_text(text),
            })
        loose = self._preamble_loose_ps()
        for text in loose[1:-1]:
            if re.match(r'^whereas\b[:,]?\s*$', text, re.IGNORECASE):
                self.recitals_intro = text
                continue
            m = re.match(r'^\((\d+)\)\s*(.*)', text, re.DOTALL)
            if m:
                self.recitals.append({
                    'eId': f'rct_{m.group(1)}',
                    'text': self._normalize_text(m.group(2).strip()),
                })
                continue
            # bare 'whereas …' recitals (agreements, older drafting)
            m = re.match(r'^whereas[,:]?\s+(.+)', text, re.IGNORECASE | re.DOTALL)
            if m:
                self.recitals.append({
                    'eId': f'rct_{len(self.recitals) + 1}',
                    'text': self._normalize_text(m.group(1).strip()),
                })

    def get_preamble_final(self) -> None:
        """
        Extracts the final preamble formula ('HAS ADOPTED THIS …').
        """
        if self.preamble is None:
            return
        loose = self._preamble_loose_ps()
        self.preamble_final = loose[-1] if len(loose) > 1 else None

    def get_body(self) -> None:
        """
        Extracts the body content from the HTML.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None
            The extracted body content is stored in the 'body' attribute
        """
        
        # Try to find body with enc_ prefix
        self.body = self.root.find('div', id=lambda x: x and x.startswith('enc_'))
        
        # If no explicit body found, use eli-container as fallback
        if self.body is None:
            self.body = self.root.find('div', class_='eli-container')
            self.logger.warning("Body element not found. Using eli-container as fallback")
        
        # If still no body, use root itself
        if self.body is None:
            self.body = self.root
            self.logger.warning("Body element not found. Using root as fallback")
        if self.body is not None and str(self.body.get('id') or '').startswith('enc'):
            getattr(self, '_consumed_ids', set()).add(id(self.body))

    # ELI subdivision id prefixes used by OJ HTML for divisions above
    # article level, mapped to their type
    _DIVISION_PREFIXES = {
        'prt': 'part',
        'tit': 'title',
        'tis': 'title',
        'cpt': 'chapter',
        'sct': 'section',
        'sbs': 'subsection',
    }

    def _is_division_id(self, an_id: Optional[str]) -> bool:
        return bool(an_id) and '.' not in an_id and \
            an_id.split('_')[0] in self._DIVISION_PREFIXES

    def _division_parent(self, element) -> Optional[str]:
        """eId of the nearest enclosing division div, if any."""
        for anc in element.find_parents('div', id=True):
            if self._is_division_id(anc.get('id')):
                return anc.get('id')
        return None

    def get_chapters(self) -> None:
        """
        Extracts every division above article level (part/title/chapter/
        section/subsection div ids), typed, with a parent link to the
        enclosing division.
        """

        if self.body is None:
            self.chapters = []
            self.logger.warning("No body element to extract chapters from")
            return

        divisions = self.body.find_all('div', id=self._is_division_id)
        self.chapters = []
        consumed = getattr(self, '_consumed_ids', set())
        for division in divisions:
            if 'eli-main-title' in (division.get('class') or []):
                continue
            eId = division.get('id')
            section_ps = division.find_all(
                'p', class_=lambda c: c and c.startswith('oj-ti-section'), limit=2)
            title_elem = division.find('div', class_='eli-title')
            num = section_ps[0].get_text(strip=True) if section_ps else None
            if title_elem is not None:
                heading = title_elem.get_text(strip=True)
                consumed.add(id(title_elem))
            elif len(section_ps) > 1:
                # older layouts carry the heading as a second section title
                heading = section_ps[1].get_text(strip=True)
                consumed.add(id(section_ps[1]))
            else:
                heading = None
            if section_ps:
                consumed.add(id(section_ps[0]))
            if num is None and heading is None:
                continue
            self.chapters.append({
                'eId': eId,
                'type': self._DIVISION_PREFIXES[eId.split('_')[0]],
                'num': num,
                'heading': heading,
                'parent': self._division_parent(division),
            })

    _ARTICLE_TITLE_CLASSES = {'oj-ti-art', 'oj-sti-art',
                              'title-article-norm', 'stitle-article-norm'}

    def _iter_article_blocks(self, article):
        """Yield the readable text blocks of an article div in document
        order, skipping titles and footnotes; tables render as row text."""
        def walk(el):
            for child in el.children:
                name = getattr(child, 'name', None)
                if name is None:
                    continue
                classes = set(child.get('class') or [])
                if classes & self._ARTICLE_TITLE_CLASSES or \
                        classes & {'oj-note', 'no-parag'}:
                    continue
                if name == 'table':
                    text = self._table_text(child, keep_notes=False)
                    if text:
                        yield text
                elif name in ('div', 'section', 'blockquote'):
                    if child.find(['p', 'table', 'div', 'dl', 'ul', 'ol']) is not None:
                        yield from walk(child)
                    else:
                        # bare-text container: its text is a block of its own
                        text = ' '.join(child.get_text(separator=' ', strip=True).split())
                        if text:
                            yield text
                else:
                    text = ' '.join(child.get_text(separator=' ', strip=True).split())
                    if text:
                        yield text
        yield from walk(article)

    def _fold_blocks(self, blocks) -> list:
        """Fold text blocks into paragraph children: a block opening with
        'N.' starts par_N; blocks that follow a numbered paragraph join it
        (points, subparagraphs); loose blocks become unp_N children."""
        children = []
        used = set()
        unp = 0
        current = None
        for text in blocks:
            text = self._normalize_text(text)
            m = re.match(r'(\d+[a-z]?)\.\s', text)
            eid = f'par_{m.group(1)}' if m else None
            if eid and eid not in used:
                used.add(eid)
                current = {'eId': eid, 'text': text}
                children.append(current)
            elif current is not None and current['eId'].startswith('par_'):
                current['text'] += '\n' + text
            else:
                unp += 1
                current = {'eId': f'unp_{unp}', 'text': text}
                children.append(current)
        return children

    def _enacting_terms_leftovers(self) -> list:
        """Text blocks of the enacting terms living outside any article
        div: attached agreement texts, decision summaries, sequence
        headings. Division numbers/headings (captured as chapters) and
        footnotes are excluded."""
        if self.body is None:
            return []
        if not str(self.body.get('id') or '').startswith('enc'):
            # no enacting-terms div anywhere (interinstitutional
            # agreements): the non-structured remainder of the act
            # container IS the enacting content
            containers = self._act_containers()
            if containers:
                return self._attachment_blocks(containers[0], skip_main_subdivs=True)
            return []

        def in_article(el):
            return el.find_parent(
                'div', id=lambda x: bool(x) and (x == 'art' or x.startswith('art_'))) is not None

        blocks = []
        for el in self.body.find_all(['p', 'table']):
            if in_article(el):
                continue
            if el.name == 'table':
                if el.find_parent('table'):
                    continue
                text = self._table_text(el, keep_notes=False)
            else:
                if el.find_parent('table'):
                    continue
                classes = set(el.get('class') or [])
                if 'oj-note' in classes:
                    continue
                if any(str(c).startswith('oj-ti-section') for c in classes):
                    continue
                if el.find_parent('div', class_='eli-title'):
                    continue
                text = ' '.join(el.get_text(separator=' ', strip=True).split())
            if text:
                blocks.append(text)
        return blocks

    def get_articles(self) -> None:
        """
        Extracts articles from the HTML. Each <div> with an id starting with "art" is treated as an article (eId).
        Subsequent subdivisions are processed based on the closest parent with an id.

        Returns:
            list[dict]: List of articles, each containing its eId and associated content.
        """
        
        if self.body is None:
            self.articles = []
            self.logger.warning("No body element to extract articles from")
            return
        
        # Find all article divs: either id="art" (sole article) or id="art_X" (numbered articles)
        articles = self.body.find_all('div', id=lambda x: x and (x == 'art' or (x.startswith('art_') and '.' not in x)))
        self.articles = []
        for article in articles:
            eId = article.get('id')  # Treat the id as the eId
            getattr(self, '_consumed_ids', set()).add(id(article))
            
            # Try original document format first (oj-ti-art), then consolidated format (title-article-norm)
            article_num_elem = article.find('p', class_='oj-ti-art')
            if article_num_elem is None:
                article_num_elem = article.find('p', class_='title-article-norm')
            
            if article_num_elem is None:
                self.logger.warning(f"Article {eId} has no article title element, skipping")
                continue
            
            article_num = self._normalize_text(article_num_elem.get_text(strip=True))
            
            # Try original document format first (oj-sti-art), then consolidated format (stitle-article-norm)
            article_title_element = article.find('p', class_='oj-sti-art')
            if article_title_element is None:
                article_title_element = article.find('p', class_='stitle-article-norm')
            
            if article_title_element is not None:
                article_title = self._normalize_text(article_title_element.get_text(strip=True))
            else:
                article_title = None
            
            # Extract paragraphs and lists within the article. OJ xhtml
            # (oj-* classes) goes through a generic document-order block
            # walk; consolidated formats keep their dedicated branches.
            children = []
            if article.find('p', class_=lambda c: bool(c) and any(
                    str(cl).startswith('oj-') for cl in (c if isinstance(c, list) else [c]))):
                children = self._fold_blocks(self._iter_article_blocks(article))

            # Handle consolidated text format with <div class="norm"> and <span class="no-parag">
            # This format is used in consolidated documents (e.g., 02009R1010)
            if not children:  # Only try this if we haven't already extracted children
                norm_divs = article.find_all('div', class_='norm', recursive=False)
                if norm_divs:
                    for idx, norm_div in enumerate(norm_divs):
                        # Check if this div has a numbered paragraph marker
                        no_parag = norm_div.find('span', class_='no-parag')
                        if no_parag:
                            # Get the text from the inline-element div or the norm div itself
                            inline_elem = norm_div.find('div', class_='inline-element')
                            if inline_elem:
                                text = ' '.join(inline_elem.get_text(separator=' ', strip=True).split())
                            else:
                                # Get all text except the no-parag span
                                no_parag.extract()
                                text = ' '.join(norm_div.get_text(separator=' ', strip=True).split())
                            text = re.sub(r'\s+([.,!?;:\\''])', r'\1', text)
                            text = self._normalize_text(text)
                            children.append({
                                'eId': idx,
                                'text': text
                            })
                        else:
                            # Single paragraph without numbering
                            text = ' '.join(norm_div.get_text(separator=' ', strip=True).split())
                            text = re.sub(r'\s+([.,!?;:\\''])', r'\1', text)
                            text = self._normalize_text(text)
                            if text:  # Only add if there's actual content
                                children.append({
                                    'eId': idx,
                                    'text': text
                                })
                
                # Also check for simple <p class="norm"> paragraphs (single paragraph articles)
                if not children:
                    norm_paragraphs = article.find_all('p', class_='norm', recursive=False)
                    for idx, p in enumerate(norm_paragraphs):
                        text = ' '.join(p.get_text(separator=' ', strip=True).split())
                        text = re.sub(r'\s+([.,!?;:\\''])', r'\1', text)
                        text = self._normalize_text(text)
                        if text:
                            children.append({
                                'eId': idx,
                                'text': text
                            })
            
            # Generic fallback: if no specific pattern matched, extract all text content
            # This handles articles with complex tables or other structures not covered by specific patterns
            if not children:
                # Skip title elements to avoid duplicate content
                article_copy = article.__copy__()
                for title_elem in article_copy.find_all(['p'], class_=['oj-ti-art', 'oj-sti-art', 'title-article-norm', 'stitle-article-norm']):
                    title_elem.decompose()
                
                text = ' '.join(article_copy.get_text(separator=' ', strip=True).split())
                text = re.sub(r'\s+([.,!?;:\\''])', r'\1', text)
                text = self._normalize_text(text)
                if text:  # Only add if there's actual content after removing titles
                    children.append({
                        'eId': 0,
                        'text': text
                    })

            # Store the article with its eId and subdivisions
            self.articles.append({
                'eId': eId,
                'num': article_num,
                'heading': article_title,
                'parent': self._division_parent(article),
                'children': children
            })

        # Enacting-terms content outside any article (attached agreements,
        # decision summaries) becomes a pseudo-article, as in the Formex
        # parser
        leftovers = self._enacting_terms_leftovers()
        if leftovers and not any(a['eId'] == 'enacting_terms' for a in self.articles):
            self.articles.append({
                'eId': 'enacting_terms',
                'num': None,
                'heading': None,
                'parent': None,
                'children': self._fold_blocks(leftovers),
            })

        # ELI-style child eIds (par_N / unp_N)
        self._standardize_children_numbering()
        self._build_structure()


    def _standardize_children_numbering(self) -> None:
        """
        Give article children ELI-style eIds: par_N for children whose
        paragraph number is known (numbered-table rows) or whose text opens
        with 'N.', unp_N for the rest.
        """
        for article in self.articles:
            used = set()
            unp = 0
            for child in article['children']:
                token = None
                par_num = child.pop('par_num', None)
                if par_num is not None:
                    # the numbered-table branch captured the real number
                    token = str(par_num)
                else:
                    m = re.match(r'(\d+[a-z]?)\.\s', str(child.get('text') or ''))
                    if m:
                        token = m.group(1)
                eid = f'par_{token}' if token else None
                if eid is None or eid in used:
                    unp += 1
                    eid = f'unp_{unp}'
                used.add(eid)
                child['eId'] = eid

    def _build_structure(self) -> None:
        """Nested skeleton of the enacting terms: division nodes
        {eId, type, num, children} with article leaves, in document order.
        References only — content stays in chapters/articles."""
        self.structure = []
        if self.body is None:
            return
        info = {c['eId']: c for c in self.chapters}
        article_ids = {a['eId'] for a in self.articles}
        nodes = {}

        def attach(element, node):
            parent = self._division_parent(element)
            if parent in nodes:
                nodes[parent]['children'].append(node)
            else:
                self.structure.append(node)

        for div in self.body.find_all('div', id=True):
            an_id = div.get('id')
            if an_id in info:
                c = info[an_id]
                node = {'eId': an_id, 'type': c['type'], 'num': c['num'],
                        'children': []}
                nodes[an_id] = node
                attach(div, node)
            elif an_id in article_ids:
                attach(div, {'eId': an_id, 'type': 'article'})
    
    def get_conclusions(self) -> None:
        """
        Extracts conclusions: the final-provisions div (fnp_*) when
        present, else the oj-final div. Footnotes are dropped.
        """
        conclusions_element = self.root.find(
            'div', id=lambda x: bool(x) and x.startswith('fnp'))
        if conclusions_element is None:
            conclusions_element = self.root.find('div', class_='oj-final')
        if conclusions_element:
            getattr(self, '_consumed_ids', set()).add(id(conclusions_element))
            texts = []
            for el in conclusions_element.find_all(['p', 'table']):
                if el.name == 'table':
                    if el.find_parent('table'):
                        continue
                    t = self._table_text(el, keep_notes=False)
                    if t:
                        texts.append(t)
                    continue
                if el.find_parent('table'):
                    continue
                if 'oj-note' in (el.get('class') or []):
                    continue
                t = ' '.join(el.get_text(separator=' ', strip=True).split())
                if t:
                    texts.append(t)
            if not texts:
                texts = [' '.join(conclusions_element.get_text(separator=' ', strip=True).split())]
            self.conclusions = self._normalize_text(' '.join(texts)) or None
        else:
            self.conclusions = None

    def _act_containers(self) -> list:
        """The document's non-annex eli-container divs (the act proper,
        plus attached acts/agreements in multi-act OJ pieces)."""
        return [c for c in self.root.find_all('div', class_='eli-container')
                if not (c.get('id') or '').startswith('anx')]

    _ACT_SUBDIV_PREFIXES = ('tit', 'pbl', 'enc', 'fnp')

    def _attachment_blocks(self, container, skip_main_subdivs) -> list:
        """Text blocks of an act container that belong to attached
        material. With skip_main_subdivs, the tit/pbl/enc/fnp
        subdivisions (the act proper) are excluded. Container-level
        footnotes and page-header furniture are dropped."""
        blocks = []

        def walk(el):
            for child in el.children:
                name = getattr(child, 'name', None)
                if name is None:
                    continue
                cid = child.get('id') or ''
                if cid.startswith('anx'):
                    continue
                classes = [str(c) for c in (child.get('class') or [])]
                if 'oj-note' in classes or any(c.startswith('oj-hd') for c in classes):
                    continue
                if skip_main_subdivs and \
                        id(child) in getattr(self, '_consumed_ids', set()):
                    # this element's text already lives in another
                    # component (preface, preamble, articles, chapters
                    # headings, conclusions)
                    continue
                if name == 'table':
                    if child.find('p', class_=lambda c: bool(c) and str(c).startswith('oj-hd')):
                        continue
                    # notes inside attached tables stay: corrigenda quote
                    # footnote definitions as content
                    text = self._table_text(child, keep_notes=True)
                    if text:
                        blocks.append(self._normalize_text(text))
                elif name in ('div', 'section', 'blockquote'):
                    if child.find(['p', 'table', 'div', 'dl', 'ul', 'ol']) is not None:
                        walk(child)
                    else:
                        text = ' '.join(child.get_text(separator=' ', strip=True).split())
                        if text:
                            blocks.append(self._normalize_text(text))
                else:
                    text = ' '.join(child.get_text(separator=' ', strip=True).split())
                    if text:
                        blocks.append(self._normalize_text(text))

        walk(container)
        return blocks

    def _table_text(self, table, keep_notes: bool = True) -> str:
        """Readable text of an HTML table: cells joined with ' | ', rows
        with newlines. Only this table's own rows are walked — a nested
        table's text is already part of its enclosing cell. Act-side
        callers pass keep_notes=False (footnotes dropped by design)."""
        if not keep_notes:
            for note in table.find_all('p', class_='oj-note'):
                note.decompose()
        rows = []
        for tr in table.find_all('tr'):
            if tr.find_parent('table') is not table:
                continue
            cells = []
            for td in tr.find_all(['td', 'th']):
                if td.find_parent('tr') is not tr:
                    continue
                cells.append(' '.join(td.get_text(separator=' ', strip=True).split()))
            cells = [c for c in cells if c]
            if cells:
                rows.append(' | '.join(cells))
        return '\n'.join(rows)

    def get_annexes(self) -> None:
        """
        Extracts annexes (top-level anx_* divs), uniform with articles:
        eId, num, heading and children text blocks with NNN.NNN eIds.
        """
        self.annexes = []
        annex_divs = self.root.find_all(
            'div', id=lambda x: bool(x) and x.startswith('anx'))
        # keep only top-level annexes: a nested anx div (annex to an
        # annexed act) is already covered by its enclosing annex
        annex_divs = [a for a in annex_divs if a.find_parent(
            'div', id=lambda x: bool(x) and x.startswith('anx')) is None]
        for index, anx in enumerate(annex_divs, start=1):
            # only direct-child titles name the annex; nested doc-ti
            # blocks belong to annexed documents and stay as content
            titles = anx.find_all('p', class_='oj-doc-ti', recursive=False)
            num = titles[0].get_text(strip=True) if titles else None
            heading = titles[1].get_text(strip=True) if len(titles) > 1 else None
            title_elems = set(id(t) for t in titles[:2])
            children = []
            for block in anx.children:
                name = getattr(block, 'name', None)
                if name is None:
                    continue
                # only the two blocks used as num/heading are titles; any
                # further oj-doc-ti block is content (inner section titles)
                if name == 'p' and id(block) in title_elems:
                    continue
                if name == 'table':
                    text = self._table_text(block)
                else:
                    text = ' '.join(block.get_text(separator=' ', strip=True).split())
                text = self._normalize_text(text)
                if not text:
                    continue
                children.append({
                    'eId': f'{index:03d}.{len(children) + 1:03d}',
                    'text': text,
                })
            self.annexes.append({
                'eId': anx.get('id'),
                'num': num,
                'heading': heading,
                'children': children,
            })

        # Attached material published with the act but outside its
        # tit/pbl/enc/fnp structure (agreements, joint declarations,
        # additional acts in multi-act OJ pieces) becomes att_N annexes.
        # The wrapper level (content between containers, e.g. sequence
        # titles of annex groups) counts as attached material too.
        containers = self._act_containers()
        first_has_enc = bool(containers) and containers[0].find(
            'div', id=lambda x: bool(x) and x.startswith('enc')) is not None
        regions = [(c, i == 0) for i, c in enumerate(containers)]
        wrapper = self._wrapper_blocks()
        att = 0
        for container, is_first in regions:
            if is_first and not first_has_enc:
                # without an enc div the remainder is enacting content
                # (captured as a pseudo-article), not an attachment
                continue
            blocks = self._attachment_blocks(container, skip_main_subdivs=is_first)
            if not blocks:
                continue
            att += 1
            children = [{'eId': f'att{att:03d}.{n:03d}', 'text': text}
                        for n, text in enumerate(blocks, start=1)]
            self.annexes.append({
                'eId': f'att_{att}',
                'num': None,
                'heading': None,
                'children': children,
            })
        if wrapper:
            att += 1
            self.annexes.append({
                'eId': f'att_{att}',
                'num': None,
                'heading': None,
                'children': [{'eId': f'att{att:03d}.{n:03d}', 'text': text}
                             for n, text in enumerate(wrapper, start=1)],
            })

    def _wrapper_blocks(self) -> list:
        """Content blocks living outside every eli-container (sequence
        titles between annexes, orphan paragraphs at OJ-piece level).
        Page-header furniture (oj-hd-*) and footnotes are excluded."""
        blocks = []
        for el in self.root.find_all(['p', 'table']):
            if el.find_parent('div', class_='eli-container') is not None:
                continue
            if el.find_parent('div', id=lambda x: bool(x) and x.startswith(
                    ('anx', 'tit', 'pbl', 'enc', 'fnp'))) is not None:
                continue
            if el.find_parent('table') is not None:
                continue
            classes = [str(c) for c in (el.get('class') or [])]
            if any(c.startswith('oj-hd') for c in classes) or 'oj-note' in classes:
                continue
            if el.name == 'table':
                if el.find('p', class_=lambda c: bool(c) and str(c).startswith('oj-hd')):
                    continue
                text = self._table_text(el)
            else:
                text = ' '.join(el.get_text(separator=' ', strip=True).split())
            text = self._normalize_text(text)
            if text:
                blocks.append(text)
        return blocks

    def parse(self, file: str, **options) -> "CellarHTMLParser":
        """
        Parses an XHTML document. If the input is a directory, searches for XHTML files.
        
        Parameters
        ----------
        file : str
            Path to the XHTML file or directory containing XHTML files.
        **options : dict
            Optional configuration options
        
        Returns
        -------
        CellarHTMLParser
            Self for method chaining with extracted content.
        """
        from pathlib import Path
        
        # Check if input is a directory
        file_path = Path(file)
        if file_path.is_dir():
            # Search for XHTML files in the directory
            xhtml_files = list(file_path.glob('*.xhtml')) + list(file_path.glob('*.html'))
            
            if xhtml_files:
                # Use the first XHTML/HTML file found
                file = str(xhtml_files[0])
                logging.info(f"Found XHTML document: {xhtml_files[0].name}")
            else:
                logging.error(f"No XHTML/HTML files found in directory: {file_path}")
                return self
        
        return super().parse(file)