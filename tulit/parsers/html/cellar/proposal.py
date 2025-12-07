from tulit.parsers.html.html_parser import HTMLParser
from tulit.parsers.strategies.article_extraction import ProposalArticleStrategy
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
        Extracts the preamble of the legal act (not the explanatory memorandum).
        The preamble appears after the explanatory memorandum and contains:
        - Interinstitutional reference
        - Status 
        - Document type
        - Title
        - Institution acting
        - Citations (Having regard to...)
        - Recitals (Whereas...)
        
        Returns
        -------
        None
            Sets self.preamble to the preamble element
        """
        try:
            # Find the second occurrence of Rfrenceinterinstitutionnelle (the legal act one)
            all_refs = self.root.find_all('p', class_='Rfrenceinterinstitutionnelle')
            if len(all_refs) > 1:
                # Start from the second reference
                start_element = all_refs[1]
                
                # Find the parent content div
                self.preamble = start_element.find_parent('div', class_='content')
                print("Preamble element found.")
            else:
                self.preamble = None
                print("No preamble found in legal act.")
        except Exception as e:
            print(f"Error extracting preamble: {e}")
    
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
                    # Add citation
                    if text and (text.startswith('Having regard') or text.startswith('After')):
                        self.citations.append({
                            'text': text
                        })
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
                    'num': number,
                    'text': text
                })
            
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
        """Generate eId from article number."""
        import re
        article_num_match = re.search(r'Article\s+(\d+)', article_num)
        if article_num_match:
            return f"art_{article_num_match.group(1)}"
        return f"art_{article_index}"
    
    def _try_extract_heading_from_next_paragraph(self, article_elem):
        """Try to extract heading from next Normal paragraph if not found."""
        next_p = article_elem.find_next_sibling('p')
        if next_p and 'Normal' in next_p.get('class', []):
            potential_heading = next_p.get_text(strip=True)
            if len(potential_heading) < 100:
                following_p = next_p.find_next_sibling('p')
                if following_p and 'Normal' in following_p.get('class', []):
                    return potential_heading
        return None
    
    def _concatenate_list_items(self, base_text: str, next_elem, processed_elems: set):
        """Concatenate list items (Point0/Point1/Text1) with base text."""
        concatenated_text = base_text
        temp_elem = next_elem.find_next_sibling('p')
        temp_visited_divs = set()
        
        while temp_elem or True:
            if not temp_elem:
                parent = next_elem.find_parent('div', class_='content')
                if parent and id(parent) not in temp_visited_divs:
                    temp_visited_divs.add(id(parent))
                    next_div = parent.find_next_sibling('div', class_='content')
                    if next_div:
                        temp_elem = next_div.find('p')
                        next_elem = next_div
                    else:
                        break
                else:
                    break
                continue
            
            temp_classes = temp_elem.get('class', [])
            if ('li' in temp_classes and ('Point0' in temp_classes or 'Point1' in temp_classes)):
                list_text = temp_elem.get_text(separator=' ', strip=True)
                if list_text:
                    concatenated_text += " " + list_text
                    processed_elems.add(id(temp_elem))
                temp_elem = temp_elem.find_next_sibling('p')
            elif 'Text1' in temp_classes:
                nested_text = temp_elem.get_text(separator=' ', strip=True)
                if nested_text:
                    concatenated_text += " " + nested_text
                    processed_elems.add(id(temp_elem))
                temp_elem = temp_elem.find_next_sibling('p')
            else:
                break
        
        return concatenated_text
    
    def _process_normal_paragraph(self, next_elem, article_heading: str, heading_consumed: bool, 
                                  processed_elems: set, article_eId: str, child_index: int):
        """Process Normal paragraph and return content dict or None."""
        text = next_elem.get_text(separator=' ', strip=True)
        if article_heading and not heading_consumed and text == article_heading:
            processed_elems.add(id(next_elem))
            return None, True, child_index
        elif text:
            processed_elems.add(id(next_elem))
            concatenated_text = self._concatenate_list_items(text, next_elem, processed_elems)
            return {
                'eId': f"{article_eId}__para_{child_index}",
                'text': concatenated_text
            }, heading_consumed, child_index + 1
        return None, heading_consumed, child_index
    
    def _process_numbered_paragraph(self, next_elem, processed_elems: set, 
                                   article_eId: str, child_index: int):
        """Process ManualNumPar1 numbered paragraph and return content dict or None."""
        text = next_elem.get_text(separator=' ', strip=True)
        if text:
            processed_elems.add(id(next_elem))
            concatenated_text = self._concatenate_list_items(text, next_elem, processed_elems)
            return {
                'eId': f"{article_eId}__para_{child_index}",
                'text': concatenated_text
            }, child_index + 1
        return None, child_index
    
    def _process_list_item(self, next_elem, processed_elems: set, 
                          article_eId: str, child_index: int):
        """Process standalone Point0/Point1 list item and return content dict or None."""
        text = next_elem.get_text(separator=' ', strip=True)
        if text:
            processed_elems.add(id(next_elem))
            return {
                'eId': f"{article_eId}__para_{child_index}",
                'text': text
            }, child_index + 1
        return None, child_index
    
    def _extract_article_content(self, article_elem, article_eId: str, 
                                article_heading: str, fait_elem):
        """Extract article content paragraphs."""
        article_content = []
        child_index = 1
        next_elem = article_elem.find_next_sibling()
        visited_divs = set()
        heading_consumed = False
        processed_elems = set()
        
        while next_elem:
            if id(next_elem) in processed_elems:
                next_elem = next_elem.find_next_sibling()
                continue
            
            if next_elem.name == 'p' and 'Fait' in next_elem.get('class', []):
                break
            
            if next_elem.name == 'p':
                elem_classes = next_elem.get('class', [])
                
                if 'Normal' in elem_classes:
                    content, heading_consumed, child_index = self._process_normal_paragraph(
                        next_elem, article_heading, heading_consumed, processed_elems, 
                        article_eId, child_index
                    )
                    if content:
                        article_content.append(content)
                elif 'li' in elem_classes and 'ManualNumPar1' in elem_classes:
                    content, child_index = self._process_numbered_paragraph(
                        next_elem, processed_elems, article_eId, child_index
                    )
                    if content:
                        article_content.append(content)
                elif ('li' in elem_classes and 'Point0' in elem_classes) or \
                     ('li' in elem_classes and 'Point1' in elem_classes):
                    content, child_index = self._process_list_item(
                        next_elem, processed_elems, article_eId, child_index
                    )
                    if content:
                        article_content.append(content)
                elif 'Titrearticle' in elem_classes:
                    break
            
            next_elem = next_elem.find_next_sibling()
            
            if not next_elem:
                parent = article_elem.find_parent('div', class_='content')
                if parent and id(parent) not in visited_divs:
                    visited_divs.add(id(parent))
                    next_div = parent.find_next_sibling('div', class_='content')
                    if next_div:
                        if next_div.find('p', class_='Fait'):
                            break
                        next_elem = next_div.find('p')
                        article_elem = next_div
                    else:
                        break
                else:
                    break
        
        return article_content
    
    def get_articles(self) -> None:
        """
        Extracts articles from the body of the legal act.
        
        Note: Due to the complex nested structure of Proposal documents
        (content divs, list concatenation, nested siblings), the full extraction
        logic remains in parser helper methods. The strategy pattern provides
        a consistent interface but delegates to parser-specific methods for
        the actual complex traversal logic.
        
        Returns
        -------
        None
            The extracted articles are stored in the 'articles' attribute.
        """
        try:
            self.articles = []
            fait_elem = self.root.find('p', class_='Fait')
            article_elements = self.root.find_all('p', class_='Titrearticle')
            
            for article_index, article_elem in enumerate(article_elements, 1):
                if self._is_after_fait(article_elem, fait_elem):
                    break
                
                article_num, article_heading = self._extract_article_number_and_heading(article_elem)
                article_eId = self._generate_article_eid(article_num, article_index)
                
                if not article_heading:
                    article_heading = self._try_extract_heading_from_next_paragraph(article_elem)
                
                article_content = self._extract_article_content(
                    article_elem, article_eId, article_heading, fait_elem
                )
                
                article_dict = {
                    'eId': article_eId,
                    'num': article_num,
                    'children': article_content
                }
                
                if article_heading:
                    article_dict['heading'] = article_heading
                
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
        """
        try:
            self.get_root(file)
            print("Root element loaded successfully.")
        except Exception as e:
            print(f"Error in get_root: {e}")
            return self
        
        try:
            self.get_metadata()
        except Exception as e:
            print(f"Error in get_metadata: {e}")
        
        try:
            self.get_explanatory_memorandum()
        except Exception as e:
            print(f"Error in get_explanatory_memorandum: {e}")
        
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