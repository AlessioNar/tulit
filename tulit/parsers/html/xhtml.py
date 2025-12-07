from bs4 import BeautifulSoup
from tulit.parsers.parser import Parser
import json
import argparse
import logging
from tulit.parsers.parser import LegalJSONValidator

class HTMLParser(Parser):
    def __init__(self):
        """
        Initializes the HTML parser and sets up the BeautifulSoup instance.
        """
        super().__init__()
        
    def get_root(self, file):
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
            print("HTML loaded successfully.")
        except Exception as e:
            print(f"Error loading HTML: {e}")
            

    def parse(self, file: str) -> Parser:
        """
        Parses an HTML file and extracts the preface, preamble, formula, citations, recitals, preamble final, body, chapters, articles, and conclusions.
        
        Parameters
        ----------
        file : str
            Path to the XML file to parse.
        
        Returns
        -------
        Parser
            The parser object with the parsed elements stored in the attributes.
        """
            
        try:
            self.get_root(file)
            print("Root element loaded successfully.")
        except Exception as e:
            print(f"Error in get_root: {e}")
            
        try:
            self.get_preface()
            print(f"Preface parsed successfully. Preface: {self.preface}")
        except Exception as e:
            print(f"Error in get_preface: {e}")
        
        try:
            self.get_preamble()
            print(f"Preamble element found.")
        except Exception as e:
            print(f"Error in get_preamble: {e}")
        try:
            self.get_formula()
            print(f"Formula parsed successfully.")
        except Exception as e:
            print(f"Error in get_formula: {e}")
        try:
            self.get_citations()
            print(f"Citations parsed successfully. Number of citations: {len(self.citations)}")
        except Exception as e:
            print(f"Error in get_citations: {e}")
        try:
            self.get_recitals()
            print(f"Recitals parsed successfully. Number of recitals: {len(self.recitals)}")
        except Exception as e:
            print(f"Error in get_recitals: {e}")
        
        try:
            self.get_preamble_final()
            print(f"Preamble final parsed successfully.")
        except Exception as e:
            print(f"Error in get_preamble_final: {e}")
        
        try:
            self.get_body()
            print("Body element found.")
        except Exception as e:
            print(f"Error in get_body: {e}")
        try:
            self.get_chapters()
            print(f"Chapters parsed successfully. Number of chapters: {len(self.chapters)}")
        except Exception as e:
            print(f"Error in get_chapters: {e}")
        try:
            self.get_articles()
            print(f"Articles parsed successfully. Number of articles: {len(self.articles)}")
            print(f"Total number of children in articles: {sum([len(list(article)) for article in self.articles])}")                        
            
        except Exception as e:
            print(f"Error in get_articles: {e}")
        try:
            self.get_conclusions()                    
            print(f"Conclusions parsed successfully. ")
        except Exception as e:
            print(f"Error in get_conclusions: {e}")
        
        return self