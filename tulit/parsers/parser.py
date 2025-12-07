from abc import ABC
import jsonschema
import json
import logging
from typing import Any, Optional
from logging import Logger

class Parser(ABC):
    """
    Abstract base class for parsers
    
    Attributes
    ----------
    root : lxml.etree._Element or bs4.BeautifulSoup
        Root element of the XML or HTML document.
    preface : str or None
        Extracted preface text from the document.
    preamble : lxml.etree.Element or bs4.Tag or None
        The preamble section of the document.
    formula : str or None
        The formula element extracted from the preamble.
    citations : list or None
        List of extracted citations from the preamble.
    recitals : list or None
        List of extracted recitals from the preamble.
    preamble_final : str or None
        The final preamble text extracted from the document.
    body : lxml.etree.Element or bs4.Tag or None
        The body section of the document.
    chapters : list or None
        List of extracted chapters from the body.
    articles : list or None
        List of extracted articles from the body. Each article is a dictionary with keys:
        - 'eId': Article identifier
        - 'text': Article text
        - 'children': List of child elements of the article
    conclusions : None or dict
        Extracted conclusions from the body.
    """
    
    def __init__(self) -> None:
        """
        Initializes the Parser object.

        Parameters
        ----------
        None
        """
        # Initialize logger with fully qualified class name
        self.logger: Logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
       
        self.root: Any = None  # Can be lxml.etree._Element or bs4.BeautifulSoup
        self.preface: Optional[str] = None

        self.preamble: Any = None  # Can be lxml.etree.Element or bs4.Tag
        self.formula: Optional[str] = None
        self.citations: list[dict[str, str]] = []
        self.recitals_init: Optional[str] = None
        self.recitals: list[dict[str, str]] = []
        self.preamble_final: Optional[str] = None
    
        self.body: Any = None  # Can be lxml.etree.Element or bs4.Tag
        self.chapters: list[dict[str, Any]] = []
        self.articles: list[dict[str, Any]] = []
        self.conclusions: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the parser's extracted data to a dictionary.

        Returns
        -------
        dict
            A dictionary containing all extracted elements from the document:
            - 'preface': Extracted preface text
            - 'preamble': Dictionary containing preamble components:
                - 'formula': The formula text
                - 'citations': List of citations
                - 'recitals': List of recitals
                - 'final': Final preamble text
            - 'body': Dictionary containing body components:
                - 'chapters': List of chapters
                - 'articles': List of articles
            - 'conclusions': Extracted conclusions
        """
        return {
            'preface': self.preface,
            'preamble': self.preamble,
            'formula': self.formula,
            'citations': self.citations,
            'recitals': self.recitals,
            'preamble_final': self.preamble_final,
            'chapters': self.chapters,
            'articles': self.articles,            
            'conclusions': self.conclusions
        }

class LegalJSONValidator:
    """
    Validator for LegalJSON output using the LegalJSON schema.
    """
    def __init__(self, schema_path: Optional[str] = None) -> None:
        if schema_path is None:
            import os
            schema_path = os.path.join(os.path.dirname(__file__), 'legaljson_schema.json')
        with open(schema_path, 'r', encoding='utf-8') as f:
            self.schema: dict[str, Any] = json.load(f)
        self.logger: Logger = logging.getLogger(self.__class__.__name__)

    def validate(self, data: dict[str, Any]) -> bool:
        """
        Validate a LegalJSON object against the LegalJSON schema.
        Returns True if valid, False otherwise.
        """
        try:
            jsonschema.validate(instance=data, schema=self.schema)
            self.logger.info("LegalJSON validation successful.")
            return True
        except jsonschema.ValidationError as e:
            self.logger.error(f"LegalJSON validation error: {e.message}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during LegalJSON validation: {e}")
            return False
