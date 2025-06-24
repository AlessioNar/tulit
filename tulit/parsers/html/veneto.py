from tulit.parsers.html.xhtml import HTMLParser
import json
import re
import argparse
# LegalJSON validation
from tulit.parsers.parser import LegalJSONValidator
import logging

class VenetoHTMLParser(HTMLParser):
    def __init__(self):
        pass
    
    def get_root(self, file):
        super().get_root(file)
        
        self.root = self.root.find_all('div', class_="row testo")[0]

    def get_preface(self):
        """
        Extracts the preface text from the HTML, if available.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None
            The extracted preface is stored in the 'preface' attribute.
        """
        try:
            preface_element = self.root.find('title')
            if preface_element:
                self.preface = preface_element.get_text(separator=' ', strip=True)
                print("Preface extracted successfully.")
            else:
                self.preface = None
                print("No preface found.")
        except Exception as e:
            print(f"Error extracting preface: {e}")
    
            
    def get_preamble(self):
        """
        Extracts the preamble text from the HTML, if available.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None
            The extracted preamble is stored in the 'preamble' attribute.
        """
        
        pass
        # self.preamble = self.root.find('div')        
        
            
    
    def get_formula(self):
        """
        Extracts the formula from the HTML, if present.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None
            The extracted formula is stored in the 'formula' attribute.
        """
        pass
        # self.formula = self.preamble.find('p', class_='oj-normal').text


    
    def get_citations(self):
        """
        Extracts citations from the HTML.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None
            The extracted citations are stored in the 'citations' attribute
        """
        self.citations = []
        pass

    def get_recitals(self):
        """
        Extracts recitals from the HTML.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None
            The extracted recitals are stored in the 'recitals' attribute.
        """
        self.recitals = []
        subtitle = self.root.find('b')        
        self.recitals.append({
                    'eId' : 0,
                    'text' : subtitle.text
                }
        )
    def get_preamble_final(self):
        """
        Extracts the final preamble text from the HTML, if available.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None
            The extracted final preamble is stored in the 'preamble_final' attribute.
        """
        pass

    def get_body(self):
        """
        Extracts the body content from the HTML.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None
            The extracted body content is stored in the 'body' attribute
        """
        pass
    
    def get_chapters(self):
        """
        Extracts chapters from the HTML, grouping them by their IDs and headings.
        """
        
        chapters = self.root.find_all('h3', class_='TITOLOCAPOTITOLO')
        chapters = self.root.find_all('h4', class_='TITOLOCAPOCAPO')

        self.chapters = []
        for index, chapter in enumerate(chapters):
            eId = index
            text = chapter.get_text(strip=True)
            num = text.split('-')[0].strip()
            heading = text.split('-')[1].strip()
            self.chapters.append({
                'eId': eId,
                'num': num,
                'heading': heading
            })



    def get_articles(self):
        """
        Extracts articles from the HTML. Each <h6> is treated as an article heading, and the next <div> contains the article content.
        Subdivisions are separated by <br> tags and stored as children.
        """
        self.articles = []
        articles = self.root.find_all('h6')
        for index, article in enumerate(articles):
            # Extract article number and heading
            text = article.get_text(strip=True)
            text = text.replace('–', '-')
            if '-' in text:
                num, heading = [t.strip() for t in text.split('-', 1)]
            else:
                num, heading = str(index+1), text
            # Get the next sibling div containing the article content
            content_div = article.find_next_sibling('div')
            children = []
            if content_div:
                # Split content by <br> tags
                parts = []
                current = ''
                for elem in content_div.children:
                    if getattr(elem, 'name', None) == 'br':
                        if current.strip():
                            parts.append(current.strip())
                        current = ''
                    else:
                        current += str(elem)
                if current.strip():
                    parts.append(current.strip())
                # Clean up HTML tags and whitespace
                for child_index, part in enumerate(parts):
                    clean_text = re.sub('<[^<]+?>', '', part)
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                    if clean_text:
                        children.append({
                            'eId': child_index,
                            'text': clean_text
                        })
            self.articles.append({
                'eId': index,
                'num': num,
                'heading': heading,
                'children': children
            })


    def get_conclusions(self):
        """
        Extracts conclusions from the HTML, if present.
        """
        conclusions_element = self.root.find('div', class_='oj-final')
        self.conclusions = conclusions_element.get_text(separator=' ', strip=True)

    def parse(self, file):
        return super().parse(file)
        

def main():
    parser = argparse.ArgumentParser(description='Parse an Cellar XHTML document and output the results to a JSON file.')
    parser.add_argument('--input', type=str, default='tests/data/html/veneto/legge.html', help='Path to the Cellar XHTML file to parse.')
    parser.add_argument('--output', type=str, default='tests/data/json/veneto_html.json', help='Path to the output JSON file.')
    args = parser.parse_args()
    
    html_parser = VenetoHTMLParser()
    html_parser.parse(args.input)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        # Get the parser's attributes as a dictionary
        parser_dict = html_parser.__dict__
    
        # Filter out non-serializable attributes
        serializable_dict = {k: v for k, v in parser_dict.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))}
    
        # Write to a JSON file
        json.dump(serializable_dict, f, ensure_ascii=False, indent=4)
    
    logging.basicConfig(level=logging.INFO)
    validator = LegalJSONValidator()
    with open(args.output, 'r', encoding='utf-8') as f:
        data = json.load(f)
    valid = validator.validate(data)
    if valid:
        print('LegalJSON validation: SUCCESS')
    else:
        print('LegalJSON validation: FAILED')
        exit(1)

if __name__ == "__main__":
    main()