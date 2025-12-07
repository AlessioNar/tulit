from tulit.parsers.html.xhtml import HTMLParser
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
            # Find the explanatory memorandum title
            em_title = self.root.find('p', class_='Exposdesmotifstitre')
            if em_title:
                self.explanatory_memorandum['title'] = em_title.get_text(strip=True)
            
            # Find all sections - we'll process them in order
            sections = []
            current_section = None
            
            # Find all Rfrenceinterinstitutionnelle to know where explanatory memorandum ends
            all_refs = self.root.find_all('p', class_='Rfrenceinterinstitutionnelle')
            # If there are 2, the second marks the start of the legal act
            end_marker = all_refs[1] if len(all_refs) > 1 else None
            
            # Get all content divs
            content_divs = self.root.find_all('div', class_='content')
            
            for content_div in content_divs:
                # Stop processing if we've reached the legal act
                if end_marker and end_marker in content_div.find_all('p'):
                    break
                # Process all paragraphs in this div
                for element in content_div.find_all(['p', 'table']):
                    # Check class names
                    classes = element.get('class', [])
                    
                    # Main heading (level 1)
                    if 'li' in classes and 'ManualHeading1' in classes:
                        # Save previous section if exists
                        if current_section:
                            sections.append(current_section)
                        
                        # Start new section
                        num_elem = element.find('span', class_='num')
                        text_elem = element.find_all('span')[-1] if element.find_all('span') else element
                        
                        current_section = {
                            'level': 1,
                            'number': num_elem.get_text(strip=True) if num_elem else None,
                            'heading': text_elem.get_text(strip=True),
                            'content': []
                        }
                    
                    # Sub-heading (level 2)
                    elif 'li' in classes and 'ManualHeading2' in classes:
                        num_elem = element.find('span', class_='num')
                        text_spans = element.find_all('span')
                        heading_text = ' '.join([s.get_text(strip=True) for s in text_spans if s.get('class') != ['num']])
                        
                        subsection = {
                            'level': 2,
                            'number': num_elem.get_text(strip=True) if num_elem else None,
                            'heading': heading_text,
                            'content': []
                        }
                        
                        if current_section:
                            current_section['content'].append(subsection)
                    
                    # Sub-heading (level 3)
                    elif 'li' in classes and 'ManualHeading3' in classes:
                        num_elem = element.find('span', class_='num')
                        text_spans = element.find_all('span')
                        heading_text = ' '.join([s.get_text(strip=True) for s in text_spans if s.get('class') != ['num']])
                        
                        subsection = {
                            'level': 3,
                            'number': num_elem.get_text(strip=True) if num_elem else None,
                            'heading': heading_text,
                            'content': []
                        }
                        
                        if current_section:
                            # Add to last level 2 subsection if exists, otherwise to main section
                            if current_section['content'] and isinstance(current_section['content'][-1], dict) and current_section['content'][-1].get('level') == 2:
                                current_section['content'][-1]['content'].append(subsection)
                            else:
                                current_section['content'].append(subsection)
                    
                    # Numbered paragraph
                    elif 'li' in classes and 'ManualNumPar1' in classes:
                        num_elem = element.find('span', class_='num')
                        # Get all text, removing the number span
                        text = element.get_text(separator=' ', strip=True)
                        if num_elem:
                            num_text = num_elem.get_text(strip=True)
                            text = text.replace(num_text, '', 1).strip()
                        
                        paragraph = {
                            'type': 'numbered_paragraph',
                            'number': num_elem.get_text(strip=True) if num_elem else None,
                            'text': text
                        }
                        
                        if current_section:
                            # Add to the deepest subsection available
                            if current_section['content'] and isinstance(current_section['content'][-1], dict):
                                last_item = current_section['content'][-1]
                                if last_item.get('level') == 2 and last_item.get('content'):
                                    if isinstance(last_item['content'][-1], dict) and last_item['content'][-1].get('level') == 3:
                                        last_item['content'][-1]['content'].append(paragraph)
                                    else:
                                        last_item['content'].append(paragraph)
                                elif last_item.get('level') in [2, 3]:
                                    last_item['content'].append(paragraph)
                                else:
                                    current_section['content'].append(paragraph)
                            else:
                                current_section['content'].append(paragraph)
                    
                    # Normal paragraph
                    elif 'Normal' in classes:
                        text = element.get_text(separator=' ', strip=True)
                        if text:  # Only add non-empty paragraphs
                            paragraph = {
                                'type': 'paragraph',
                                'text': text
                            }
                            
                            if current_section:
                                # Add to the deepest subsection available
                                if current_section['content'] and isinstance(current_section['content'][-1], dict):
                                    last_item = current_section['content'][-1]
                                    if last_item.get('level') == 2 and last_item.get('content'):
                                        if isinstance(last_item['content'][-1], dict) and last_item['content'][-1].get('level') == 3:
                                            last_item['content'][-1]['content'].append(paragraph)
                                        else:
                                            last_item['content'].append(paragraph)
                                    elif last_item.get('level') in [2, 3]:
                                        last_item['content'].append(paragraph)
                                    else:
                                        current_section['content'].append(paragraph)
                                else:
                                    current_section['content'].append(paragraph)
                    
                    # Handle tables
                    elif element.name == 'table':
                        table_data = []
                        rows = element.find_all('tr')
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            row_data = [cell.get_text(separator=' ', strip=True) for cell in cells]
                            if any(row_data):  # Only add non-empty rows
                                table_data.append(row_data)
                        
                        if table_data:
                            table_obj = {
                                'type': 'table',
                                'data': table_data
                            }
                            
                            if current_section:
                                if current_section['content'] and isinstance(current_section['content'][-1], dict):
                                    last_item = current_section['content'][-1]
                                    if last_item.get('level') in [2, 3]:
                                        last_item['content'].append(table_obj)
                                    else:
                                        current_section['content'].append(table_obj)
                                else:
                                    current_section['content'].append(table_obj)
            
            # Don't forget to add the last section
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
    
    def get_articles(self) -> None:
        """
        Extracts articles from the body of the legal act.
        Articles may span multiple content divs.
        
        Returns
        -------
        None
            The extracted articles are stored in the 'articles' attribute.
        """
        try:
            self.articles = []
            
            # Find the Fait element to know where articles end
            fait_elem = self.root.find('p', class_='Fait')
            
            # Find all article titles across all content divs
            article_elements = self.root.find_all('p', class_='Titrearticle')
            
            for article_index, article_elem in enumerate(article_elements, 1):
                # Stop if we've reached the Fait (conclusions) section
                # Check if this article comes after Fait by comparing positions in document
                if fait_elem:
                    # Get all elements and compare positions
                    all_elems = list(self.root.descendants)
                    try:
                        article_pos = all_elems.index(article_elem)
                        fait_pos = all_elems.index(fait_elem)
                        if article_pos >= fait_pos:
                            # This article is after Fait, stop processing
                            break
                    except (ValueError, AttributeError):
                        # If we can't compare positions, continue
                        pass
                
                # Extract article number and heading from the Titrearticle element
                # The article element can have various structures:
                # 1. <span>Article X</span><br/><span>Heading</span>
                # 2. <span> </span><span>Article X</span><br/><span>Heading parts...</span>
                # We need to find the "Article X" span and everything after the <br/>
                
                import re
                
                # Get all text parts before and after <br/>
                br_elem = article_elem.find('br')
                if br_elem:
                    # Find all spans before br
                    before_br = []
                    for elem in article_elem.children:
                        if elem == br_elem:
                            break
                        if hasattr(elem, 'get_text'):
                            text = elem.get_text(strip=True)
                            if text:
                                before_br.append(text)
                    
                    # Find all spans after br
                    after_br = []
                    found_br = False
                    for elem in article_elem.children:
                        if elem == br_elem:
                            found_br = True
                            continue
                        if found_br and hasattr(elem, 'get_text'):
                            text = elem.get_text(strip=True)
                            if text:
                                after_br.append(text)
                    
                    # Article number is the part containing "Article X"
                    article_num = ' '.join(before_br)
                    # Heading is everything after br
                    article_heading = ' '.join(after_br) if after_br else None
                else:
                    # No <br/>, use fallback
                    article_num = article_elem.get_text(strip=True)
                    article_heading = None
                
                # Generate eId from article number (e.g., "Article 1" -> "art_1")
                article_num_match = re.search(r'Article\s+(\d+)', article_num)
                if article_num_match:
                    article_eId = f"art_{article_num_match.group(1)}"
                else:
                    article_eId = f"art_{article_index}"
                
                # If no heading was found in the Titrearticle, check if next element is a Normal paragraph with the heading
                if not article_heading:
                    next_p = article_elem.find_next_sibling('p')
                    if next_p and 'Normal' in next_p.get('class', []):
                        # Check if this looks like a heading (short text, often one word)
                        potential_heading = next_p.get_text(strip=True)
                        # Simple heuristic: if it's short (< 100 chars) and the following element is also Normal, it's likely a heading
                        if len(potential_heading) < 100:
                            following_p = next_p.find_next_sibling('p')
                            if following_p and 'Normal' in following_p.get('class', []):
                                article_heading = potential_heading
                
                # Find the next Normal paragraph(s) that belong to this article
                article_content = []
                child_index = 1  # Counter for generating child eIds
                next_elem = article_elem.find_next_sibling()
                visited_divs = set()  # Track visited divs to prevent infinite loops
                heading_consumed = False  # Track if we've consumed the heading paragraph
                processed_elems = set()  # Track elements already processed to avoid duplication
                
                while next_elem:
                    # Skip if already processed
                    if id(next_elem) in processed_elems:
                        next_elem = next_elem.find_next_sibling()
                        continue
                    
                    # Check if we've reached the Fait section
                    if next_elem.name == 'p' and 'Fait' in next_elem.get('class', []):
                        break
                    
                    # Check if it's a paragraph element
                    if next_elem.name == 'p':
                        elem_classes = next_elem.get('class', [])
                        if 'Normal' in elem_classes:
                            text = next_elem.get_text(separator=' ', strip=True)
                            # Skip if this is the heading paragraph we already extracted
                            if article_heading and not heading_consumed and text == article_heading:
                                heading_consumed = True
                                processed_elems.add(id(next_elem))
                            elif text:
                                # Check if this is followed by list items that should be concatenated
                                concatenated_text = text
                                processed_elems.add(id(next_elem))
                                temp_elem = next_elem.find_next_sibling('p')
                                temp_visited_divs = set()
                                
                                # Look ahead to see if there are Point0/Point1/Text1 list items to concatenate
                                while temp_elem or True:  # Continue even if temp_elem is None (to check next div)
                                    if not temp_elem:
                                        # No more siblings, try next content div
                                        parent = next_elem.find_parent('div', class_='content')
                                        if parent and id(parent) not in temp_visited_divs:
                                            temp_visited_divs.add(id(parent))
                                            next_div = parent.find_next_sibling('div', class_='content')
                                            if next_div:
                                                temp_elem = next_div.find('p')
                                                next_elem = next_div  # Update reference for next iteration
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
                                        # Also capture Text1 (nested under Point0/Point1)
                                        nested_text = temp_elem.get_text(separator=' ', strip=True)
                                        if nested_text:
                                            concatenated_text += " " + nested_text
                                            processed_elems.add(id(temp_elem))
                                        temp_elem = temp_elem.find_next_sibling('p')
                                    else:
                                        break
                                
                                article_content.append({
                                    'eId': f"{article_eId}__para_{child_index}",
                                    'text': concatenated_text
                                })
                                child_index += 1
                        elif 'li' in elem_classes and 'ManualNumPar1' in elem_classes:
                            # Numbered paragraphs within articles
                            text = next_elem.get_text(separator=' ', strip=True)
                            if text:
                                # Check if this is followed by list items (Point0/Point1) that should be concatenated
                                concatenated_text = text
                                processed_elems.add(id(next_elem))
                                temp_elem = next_elem.find_next_sibling('p')
                                temp_visited_divs = set()
                                
                                # Look ahead to see if there are Point0/Point1/Text1 list items to concatenate
                                while temp_elem or True:  # Continue even if temp_elem is None (to check next div)
                                    if not temp_elem:
                                        # No more siblings, try next content div
                                        parent = next_elem.find_parent('div', class_='content')
                                        if parent and id(parent) not in temp_visited_divs:
                                            temp_visited_divs.add(id(parent))
                                            next_div = parent.find_next_sibling('div', class_='content')
                                            if next_div:
                                                temp_elem = next_div.find('p')
                                                next_elem = next_div  # Update reference for next iteration
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
                                        # Also capture Text1 (nested under Point0/Point1)
                                        nested_text = temp_elem.get_text(separator=' ', strip=True)
                                        if nested_text:
                                            concatenated_text += " " + nested_text
                                            processed_elems.add(id(temp_elem))
                                        temp_elem = temp_elem.find_next_sibling('p')
                                    else:
                                        break
                                
                                article_content.append({
                                    'eId': f"{article_eId}__para_{child_index}",
                                    'text': concatenated_text
                                })
                                child_index += 1
                        elif ('li' in elem_classes and 'Point0' in elem_classes) or ('li' in elem_classes and 'Point1' in elem_classes):
                            # These should have been processed with their parent Normal paragraph
                            # If we reach here, treat them as standalone
                            text = next_elem.get_text(separator=' ', strip=True)
                            if text:
                                article_content.append({
                                    'eId': f"{article_eId}__para_{child_index}",
                                    'text': text
                                })
                                child_index += 1
                                processed_elems.add(id(next_elem))
                        elif 'Titrearticle' in elem_classes:
                            # Next article found, stop
                            break
                    
                    # Move to next sibling
                    next_elem = next_elem.find_next_sibling()
                    
                    # If no more siblings, try next content div (but prevent infinite loops)
                    if not next_elem:
                        parent = article_elem.find_parent('div', class_='content')
                        if parent and id(parent) not in visited_divs:
                            visited_divs.add(id(parent))
                            next_div = parent.find_next_sibling('div', class_='content')
                            if next_div:
                                # Check if next_div contains Fait element - if so, stop
                                if next_div.find('p', class_='Fait'):
                                    break
                                next_elem = next_div.find('p')
                                # Update parent reference for next iteration
                                article_elem = next_div
                            else:
                                break
                        else:
                            break
                
                article_dict = {
                    'eId': article_eId,
                    'num': article_num,
                    'children': article_content
                }
                
                # Only add heading if it exists
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


