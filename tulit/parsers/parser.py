from abc import ABC
import jsonschema
import json
import logging

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
    
    def __init__(self):
        """
        Initializes the Parser object.

        Parameters
        ----------
        None
        """
       
        self.root = None 
        self.preface = None

        self.preamble = None        
        self.formula = None    
        self.citations = []
        self.recitals_init = None
        self.recitals = []
        self.preamble_final = None
    
        self.body = None
        self.chapters = []
        self.articles = []
        self.conclusions = None

class LegalJSONValidator:
    """
    Validator for LegalJSON output using the LegalJSON schema.
    """
    def __init__(self, schema_path=None):
        if schema_path is None:
            import os
            schema_path = os.path.join(os.path.dirname(__file__), 'legaljson_schema.json')
        with open(schema_path, 'r', encoding='utf-8') as f:
            self.schema = json.load(f)
        self.logger = logging.getLogger(self.__class__.__name__)

    def validate(self, data):
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
