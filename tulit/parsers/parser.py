from abc import ABC

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
    body : lxml.etree.Element or bs4.Tag or None
        The body section of the document.
    chapters : list or None
        List of extracted chapters from the body.
    articles : list or None
        List of extracted articles from the body.
    articles_text : list
        List of extracted article texts.
    conclusions : None or str
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
        self.citations = None
        self.recitals = None
        self.preamble_final = None
    
        self.body = None
        self.chapters = []
        self.articles = []
        self.conclusions = None
        
        self.articles_text = []

