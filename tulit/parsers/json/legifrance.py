"""
Parser for Legifrance JSON format to LegalJSON format.

This module converts JSON documents from the French Legifrance API
(codes, laws, decrees) into the standardized LegalJSON format.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path


class LegifranceParser:
    """
    Parser for Legifrance JSON documents.
    
    Converts French legal documents (Codes, LODA, etc.) from the Legifrance API
    into the LegalJSON format.
    """
    
    def __init__(self, log_dir: str = './logs'):
        """
        Initialize the Legifrance parser.
        
        Parameters
        ----------
        log_dir : str
            Directory for log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(self.__class__.__name__)
        handler = logging.FileHandler(self.log_dir / 'legifrance_parser.log')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def parse_file(self, filepath: str) -> Dict[str, Any]:
        """
        Parse a Legifrance JSON file and convert to LegalJSON format.
        
        Parameters
        ----------
        filepath : str
            Path to the Legifrance JSON file
            
        Returns
        -------
        dict
            Document in LegalJSON format
        """
        self.logger.info(f"Parsing Legifrance JSON file: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Determine document type
            nature = data.get('nature', '')
            
            if nature == 'CODE':
                result = self._parse_code(data, filepath)
            elif nature in ['LOI', 'ORDONNANCE', 'DECRET']:
                result = self._parse_loda(data, filepath)
            else:
                result = self._parse_generic(data, filepath)
            
            self.logger.info(f"Successfully parsed {filepath}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing {filepath}: {e}")
            raise
    
    def _parse_code(self, data: Dict[str, Any], filepath: str) -> Dict[str, Any]:
        """
        Parse a Code document.
        
        Parameters
        ----------
        data : dict
            Raw Legifrance JSON data
        filepath : str
            Source file path
            
        Returns
        -------
        dict
            LegalJSON formatted document
        """
        # Build preface with metadata
        preface = {
            "title": data.get('title'),
            "source": "legifrance",
            "source_id": data.get('cid'),
            "source_url": f"https://www.legifrance.gouv.fr/codes/id/{data.get('cid')}",
            "jurisdiction": "FR",
            "type": "code",
            "nature": data.get('nature'),
            "eli": data.get('eli'),
            "nor": data.get('nor'),
            "state": data.get('jurisState'),
            "date_debut": data.get('dateDebutVersion'),
            "date_fin": data.get('dateFinVersion'),
            "date_modification": data.get('modifDate'),
            "file_path": filepath
        }
        
        # Extract citations
        citations = self._extract_citations(data)
        
        # Parse structure into chapters and articles
        chapters = []
        articles = []
        
        for section in data.get('sections', []):
            chapter_data = self._parse_section_to_chapter(section)
            if chapter_data:
                chapters.append(chapter_data)
            
            # Collect all articles from all sections (only VIGUEUR ones)
            section_articles = self._collect_all_articles_from_section(section)
            articles.extend(section_articles)
        
        # Build LegalJSON structure matching the schema
        legal_json = {
            "preface": json.dumps(preface, ensure_ascii=False),
            "preamble": None,
            "formula": None,
            "citations": citations,
            "recitals": [],
            "preamble_final": None,
            "chapters": chapters,
            "articles": articles,
            "conclusions": None
        }
        
        return legal_json
    
    def _parse_loda(self, data: Dict[str, Any], filepath: str) -> Dict[str, Any]:
        """
        Parse a LODA (law/decree) document.
        
        Parameters
        ----------
        data : dict
            Raw Legifrance JSON data
        filepath : str
            Source file path
            
        Returns
        -------
        dict
            LegalJSON formatted document
        """
        preface = {
            "title": data.get('title'),
            "source": "legifrance",
            "source_id": data.get('cid'),
            "source_url": f"https://www.legifrance.gouv.fr/loda/id/{data.get('cid')}",
            "jurisdiction": "FR",
            "type": "loda",
            "nature": data.get('nature'),
            "eli": data.get('eli'),
            "nor": data.get('nor'),
            "state": data.get('jurisState'),
            "date_texte": data.get('dateTexte'),
            "date_parution": data.get('dateParution'),
            "num_parution": data.get('numParution'),
            "file_path": filepath
        }
        
        citations = self._extract_citations(data)
        
        chapters = []
        articles = []
        
        for section in data.get('sections', []):
            chapter_data = self._parse_section_to_chapter(section)
            if chapter_data:
                chapters.append(chapter_data)
            
            # Collect all articles from all sections (only VIGUEUR ones)
            section_articles = self._collect_all_articles_from_section(section)
            articles.extend(section_articles)
        
        # Add top-level articles if present (only VIGUEUR ones)
        if data.get('articles'):
            top_articles = self._convert_articles_to_legaljson(data.get('articles', []))
            articles.extend(top_articles)
        
        legal_json = {
            "preface": json.dumps(preface, ensure_ascii=False),
            "preamble": None,
            "formula": None,
            "citations": citations,
            "recitals": [],
            "preamble_final": None,
            "chapters": chapters,
            "articles": articles,
            "conclusions": None
        }
        
        return legal_json
    
    def _parse_generic(self, data: Dict[str, Any], filepath: str) -> Dict[str, Any]:
        """
        Parse a generic document type.
        
        Parameters
        ----------
        data : dict
            Raw Legifrance JSON data
        filepath : str
            Source file path
            
        Returns
        -------
        dict
            LegalJSON formatted document
        """
        preface = {
            "title": data.get('title', 'Untitled'),
            "source": "legifrance",
            "source_id": data.get('cid'),
            "jurisdiction": "FR",
            "nature": data.get('nature'),
            "file_path": filepath
        }
        
        chapters = []
        for section in data.get('sections', []):
            chapter_data = self._parse_section_to_chapter(section)
            if chapter_data:
                chapters.append(chapter_data)
        
        legal_json = {
            "preface": json.dumps(preface, ensure_ascii=False),
            "preamble": None,
            "formula": None,
            "citations": [],
            "recitals": [],
            "preamble_final": None,
            "chapters": chapters,
            "articles": [],
            "conclusions": None
        }
        
        return legal_json
    
    def _parse_section_to_chapter(self, section: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a Legifrance section to a LegalJSON chapter.
        
        Parameters
        ----------
        section : dict
            Section data from Legifrance
            
        Returns
        -------
        dict
            Chapter in LegalJSON format (structure only, no articles)
        """
        chapter = {
            "eId": section.get('id'),
            "title": section.get('title')
        }
        
        return chapter
    
    def _collect_all_articles_from_section(self, section: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Recursively collect all articles from a section and its subsections.
        
        Parameters
        ----------
        section : dict
            Section data
            
        Returns
        -------
        list
            All articles in LegalJSON format
        """
        articles = []
        
        # Add articles at this level
        if section.get('articles'):
            articles.extend(self._convert_articles_to_legaljson(section.get('articles', [])))
        
        # Recursively add articles from subsections
        if section.get('sections'):
            for subsection in section.get('sections', []):
                articles.extend(self._collect_all_articles_from_section(subsection))
        
        return articles
    
    def _convert_articles_to_legaljson(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert Legifrance articles to LegalJSON format.
        Only includes articles with state VIGUEUR (in force), skips ABROGE (abrogated).
        
        Parameters
        ----------
        articles : list
            List of articles from Legifrance
            
        Returns
        -------
        list
            Articles in LegalJSON format (only VIGUEUR)
        """
        result = []
        
        for article in articles:
            # Skip abrogated articles
            if article.get('etat') == 'ABROGE':
                continue
            
            article_obj = {
                "eId": article.get('id'),
                "num": article.get('num'),
                "heading": None,
                "content": self._clean_html_content(article.get('texteHtml', '')),
                "metadata": {
                    "cid": article.get('cid'),
                    "state": article.get('etat'),
                    "date_debut": article.get('dateDebut'),
                    "date_fin": article.get('dateFin')
                }
            }
            
            if article.get('nota'):
                article_obj['nota'] = article.get('nota')
            
            result.append(article_obj)
        
        return result
    
    def _extract_citations(self, data: Dict[str, Any]) -> List[str]:
        """
        Extract citations from document.
        
        Parameters
        ----------
        data : dict
            Document data
            
        Returns
        -------
        list
            List of citation strings
        """
        citations = []
        
        # Extract from visa
        if data.get('visa'):
            citations.append(data.get('visa'))
        
        # Extract from liens
        if data.get('liens'):
            for lien in data.get('liens', []):
                citation_text = lien.get('titre', '')
                if citation_text:
                    citations.append(citation_text)
        
        return citations
    
    def _clean_html_content(self, html: str) -> str:
        """
        Clean HTML content for LegalJSON.
        
        Parameters
        ----------
        html : str
            Raw HTML content
            
        Returns
        -------
        str
            Cleaned content
        """
        if not html:
            return ""
        
        # For now, keep the HTML as is
        # Could add HTML stripping or conversion here if needed
        return html.strip()
    
    def save_legaljson(self, legal_json: Dict[str, Any], output_path: str) -> None:
        """
        Save LegalJSON to file.
        
        Parameters
        ----------
        legal_json : dict
            LegalJSON document
        output_path : str
            Path to save the output
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(legal_json, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved LegalJSON to: {output_path}")


def main():
    """
    Command-line interface for Legifrance parser.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Parse Legifrance JSON to LegalJSON')
    parser.add_argument('input', help='Input Legifrance JSON file')
    parser.add_argument('output', help='Output LegalJSON file')
    parser.add_argument('--logdir', default='./logs', help='Log directory')
    
    args = parser.parse_args()
    
    # Parse
    legifrance_parser = LegifranceParser(log_dir=args.logdir)
    legal_json = legifrance_parser.parse_file(args.input)
    
    # Save
    legifrance_parser.save_legaljson(legal_json, args.output)
    
    print(f"Successfully converted {args.input} to {args.output}")


if __name__ == "__main__":
    main()