def main():
    parser = argparse.ArgumentParser(description='Parse a Commission proposal XHTML document and output the results to a JSON file.')
    parser.add_argument('--input', type=str, default='tests/data/eurlex/commission_proposals_html/COM(2025)6.html', help='Path to the proposal XHTML file to parse.')
    parser.add_argument('--output', type=str, default='tests/data/json/proposal_html.json', help='Path to the output JSON file.')
    args = parser.parse_args()
    
    html_parser = ProposalHTMLParser()
    html_parser.parse(args.input)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        # Create a dictionary following the LegalJSON schema structure
        legaljson_dict = {
            "preface": html_parser.preface,
            "preamble": None,  # According to schema, preamble should be string or null, not object
            "formula": html_parser.formula,
            "citations": html_parser.citations if hasattr(html_parser, 'citations') else [],
            "recitals": html_parser.recitals if hasattr(html_parser, 'recitals') else [],
            "preamble_final": html_parser.preamble_final if hasattr(html_parser, 'preamble_final') else None,
            "chapters": html_parser.chapters if hasattr(html_parser, 'chapters') else [],
            "articles": html_parser.articles if hasattr(html_parser, 'articles') else [],
            "conclusions": html_parser.conclusions if hasattr(html_parser, 'conclusions') else None
        }
        
        # Write to a JSON file
        json.dump(legaljson_dict, f, ensure_ascii=False, indent=4)
    
    print(f"Parsing complete. Output written to {args.output}")

if __name__ == "__main__":
    main()
