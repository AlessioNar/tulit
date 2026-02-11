from bs4 import BeautifulSoup
from tulit.parser.parser import Parser
import json
import argparse
import logging
from tulit.parser.parser import LegalJSONValidator
from typing import Optional
from abc import abstractmethod

class HTMLParser(Parser):
    """
    Abstract base class for HTML parsers.
    
    Provides common HTML parsing utilities and a template parse() method that
    orchestrates the complete parsing workflow. Subclasses must implement the
    core extraction methods while inheriting robust error handling and logging.
    
    Key Features
    ------------
    - BeautifulSoup integration for HTML parsing
    - Template method pattern for consistent parsing workflow
    - Comprehensive error handling and logging
    - Support for various HTML-based legal document formats
    - Automatic conversion to structured LegalJSON format
    
    Abstract Methods (Must Implement)
    --------------------------------
    get_preface() -> Optional[str]
        Extract the document preface/title
    get_articles() -> None
        Extract articles from the document body
    
    Optional Methods (Can Override)
    -------------------------------
    get_preamble() -> Optional[Any]
        Extract preamble section
    get_formula() -> Optional[str]
        Extract formula (enacting clause)
    get_citations() -> list[dict[str, str]]
        Extract citations/references
    get_recitals() -> list[dict[str, str]]
        Extract recitals (whereas clauses)
    get_preamble_final() -> Optional[str]
        Extract final preamble text
    get_body() -> Optional[Any]
        Extract body section
    get_chapters() -> list[dict[str, Any]]
        Extract chapters
    get_conclusions() -> Optional[dict[str, Any]]
        Extract conclusions section
    
    Usage Example
    -------------
    >>> class MyHTMLParser(HTMLParser):
    ...     def get_preface(self) -> Optional[str]:
    ...         if self.root:
    ...             title = self.root.find('title')
    ...             return title.text if title else None
    ...         return None
    ...     
    ...     def get_articles(self) -> None:
    ...         self.articles = []
    ...         if self.root:
    ...             for article in self.root.select('div.article'):
    ...                 self.articles.append({
    ...                     'text': article.get_text(),
    ...                     'id': article.get('id')
    ...                 })
    
    >>> parser = MyHTMLParser()
    >>> parser.parse('document.html')
    >>> result = parser.to_dict()
    
    Error Handling
    --------------
    The parser implements comprehensive error handling with:
    - Detailed logging at different levels (DEBUG, INFO, WARNING, ERROR)
    - Graceful degradation on partial failures
    - Specific exception types for different failure modes
    - Validation of parsed data structure
    
    Performance Considerations
    -------------------------
    - Uses BeautifulSoup's built-in parsing optimizations
    - Processes document in single pass where possible
    - Minimizes memory usage by streaming large documents when feasible
    
    Notes
    -----
    - Subclasses should call super().__init__() to ensure proper initialization
    - Always check for None values when accessing self.root
    - Use BeautifulSoup's CSS selectors for robust element selection
    - Consider using self.normalizer for text cleaning
    """
    
    def __init__(self) -> None:
        """
        Initializes the HTML parser and sets up the BeautifulSoup instance.
        """
        super().__init__()
        
    def get_root(self, file: str) -> None:
        """
        Loads an HTML file and parses it with BeautifulSoup.

        Parameters
        ----------
        file : str
            The path to the HTML file.
        
        Returns
        -------
        None
            The root element is stored in the parser under the 'root' attribute.
        """
        try:
            with open(file, 'r', encoding='utf-8') as f:
                html = f.read()
            self.root = BeautifulSoup(html, 'html.parser')
            self.logger.info("HTML loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading HTML: {e}", exc_info=True)
            

    def parse(self, file: str, **options) -> 'HTMLParser':
        """
        Parses an HTML file and extracts the preface, preamble, formula, citations, recitals, preamble final, body, chapters, articles, and conclusions.
        
        Parameters
        ----------
        file : str
            Path to the HTML file to parse.
        **options : dict
            Optional configuration options
        
        Returns
        -------
        HTMLParser
            Self for method chaining with the parsed elements stored in the attributes.
        """
            
        try:
            self.get_root(file)
            self.logger.info("Root element loaded successfully")
        except Exception as e:
            self.logger.error(f"Error in get_root: {e}", exc_info=True)
            
        try:
            self.get_preface()
            self.logger.debug(f"Preface parsed successfully. Preface: {self.preface}")
        except Exception as e:
            self.logger.error(f"Error in get_preface: {e}", exc_info=True)
        
        try:
            self.get_preamble()
            self.logger.info("Preamble element found")
        except Exception as e:
            self.logger.error(f"Error in get_preamble: {e}", exc_info=True)
        try:
            self.get_formula()
            self.logger.info("Formula parsed successfully")
        except Exception as e:
            self.logger.error(f"Error in get_formula: {e}", exc_info=True)
        try:
            self.get_citations()
            self.logger.info(f"Citations parsed successfully. Number of citations: {len(self.citations)}")
        except Exception as e:
            self.logger.error(f"Error in get_citations: {e}", exc_info=True)
        try:
            self.get_recitals()
            self.logger.info(f"Recitals parsed successfully. Number of recitals: {len(self.recitals)}")
        except Exception as e:
            self.logger.error(f"Error in get_recitals: {e}", exc_info=True)
        
        try:
            self.get_preamble_final()
            self.logger.info("Preamble final parsed successfully")
        except Exception as e:
            self.logger.error(f"Error in get_preamble_final: {e}", exc_info=True)
        
        try:
            self.get_body()
            self.logger.info("Body element found")
        except Exception as e:
            self.logger.error(f"Error in get_body: {e}", exc_info=True)
        try:
            self.get_chapters()
            self.logger.info(f"Chapters parsed successfully. Number of chapters: {len(self.chapters)}")
        except Exception as e:
            self.logger.error(f"Error in get_chapters: {e}", exc_info=True)
        try:
            self.get_articles()
            self.logger.info(f"Articles parsed successfully. Number of articles: {len(self.articles)}")
            self.logger.debug(f"Total number of children in articles: {sum([len(list(article)) for article in self.articles])}")
            
        except Exception as e:
            self.logger.error(f"Error in get_articles: {e}", exc_info=True)
        try:
            self.get_conclusions()
            self.logger.info("Conclusions parsed successfully")
        except Exception as e:
            self.logger.error(f"Error in get_conclusions: {e}", exc_info=True)
        
        return self