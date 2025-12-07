from tulit.parsers.html.xhtml import HTMLParser
import json
import re
import argparse
from typing import Optional, Any
from tulit.parsers.parser import LegalJSONValidator
import logging


class CellarStandardHTMLParser(HTMLParser):
    """
    Parser for standard HTML format documents from EU Cellar.
    This format wraps content in <TXT_TE> tags with simple <p> structure,
    unlike the semantic XHTML format with class-based structure.
    """
    
    def __init__(self) -> None:
        super().__init__()
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        # Remove consolidation markers (▼B, ▼M1, ▼M2, etc.)
        text = re.sub(r'▼[A-Z]\d*', '', text)
        # Replace multiple whitespaces with single space
        text = re.sub(r'\s+', ' ', text).strip()
        # Fix spacing before punctuation
        text = re.sub(r'\s+([.,!?;:\'])', r'\1', text)
        return text
    
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
        In standard HTML, the preamble typically includes the decision-making body,
        references, and recitals.
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
                self.logger.info("Preamble container found (standard format).")
            else:
                # Consolidated format - use body element
                body = self.root.find('body')
                if body:
                    self.txt_te = body
                    self.preamble = body
                    self.is_consolidated = True
                    self.logger.info("Preamble container found (consolidated format).")
                else:
                    self.preamble = None
                    self.logger.warning("No preamble container found.")
        except Exception as e:
            self.preamble = None
            self.logger.error(f"Error extracting preamble: {e}")
    
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
            
            for p in paragraphs:
                text = self._clean_text(p.get_text())
                # Look for citation patterns
                if text.startswith('Having regard to') or text.startswith('Having considered'):
                    citation_idx += 1
                    self.citations.append({
                        'eId': f'cit_{citation_idx}',
                        'text': text
                    })
            
            self.logger.info(f"Extracted {len(self.citations)} citations.")
        except Exception as e:
            self.citations = []
            self.logger.error(f"Error extracting citations: {e}")
    
    def get_recitals(self):
        """
        Extract recitals (whereas clauses).
        Usually starts with "Whereas:" followed by numbered items.
        """
        try:
            if not hasattr(self, 'txt_te') or not self.txt_te:
                self.recitals = []
                return
            
            self.recitals = []
            
            # Check for consolidated format with table-based recitals
            tables = self.txt_te.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) == 2:
                        # First column might be recital number
                        num_text = self._clean_text(cols[0].get_text())
                        content_text = self._clean_text(cols[1].get_text())
                        
                        # Check if it's a numbered recital (1), (2), etc.
                        if re.match(r'^\(?\d+\)?$', num_text):
                            recital_num = re.sub(r'[()]', '', num_text)
                            self.recitals.append({
                                'eId': f'rct_{recital_num}',
                                'text': content_text
                            })
            
            # If no recitals found in tables, try paragraph-based extraction
            if not self.recitals:
                paragraphs = self.txt_te.find_all('p')
                
                in_recitals = False
                
                for p in paragraphs:
                    text = self._clean_text(p.get_text())
                    
                    # Check if we're entering the recitals section
                    if text.strip() == 'Whereas:':
                        in_recitals = True
                        continue
                    
                    # Check if we're exiting recitals (usually at "HAS ADOPTED")
                    if in_recitals and re.match(r'^(HAS ADOPTED|HAS DECIDED|Article)', text, re.IGNORECASE):
                        in_recitals = False
                        break
                    
                    # Extract numbered recitals like "(1) Some text"
                    if in_recitals:
                        match = re.match(r'^\((\d+)\)\s*(.+)$', text)
                        if match:
                            recital_num = match.group(1)
                            recital_text = match.group(2)
                            self.recitals.append({
                                'eId': f'rct_{recital_num}',
                                'text': recital_text
                            })
            
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
        Extract articles from the document.
        Articles typically start with "Article X" followed by optional title and content.
        """
        try:
            if not hasattr(self, 'txt_te') or not self.txt_te:
                self.articles = []
                self.logger.warning("No container found for article extraction.")
                return
            
            self.articles = []
            
            # Use different extraction method based on document type
            if hasattr(self, 'is_consolidated') and self.is_consolidated:
                self._extract_articles_consolidated()
            else:
                self._extract_articles_standard()
            
            self.logger.info(f"Extracted {len(self.articles)} articles.")
            
        except Exception as e:
            self.articles = []
            self.logger.error(f"Error extracting articles: {e}")
    
    def _extract_articles_standard(self):
        """Extract articles from standard HTML format (with TXT_TE tags)."""
        # Get all children elements (paragraphs, tables, etc.)
        elements = self.txt_te.find_all(['p', 'table'], recursive=False)
        
        current_article = None
        article_content = []
        
        for element in elements:
            if element.name == 'table':
                # Handle tables
                if current_article:
                    # Table belongs to current article
                    table_text = self._extract_table_text(element)
                    if table_text:
                        article_content.append(f"[TABLE]\n{table_text}")
                continue
            
            # Handle paragraphs
            text = self._clean_text(element.get_text())
            
            # Check if this is the start of a new article
            article_num, remaining = self._extract_article_number(text)
            
            if article_num:
                # Save previous article if exists
                if current_article:
                    self._finalize_article(current_article, article_content)
                    article_content = []
                
                # Start new article
                current_article = {
                    'eId': f'art_{article_num}',
                    'num': f'Article {article_num}',
                    'heading': None,
                    'children': []
                }
                
                # Check if there's a title on the same line
                if remaining:
                    current_article['heading'] = remaining
            
            elif current_article:
                # Check if this is signature or footnote section
                if self._is_signature_section(text) or self._is_footnote(text):
                    # Stop collecting article content - finalize current article and break
                    self._finalize_article(current_article, article_content)
                    current_article = None
                    break
                # This is content of the current article
                if text:  # Only add non-empty content
                    article_content.append(text)
            else:
                # No current article - check if we've reached signature/footnote section
                if self._is_signature_section(text) or self._is_footnote(text):
                    break
        
        # Finalize the last article if not already finalized
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
    
    def _extract_articles_consolidated(self):
        """Extract articles from consolidated HTML format (styled paragraphs)."""
        # Get all children elements (paragraphs, tables, etc.)
        elements = self.txt_te.find_all(['p', 'table'], recursive=False)
        
        current_article = None
        article_content = []
        
        for i, element in enumerate(elements):
            if element.name == 'table':
                # Handle tables
                if current_article:
                    # Table belongs to current article
                    table_text = self._extract_table_text(element)
                    if table_text:
                        article_content.append(f"[TABLE]\n{table_text}")
                continue
            
            # Handle paragraphs
            text = self._clean_text(element.get_text())
            style = element.get('style', '')
            
            # Check if this is an article number (italic, centered)
            if 'italic' in style and 'center' in style:
                article_num, remaining = self._extract_article_number(text)
                
                if article_num:
                    # Save previous article if exists
                    if current_article:
                        self._finalize_article(current_article, article_content)
                        article_content = []
                    
                    # Start new article
                    current_article = {
                        'eId': f'art_{article_num}',
                        'num': f'Article {article_num}',
                        'heading': None,
                        'children': []
                    }
                    
                    # Next element might be the heading (bold, centered)
                    if i + 1 < len(elements):
                        next_elem = elements[i + 1]
                        if next_elem.name == 'p':
                            next_style = next_elem.get('style', '')
                            if 'bold' in next_style and 'center' in next_style:
                                current_article['heading'] = self._clean_text(next_elem.get_text())
            
            elif current_article:
                # Check if this is signature or footnote section
                if self._is_signature_section(text) or self._is_footnote(text):
                    # Stop collecting article content - finalize current article and break
                    self._finalize_article(current_article, article_content)
                    current_article = None
                    break
                # This might be article content
                # Skip if it's the heading we already captured
                if current_article['heading'] and text == current_article['heading']:
                    continue
                
                # Add content paragraphs
                if text and 'center' not in style and 'italic' not in style:
                    article_content.append(text)
            else:
                # No current article - check if we've reached signature/footnote section
                if self._is_signature_section(text) or self._is_footnote(text):
                    break
        
        # Finalize the last article if not already finalized
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
    
    def get_conclusions(self):
        """
        Extract conclusion text (e.g., "Done at Brussels, ...").
        """
        try:
            if not hasattr(self, 'txt_te') or not self.txt_te:
                self.conclusions = None
                return
            
            paragraphs = self.txt_te.find_all('p')
            
            # Look for conclusion patterns, typically near the end
            for i in range(len(paragraphs) - 1, max(len(paragraphs) - 20, -1), -1):
                text = self._clean_text(paragraphs[i].get_text())
                if re.match(r'^Done at', text, re.IGNORECASE):
                    # Collect this and subsequent paragraphs as conclusion
                    conclusion_parts = []
                    for j in range(i, len(paragraphs)):
                        conclusion_parts.append(self._clean_text(paragraphs[j].get_text()))
                    self.conclusions = ' '.join(conclusion_parts)
                    self.logger.info("Conclusions extracted.")
                    return
            
            self.conclusions = None
            self.logger.warning("No conclusions found.")
        except Exception as e:
            self.conclusions = None
            self.logger.error(f"Error extracting conclusions: {e}")
    
    def parse(self, file_path, validate=False):
        """
        Parse a standard HTML document and extract all components.
        If the input is a directory, searches for HTML files.
        
        Parameters
        ----------
        file_path : str
            Path to the HTML file or directory containing HTML files
        validate : bool, optional
            Whether to validate against LegalJSON schema (default: False)
        
        Returns
        -------
        dict
            Parsed document in LegalJSON-compatible format
        """
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
                return {'articles': []}  # Return empty result
        
        try:
            # Load and parse HTML
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
            
            # Build result dictionary
            result = {
                'preface': self.preface,
                'preamble': {
                    'formula': self.formula,
                    'citations': self.citations,
                    'recitals': self.recitals,
                    'preamble_final': self.preamble_final
                },
                'chapters': self.chapters,
                'articles': self.articles,
                'conclusions': self.conclusions
            }
            
            # Validate if requested
            if validate:
                validator = LegalJSONValidator()
                is_valid, errors = validator.validate(result)
                if not is_valid:
                    self.logger.warning(f"Validation failed: {errors}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing document: {e}")
            raise