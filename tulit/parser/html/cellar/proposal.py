from tulit.parser.html.html_parser import HTMLParser
from tulit.parser.strategies.article_extraction import ProposalArticleStrategy
import json
import re
import argparse
from typing import Optional, Any

class ProposalHTMLParser(HTMLParser):
    """
    Parser for European Commission proposal documents (COM documents).
    
    These documents have a different structure than regular EUR-Lex legislative acts.
    They typically contain:
    - Metadata (institution, date, reference numbers)
    - Proposal status and title
    - Explanatory Memorandum with sections and subsections
    - Sometimes the actual legal act text at the end
    """
    
    def __init__(self) -> None:
        super().__init__()
        self.metadata = {}
        self.explanatory_memorandum = {}
        self.chapters = []  # Proposals don't have chapters structure
        # Initialize article extraction strategy
        self.article_strategy = ProposalArticleStrategy()
        
    def get_metadata(self) -> None:
        """
        Extracts metadata from the Commission proposal HTML.
        
        Metadata includes:
        - Institution name (e.g., "EUROPEAN COMMISSION")
        - Emission date and location
        - Reference numbers (COM number, interinstitutional reference)
        - Proposal status
        - Document type
        - Title/subject
        
        Returns
        -------
        None
            The extracted metadata is stored in the 'metadata' attribute.
        """
        try:
            # Institution name
            logo_element = self.root.find('p', class_='Logo')
            if logo_element:
                self.metadata['institution'] = logo_element.get_text(strip=True)
            
            # Emission date
            emission_element = self.root.find('p', class_='Emission')
            if emission_element:
                self.metadata['emission_date'] = emission_element.get_text(strip=True)
            
            # Reference institutionnelle (COM number)
            ref_inst = self.root.find('p', class_='Rfrenceinstitutionnelle')
            if ref_inst:
                self.metadata['com_reference'] = ref_inst.get_text(strip=True)
            
            # Reference interinstitutionnelle (procedure number)
            ref_interinst = self.root.find('p', class_='Rfrenceinterinstitutionnelle')
            if ref_interinst:
                self.metadata['interinstitutional_reference'] = ref_interinst.get_text(strip=True)
            
            # Proposal status (e.g., "Proposal for a")
            status = self.root.find('p', class_='Statut')
            if status:
                self.metadata['status'] = status.get_text(strip=True)
            
            # Document type (e.g., "COUNCIL DECISION", "DIRECTIVE OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL")
            doc_type = self.root.find('p', class_='Typedudocument_cp')
            if doc_type:
                self.metadata['document_type'] = doc_type.get_text(strip=True)
            
            # Title/subject
            title = self.root.find('p', class_='Titreobjet_cp')
            if title:
                self.metadata['title'] = title.get_text(separator=' ', strip=True)
            
            print(f"Metadata extracted successfully. Keys: {list(self.metadata.keys())}")
        except Exception as e:
            print(f"Error extracting metadata: {e}")
    
    def _get_deepest_subsection_em(self, current_section):
        """Get the deepest available subsection for adding content."""
        if not current_section or not current_section['content']:
            return current_section
        
        last_item = current_section['content'][-1]
        if not isinstance(last_item, dict):
            return current_section
        
        if last_item.get('level') == 2 and last_item.get('content'):
            if isinstance(last_item['content'][-1], dict) and last_item['content'][-1].get('level') == 3:
                return last_item['content'][-1]
            return last_item
        elif last_item.get('level') in [2, 3]:
            return last_item
        
        return current_section
    
    def _process_heading_level1_em(self, element, current_section, sections):
        """Process ManualHeading1 element and return new section."""
        if current_section:
            sections.append(current_section)
        
        num_elem = element.find('span', class_='num')
        text_elem = element.find_all('span')[-1] if element.find_all('span') else element
        
        return {
            'level': 1,
            'number': num_elem.get_text(strip=True) if num_elem else None,
            'heading': text_elem.get_text(strip=True),
            'content': []
        }
    
    def _process_heading_level2_em(self, element):
        """Process ManualHeading2 element and return subsection."""
        num_elem = element.find('span', class_='num')
        text_spans = element.find_all('span')
        heading_text = ' '.join([s.get_text(strip=True) for s in text_spans if s.get('class') != ['num']])
        
        return {
            'level': 2,
            'number': num_elem.get_text(strip=True) if num_elem else None,
            'heading': heading_text,
            'content': []
        }
    
    def _process_heading_level3_em(self, element):
        """Process ManualHeading3 element and return subsection."""
        num_elem = element.find('span', class_='num')
        text_spans = element.find_all('span')
        heading_text = ' '.join([s.get_text(strip=True) for s in text_spans if s.get('class') != ['num']])
        
        return {
            'level': 3,
            'number': num_elem.get_text(strip=True) if num_elem else None,
            'heading': heading_text,
            'content': []
        }
    
    def _process_numbered_paragraph_em(self, element):
        """Process ManualNumPar1 element and return paragraph dict."""
        num_elem = element.find('span', class_='num')
        text = element.get_text(separator=' ', strip=True)
        if num_elem:
            num_text = num_elem.get_text(strip=True)
            text = text.replace(num_text, '', 1).strip()
        
        return {
            'type': 'numbered_paragraph',
            'number': num_elem.get_text(strip=True) if num_elem else None,
            'text': text
        }
    
    def _process_normal_paragraph_em(self, element):
        """Process Normal paragraph element and return paragraph dict or None."""
        text = element.get_text(separator=' ', strip=True)
        if text:
            return {
                'type': 'paragraph',
                'text': text
            }
        return None
    
    def _process_table_em(self, element):
        """Process table element and return table dict or None."""
        table_data = []
        rows = element.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            row_data = [cell.get_text(separator=' ', strip=True) for cell in cells]
            if any(row_data):
                table_data.append(row_data)
        
        if table_data:
            return {
                'type': 'table',
                'data': table_data
            }
        return None
    
    def _add_content_to_section_em(self, current_section, content_item):
        """Add content item to the appropriate subsection level."""
        if not current_section:
            return
        
        target = self._get_deepest_subsection_em(current_section)
        target['content'].append(content_item)
    
    def get_explanatory_memorandum(self) -> None:
        """
        Extracts the Explanatory Memorandum section from the proposal.
        
        The Explanatory Memorandum typically contains:
        - Title (class="Exposdesmotifstitre")
        - Sections with headings (class="li ManualHeading1", "li ManualHeading2", etc.)
        - Numbered paragraphs (class="li ManualNumPar1")
        - Normal text (class="Normal")
        
        Returns
        -------
        None
            The extracted content is stored in the 'explanatory_memorandum' attribute.
        """
        try:
            em_title = self.root.find('p', class_='Exposdesmotifstitre')
            if em_title:
                self.explanatory_memorandum['title'] = em_title.get_text(strip=True)
            
            sections = []
            current_section = None
            
            all_refs = self.root.find_all('p', class_='Rfrenceinterinstitutionnelle')
            end_marker = all_refs[1] if len(all_refs) > 1 else None
            
            content_divs = self.root.find_all('div', class_='content')
            
            for content_div in content_divs:
                if end_marker and end_marker in content_div.find_all('p'):
                    break
                
                for element in content_div.find_all(['p', 'table']):
                    classes = element.get('class', [])
                    
                    if 'li' in classes and 'ManualHeading1' in classes:
                        current_section = self._process_heading_level1_em(element, current_section, sections)
                    
                    elif 'li' in classes and 'ManualHeading2' in classes:
                        subsection = self._process_heading_level2_em(element)
                        if current_section:
                            current_section['content'].append(subsection)
                    
                    elif 'li' in classes and 'ManualHeading3' in classes:
                        subsection = self._process_heading_level3_em(element)
                        if current_section:
                            if current_section['content'] and isinstance(current_section['content'][-1], dict) \
                               and current_section['content'][-1].get('level') == 2:
                                current_section['content'][-1]['content'].append(subsection)
                            else:
                                current_section['content'].append(subsection)
                    
                    elif 'li' in classes and 'ManualNumPar1' in classes:
                        paragraph = self._process_numbered_paragraph_em(element)
                        self._add_content_to_section_em(current_section, paragraph)
                    
                    elif 'Normal' in classes:
                        paragraph = self._process_normal_paragraph_em(element)
                        if paragraph:
                            self._add_content_to_section_em(current_section, paragraph)
                    
                    elif element.name == 'table':
                        table_obj = self._process_table_em(element)
                        if table_obj:
                            self._add_content_to_section_em(current_section, table_obj)
            
            if current_section:
                sections.append(current_section)
            
            self.explanatory_memorandum['sections'] = sections
            
            print(f"Explanatory Memorandum extracted successfully. Number of sections: {len(sections)}")
        except Exception as e:
            print(f"Error extracting explanatory memorandum: {e}")
            import traceback
            traceback.print_exc()
    
    def get_preface(self) -> None:
        """
        For proposals, the preface is the combination of status, document type, and title.
        This extracts from the SECOND occurrence (the actual legal act), not the first (cover page).
        """
        try:
            # Find all occurrences and take the second set (the legal act itself)
            all_status = self.root.find_all('p', class_='Statut')
            all_doc_types = self.root.find_all('p', class_='Typedudocument')
            all_titles = self.root.find_all('p', class_='Titreobjet')
            
            parts = []
            
            # Use the second occurrence if available (the actual legal act), otherwise first
            status = all_status[1] if len(all_status) > 1 else all_status[0] if all_status else None
            if status:
                parts.append(status.get_text(strip=True))
            
            doc_type = all_doc_types[0] if all_doc_types else None
            if doc_type:
                parts.append(doc_type.get_text(strip=True))
            
            title = all_titles[0] if all_titles else None
            if title:
                parts.append(title.get_text(separator=' ', strip=True))
            
            self.preface = ' '.join(parts) if parts else None
            print(f"Preface extracted: {self.preface[:100] if self.preface else None}...")
        except Exception as e:
            print(f"Error extracting preface: {e}")
    
    def get_preamble(self) -> None:
        """
        For proposals, the preamble is typically null or minimal introductory text.
        The actual preamble components (formula, citations, recitals) are extracted separately.
        In EU legal documents, preamble usually refers to text before the formula,
        which in proposals is typically non-existent as they start with the formula directly.
        
        Returns
        -------
        None
            Sets self.preamble to null for proposals
        """
        try:
            # For proposals, preamble is null as the structure starts directly with formula
            # The formula, citations, and recitals are extracted as separate components
            self.preamble = None
            print("Preamble set to null (proposals have no introductory preamble text).")
        except Exception as e:
            print(f"Error extracting preamble: {e}")
            self.preamble = None
    
    def get_formula(self) -> None:
        """
        Extracts the formula from the preamble (e.g., "THE COUNCIL OF THE EUROPEAN UNION,").
        
        Returns
        -------
        None
            The extracted formula is stored in the 'formula' attribute.
        """
        try:
            if self.preamble:
                formula_elem = self.preamble.find('p', class_='Institutionquiagit')
                if formula_elem:
                    self.formula = formula_elem.get_text(strip=True)
                    print(f"Formula extracted: {self.formula}")
                else:
                    self.formula = None
            else:
                self.formula = None
        except Exception as e:
            print(f"Error extracting formula: {e}")
    
    def get_citations(self) -> None:
        """
        Extracts citations from the preamble (paragraphs starting with "Having regard to").
        Citations appear between the formula and "Whereas:"
        
        Returns
        -------
        None
            The extracted citations are stored in the 'citations' attribute.
        """
        try:
            self.citations = []
            citation_counter = 1
            
            # Find the formula element to start from
            formula_elem = self.root.find('p', class_='Institutionquiagit')
            if not formula_elem:
                return
            
            # Get all siblings after the formula until we hit "Whereas:"
            current = formula_elem.find_next_sibling()
            
            while current:
                if current.name == 'p' and 'Normal' in current.get('class', []):
                    text = current.get_text(strip=True)
                    # Stop when we hit "Whereas:"
                    if text.strip() == "Whereas:":
                        break
                    # Add citation with eId
                    if text and (text.startswith('Having regard') or text.startswith('After')):
                        self.citations.append({
                            'eId': f'cit_{citation_counter}',
                            'text': text
                        })
                        citation_counter += 1
                current = current.find_next_sibling()
                # Also check if we need to jump to next content div
                if not current:
                    parent = formula_elem.find_parent('div', class_='content')
                    if parent:
                        next_div = parent.find_next_sibling('div', class_='content')
                        if next_div:
                            current = next_div.find('p')
            
            print(f"Citations extracted: {len(self.citations)}")
        except Exception as e:
            print(f"Error extracting citations: {e}")
    
    def get_recitals(self) -> None:
        """
        Extracts recitals from the preamble (paragraphs with class "li ManualConsidrant").
        Recitals may span multiple content divs.
        
        Returns
        -------
        None
            The extracted recitals are stored in the 'recitals' attribute.
        """
        try:
            self.recitals = []
            recital_counter = 1
            
            # Find all recitals across all content divs (they're not limited to self.preamble div)
            # Recitals are between "Whereas:" and "HAS ADOPTED"
            recital_elements = self.root.find_all('p', class_='li ManualConsidrant')
            
            for recital in recital_elements:
                num_elem = recital.find('span', class_='num')
                number = num_elem.get_text(strip=True) if num_elem else None
                
                # Get full text
                text = recital.get_text(separator=' ', strip=True)
                # Remove the number from the beginning
                if number:
                    text = text.replace(number, '', 1).strip()
                
                self.recitals.append({
                    'eId': f'rct_{recital_counter}',
                    'num': number,
                    'text': text
                })
                recital_counter += 1
            
            print(f"Recitals extracted: {len(self.recitals)}")
        except Exception as e:
            print(f"Error extracting recitals: {e}")
    
    def get_preamble_final(self) -> None:
        """
        Extracts the final formula of the preamble (e.g., "HAS ADOPTED THIS DECISION:").
        
        Returns
        -------
        None
            The extracted final preamble is stored in the 'preamble_final' attribute.
        """
        try:
            if self.preamble:
                formula_elem = self.preamble.find('p', class_='Formuledadoption')
                if formula_elem:
                    self.preamble_final = formula_elem.get_text(strip=True)
                    print(f"Preamble final extracted: {self.preamble_final}")
                else:
                    self.preamble_final = None
            else:
                self.preamble_final = None
        except Exception as e:
            print(f"Error extracting preamble final: {e}")
    
    def get_body(self) -> None:
        """
        Extracts the body of the legal act (the enacting terms/articles).
        
        Returns
        -------
        None
            Sets self.body to the body element
        """
        try:
            # Find the div containing the Formuledadoption, then the body is in the same or next div
            if self.preamble:
                # The body typically comes after the preamble final
                formula = self.preamble.find('p', class_='Formuledadoption')
                if formula:
                    # Body is in the same div after the formula
                    self.body = formula.find_parent('div', class_='content')
                    print("Body element found.")
                else:
                    self.body = None
            else:
                self.body = None
        except Exception as e:
            print(f"Error extracting body: {e}")
    
    def _is_after_fait(self, article_elem, fait_elem) -> bool:
        """Check if article element comes after Fait section."""
        if not fait_elem:
            return False
        all_elems = list(self.root.descendants)
        try:
            article_pos = all_elems.index(article_elem)
            fait_pos = all_elems.index(fait_elem)
            return article_pos >= fait_pos
        except (ValueError, AttributeError):
            return False
    
    def _get_all_content_elements(self):
        """
        Get all content elements in document order, ignoring div structure.
        This flattens the document and eliminates div boundary complexity.
        """
        relevant_classes = ['Titrearticle', 'Normal', 'ManualNumPar1', 
                           'Point0', 'Point1', 'Text1', 'Fait']
        
        def has_relevant_class(elem):
            classes = elem.get('class', [])
            return any(cls in classes for cls in relevant_classes)
        
        return [elem for elem in self.root.find_all('p') if has_relevant_class(elem)]
    
    def _extract_article_number_and_heading(self, article_elem):
        """Extract article number and heading from Titrearticle element."""
        import re
        
        br_elem = article_elem.find('br')
        if br_elem:
            before_br = [elem.get_text(strip=True) for elem in article_elem.children
                        if elem != br_elem and hasattr(elem, 'get_text') 
                        and elem.get_text(strip=True)]
            
            found_br = False
            after_br = []
            for elem in article_elem.children:
                if elem == br_elem:
                    found_br = True
                    continue
                if found_br and hasattr(elem, 'get_text'):
                    text = elem.get_text(strip=True)
                    if text:
                        after_br.append(text)
            
            article_num = ' '.join(before_br)
            article_heading = ' '.join(after_br) if after_br else None
        else:
            article_num = article_elem.get_text(strip=True)
            article_heading = None
        
        return article_num, article_heading
    
    def _generate_article_eid(self, article_num: str, article_index: int) -> str:
        """Generate eId in format 'XXX' (e.g., '001', '002', '003')."""
        import re
        article_num_match = re.search(r'Article\s+(\d+)', article_num)
        if article_num_match:
            return article_num_match.group(1).zfill(3)
        return str(article_index).zfill(3)
    
    def _is_heading_text(self, text: str, following_text: str = None) -> bool:
        """
        Determine if text is likely a heading (not content).
        Headings are typically:
        - Short (< 100 chars)
        - Don't start with numbers like "1." or "(1)"
        - Don't contain full sentences (verbs like "shall", "is", "are")
        - Title-like formatting (often starts with capitals)
        """
        import re
        if not text or len(text) > 100:
            return False
        
        text_lower = text.lower()
        
        # Starts with numbered pattern = content, not heading
        if re.match(r'^[0-9]+\.', text) or re.match(r'^\([0-9a-z]+\)', text):
            return False
        
        # Contains sentence markers = likely content, not heading
        sentence_markers = ['shall ', ' is ', ' are ', ' was ', ' were ', 
                           ' has ', ' have ', ' will ', ' may ', ' must ',
                           'this decision', 'this regulation', 'this directive',
                           'member states', 'the commission', 'addressed to']
        if any(marker in text_lower for marker in sentence_markers):
            return False
        
        # Very short text without sentence structure = likely heading
        if len(text) < 60 and '.' not in text[:-1]:  # Allow trailing period
            return True
        
        # If following text is much longer, current is likely heading
        if following_text and len(following_text) > len(text) * 2:
            return True
        
        return False
    
    def _concatenate_related_content(self, elements: list, start_idx: int) -> tuple:
        """
        Concatenate list items, amendments, and quoted content starting from start_idx.
        Returns (concatenated_text, next_index_to_process).
        
        Handles:
        - Point0/Point1/Text1 list items following Normal paragraphs
        - Amendment patterns with quoted replacement text
        """
        import re
        
        if start_idx >= len(elements):
            return "", start_idx
        
        base_elem = elements[start_idx]
        base_text = base_elem.get_text(separator=' ', strip=True)
        concatenated = base_text
        current_idx = start_idx + 1
        
        # Quote characters for amendment detection
        opening_quotes = ("'", '"', "\u2018", "\u201C", '‹', '«', '「')
        closing_quotes = ("'", '"', "\u2019", "\u201D", '›', '»', '」', 
                         ".", "'.", '".', '.";', '";', "';", "';", 
                         '.\u201D;', '\u201D;', '.\u201D', '\u201D')
        
        # Check if this is an amendment introduction
        is_amendment_intro = (base_text.strip().endswith(':') and 
                            any(pattern in base_text.lower() for pattern in 
                                ['replaced by the following', 'amended as follows', 
                                 'inserted', 'added', 'shall read as follows']))
        
        in_quoted_content = False
        
        while current_idx < len(elements):
            elem = elements[current_idx]
            elem_classes = elem.get('class', [])
            elem_text = elem.get_text(separator=' ', strip=True)
            
            if not elem_text:
                current_idx += 1
                continue
            
            # Stop at Fait
            if 'Fait' in elem_classes:
                break
            
            # Handle Titrearticle - stop only if it's a real article boundary
            if 'Titrearticle' in elem_classes:
                # Check if this is a replacement article (quoted or out of sequence)
                if any(elem_text.startswith(q) for q in opening_quotes):
                    # This is a quoted replacement article - include it as content
                    concatenated += " " + elem_text
                    current_idx += 1
                    continue
                else:
                    # Check if it's a real article (in sequence)
                    # If we're in an amendment, articles like "Article 25" are replacements
                    match = re.search(r'Article\s+(\d+)([a-zA-Z])?', elem_text, re.IGNORECASE)
                    if match:
                        num = int(match.group(1))
                        has_letter = match.group(2) is not None
                        # Articles with letters or high numbers are replacement articles
                        if has_letter or num > 10:
                            concatenated += " " + elem_text
                            current_idx += 1
                            continue
                    # Real article boundary - stop
                    break
            
            # Check quote patterns
            starts_with_quote = any(elem_text.startswith(q) for q in opening_quotes)
            ends_with_quote = any(elem_text.endswith(q) for q in closing_quotes)
            is_numbered_item = bool(re.match(r'^\([0-9]+\)', elem_text.strip()) or 
                                   re.match(r'^\([a-z]\)', elem_text.strip()))
            
            # Handle Point0/Point1/Text1 list items - always concatenate
            if any(cls in elem_classes for cls in ['Point0', 'Point1', 'Text1']):
                concatenated += " " + elem_text
                current_idx += 1
                continue
            
            # For amendment introductions, handle numbered items and quoted content
            if is_amendment_intro:
                if in_quoted_content:
                    # Continue concatenating until quote ends
                    concatenated += " " + elem_text
                    current_idx += 1
                    if ends_with_quote:
                        in_quoted_content = False
                    continue
                elif is_numbered_item or starts_with_quote:
                    # Numbered items like (1), (2) are part of amendment
                    concatenated += " " + elem_text
                    current_idx += 1
                    if starts_with_quote and not ends_with_quote:
                        in_quoted_content = True
                    continue
                elif 'Normal' in elem_classes:
                    # Normal paragraph after amendment - might be quoted content
                    if starts_with_quote:
                        concatenated += " " + elem_text
                        current_idx += 1
                        if not ends_with_quote:
                            in_quoted_content = True
                        continue
                    else:
                        break
                else:
                    break
            else:
                # Non-amendment: only concatenate Point/Text items (handled above)
                break
        
        return concatenated, current_idx
    
    def _process_article_elements(self, elements: list, article_eId: str) -> tuple:
        """
        Process a list of elements belonging to one article.
        Returns (heading, children_list).
        
        First element might be a heading (short Normal text).
        Remaining elements become children.
        
        For amending articles (those containing "is amended as follows" or similar),
        all content is concatenated into a single child.
        """
        if not elements:
            return None, []
        
        heading = None
        children = []
        child_index = 1
        start_idx = 0
        
        # Check if first element is a heading
        first_elem = elements[0]
        first_classes = first_elem.get('class', [])
        first_text = first_elem.get_text(strip=True)
        
        if 'Normal' in first_classes:
            # Get following text for comparison
            following_text = None
            if len(elements) > 1:
                following_text = elements[1].get_text(strip=True)
            
            if self._is_heading_text(first_text, following_text):
                heading = first_text
                start_idx = 1
        
        # Check if this is an amending article by scanning for amendment intro
        is_amending_article = False
        for elem in elements[start_idx:]:
            elem_text = elem.get_text(strip=True).lower()
            if any(pattern in elem_text for pattern in 
                   ['is amended as follows', 'are amended as follows']):
                is_amending_article = True
                break
        
        # For amending articles, concatenate all content into single child
        if is_amending_article:
            all_text_parts = []
            for elem in elements[start_idx:]:
                elem_classes = elem.get('class', [])
                elem_text = elem.get_text(separator=' ', strip=True)
                
                if not elem_text:
                    continue
                
                # Stop at Fait
                if 'Fait' in elem_classes:
                    break
                
                all_text_parts.append(elem_text)
            
            if all_text_parts:
                children.append({
                    'eId': f"{article_eId}.001",
                    'text': ' '.join(all_text_parts)
                })
            
            return heading, children
        
        # Non-amending articles: process elements with concatenation logic
        idx = start_idx
        while idx < len(elements):
            elem = elements[idx]
            elem_classes = elem.get('class', [])
            elem_text = elem.get_text(separator=' ', strip=True)
            
            if not elem_text:
                idx += 1
                continue
            
            # Stop conditions
            if 'Titrearticle' in elem_classes or 'Fait' in elem_classes:
                break
            
            # Concatenate related content
            concatenated_text, next_idx = self._concatenate_related_content(elements, idx)
            
            if concatenated_text:
                children.append({
                    'eId': f"{article_eId}.{str(child_index).zfill(3)}",
                    'text': concatenated_text
                })
                child_index += 1
            
            idx = next_idx
        
        return heading, children
    
    def _is_replacement_article(self, article_text: str, expected_num: int) -> bool:
        """
        Check if an article is a replacement article inside an amendment.
        
        Replacement articles:
        - Start with a quote character
        - Have article numbers out of sequence (e.g., Article 25 when expecting Article 2)
        - Have article numbers with letters (e.g., Article 56a, Article 39a)
        """
        import re
        
        opening_quotes = ("'", '"', "\u2018", "\u201C", '‹', '«', '「')
        
        # Check for leading quote
        if article_text and any(article_text.startswith(q) for q in opening_quotes):
            return True
        
        # Extract article number from text
        match = re.search(r'Article\s+(\d+)([a-zA-Z])?', article_text, re.IGNORECASE)
        if match:
            num = int(match.group(1))
            has_letter = match.group(2) is not None
            
            # Articles with letters (e.g., 56a, 39a) are typically replacement articles
            if has_letter:
                return True
            
            # Article number significantly out of sequence (more than 2 ahead)
            if num > expected_num + 2:
                return True
        
        return False
    
    def get_articles(self) -> None:
        """
        Extracts articles using range-based approach.
        
        Strategy:
        1. Flatten all content elements in document order
        2. Find article boundaries (Titrearticle elements)
        3. Filter out replacement articles inside amendments
        4. Extract content between boundaries
        5. First short Normal paragraph = heading, rest = children
        
        Note: Titrearticle elements starting with a quote character or with
        out-of-sequence article numbers are replacement text inside amendments.
        """
        import re
        
        try:
            self.articles = []
            
            # Get all content elements in document order
            all_elements = self._get_all_content_elements()
            
            # First pass: Find all potential article positions and Fait
            potential_articles = []
            fait_index = len(all_elements)
            
            for i, elem in enumerate(all_elements):
                classes = elem.get('class', [])
                if 'Titrearticle' in classes:
                    text = elem.get_text(separator=' ', strip=True)
                    potential_articles.append((i, elem, text))
                elif 'Fait' in classes:
                    fait_index = i
                    break
            
            # Second pass: Filter out replacement articles
            article_starts = []
            expected_num = 1
            
            for i, elem, text in potential_articles:
                if self._is_replacement_article(text, expected_num):
                    # This is a replacement article inside an amendment - skip it
                    continue
                article_starts.append((i, elem))
                expected_num += 1
            
            # Process each article
            for idx, (start_pos, article_elem) in enumerate(article_starts):
                # Determine end position (next article or Fait)
                if idx + 1 < len(article_starts):
                    end_pos = article_starts[idx + 1][0]
                else:
                    end_pos = fait_index
                
                # Skip if article is after Fait
                if start_pos >= fait_index:
                    break
                
                # Extract article number and inline heading
                article_num, inline_heading = self._extract_article_number_and_heading(article_elem)
                article_eId = self._generate_article_eid(article_num, idx + 1)
                
                # Get content elements for this article (excluding the Titrearticle itself)
                content_elements = all_elements[start_pos + 1 : end_pos]
                
                # Process content to get heading and children
                heading, children = self._process_article_elements(content_elements, article_eId)
                
                # Use inline heading if available, otherwise use extracted heading
                final_heading = inline_heading or heading
                
                article_dict = {
                    'eId': article_eId,
                    'num': article_num,
                    'children': children
                }
                
                if final_heading:
                    article_dict['heading'] = final_heading
                
                self.articles.append(article_dict)
            
            print(f"Articles extracted: {len(self.articles)}")
        except Exception as e:
            print(f"Error extracting articles: {e}")
    
    def get_conclusions(self) -> None:
        """
        Extracts conclusions from the legal act (signature section).
        
        Returns
        -------
        None
            The extracted conclusions are stored in the 'conclusions' attribute.
        """
        try:
            # Find the Fait and signature elements
            fait = self.root.find('p', class_='Fait')
            signature = self.root.find('div', class_='signature')
            
            if fait or signature:
                parts = []
                if fait:
                    parts.append(fait.get_text(strip=True))
                if signature:
                    parts.append(signature.get_text(separator=' ', strip=True))
                
                self.conclusions = ' '.join(parts)
                print("Conclusions extracted.")
            else:
                self.conclusions = None
        except Exception as e:
            print(f"Error extracting conclusions: {e}")
    
    def parse(self, file: str) -> "ProposalHTMLParser":
        """
        Parses a Commission proposal HTML file and extracts all relevant information.
        
        Parameters
        ----------
        file : str
            Path to the HTML file to parse.
        
        Returns
        -------
        ProposalHTMLParser
            The parser object with parsed elements stored in attributes.
        
        Raises
        ------
        ValueError
            If the document is an annex rather than a main proposal.
        """
        try:
            self.get_root(file)
            print("Root element loaded successfully.")
        except Exception as e:
            print(f"Error in get_root: {e}")
            return self
        
        # Check if this is an annex document - fail early if so
        # Check document type element
        doc_type = self.root.find('p', class_='Typedudocument_cp')
        if doc_type and doc_type.get_text(strip=True).upper() == 'ANNEX':
            raise ValueError("This document is an annex (document_type is 'ANNEX'). Only main proposal documents should be parsed.")
        
        # Check for annex title class
        annex_title = self.root.find('p', class_='Annexetitre')
        if annex_title:
            raise ValueError("This document is an annex (detected 'Annexetitre' class). Only main proposal documents should be parsed.")
        
        try:
            self.get_metadata()
        except Exception as e:
            print(f"Error in get_metadata: {e}")
        
        # Skip explanatory memorandum parsing - not relevant for analysis
        # try:
        #     self.get_explanatory_memorandum()
        # except Exception as e:
        #     print(f"Error in get_explanatory_memorandum: {e}")
        
        # Parse the legal act itself (preamble and body)
        try:
            self.get_preamble()
        except Exception as e:
            print(f"Error in get_preamble: {e}")
        
        try:
            self.get_preface()
        except Exception as e:
            print(f"Error in get_preface: {e}")
        
        try:
            self.get_formula()
        except Exception as e:
            print(f"Error in get_formula: {e}")
        
        try:
            self.get_citations()
        except Exception as e:
            print(f"Error in get_citations: {e}")
        
        try:
            self.get_recitals()
        except Exception as e:
            print(f"Error in get_recitals: {e}")
        
        try:
            self.get_preamble_final()
        except Exception as e:
            print(f"Error in get_preamble_final: {e}")
        
        try:
            self.get_body()
        except Exception as e:
            print(f"Error in get_body: {e}")
        
        try:
            self.get_articles()
        except Exception as e:
            print(f"Error in get_articles: {e}")
        
        try:
            self.get_conclusions()
        except Exception as e:
            print(f"Error in get_conclusions: {e}")
        
        return self