import os
import json
import argparse
from typing import Optional, Any
from lxml import etree
from tulit.parsers.parser import LegalJSONValidator, Parser
from tulit.parsers.xml.xml import XMLParser
from tulit.parsers.strategies.article_extraction import BOEArticleStrategy
import logging

class BOEXMLParser(XMLParser):
    """
    Parser for BOE XML documents to LegalJSON.
    
    Uses BOEArticleStrategy to extract articles, reducing code duplication
    and improving maintainability.
    """
    def __init__(self) -> None:
        super().__init__()
        self.namespaces = {}
        self.article_strategy = BOEArticleStrategy()

    def get_preface(self) -> Optional[str]:
        # Get all <p> elements in the document and filter by those under <texto>
        all_p_elements = self.root.findall('.//p')
        texto_p_elements = [p for p in all_p_elements if p.getparent() is not None and p.getparent().tag == 'texto']
        
        preface_paragraphs = []
        for p in texto_p_elements:
            p_class = p.get('class')
            text = ''.join(p.itertext()).strip()
            if p_class in ('parrafo', 'parrafo_2'):
                preface_paragraphs.append(text)
            elif p_class == 'articulo':
                break  # Stop at first article
        self.preface = '\n'.join(preface_paragraphs) if preface_paragraphs else None
        return self.preface

    def get_articles(self) -> None:
        """
        Extract articles using BOEArticleStrategy.
        
        This method delegates article extraction to the strategy pattern,
        reducing code duplication and improving testability.
        """
        self.articles = self.article_strategy.extract_articles(self.root)
        return self.articles

    def get_chapters(self) -> list:
        self.chapters = []
        return self.chapters

    def get_citations(self) -> list:
        self.citations = []
        return self.citations

    def get_recitals(self) -> list:
        self.recitals = []
        return self.recitals

    def get_preamble(self) -> None:
        self.preamble = None
        return self.preamble

    def get_formula(self) -> None:
        self.formula = None
        return self.formula

    def get_preamble_final(self) -> None:
        self.preamble_final = None
        return self.preamble_final

    def get_conclusions(self) -> None:
        self.conclusions = None
        return self.conclusions

    def parse(self, file: str, **options) -> "BOEXMLParser":
        """
        Parse a BOE XML document.
        
        Parameters
        ----------
        file : str
            Path to the BOE XML file
        **options : dict
            Optional configuration options
            
        Returns
        -------
        BOEXMLParser
            Self for method chaining
        """
        # Use secure parser from parent class
        self.get_root(file)
        
        self.get_preface()
        self.get_articles()
        self.get_chapters()
        self.get_citations()
        self.get_recitals()
        self.get_preamble()
        self.get_formula()
        self.get_preamble_final()
        self.get_conclusions()
        return self

    def to_legaljson(self) -> dict[str, Any]:
        return {
            'preface': self.preface,
            'citations': self.citations,
            'recitals': self.recitals,
            'chapters': self.chapters,
            'articles': self.articles,
            'preamble': self.preamble,
            'formula': self.formula,
            'preamble_final': self.preamble_final,
            'conclusions': self.conclusions
        }