from tulit.parsers.html.xhtml import HTMLParser
import json
import re
import argparse

class CellarHTMLParser(HTMLParser):
    def __init__(self):
        pass

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
            preface_element = self.root.find('div', class_='eli-main-title')
            if preface_element:
                self.preface = preface_element.get_text(strip=True)
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
        
        self.preamble = self.root.find('div', class_='eli-subdivision', id='pbl_1')
        # Remove all a tags from the preamble
        for a in self.preamble.find_all('a'):
            a.decompose()
            
    
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
        self.formula = self.preamble.find('p', class_='oj-normal').text


    
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
        citations = self.preamble.find_all('div', class_='eli-subdivision', id=lambda x: x and x.startswith('cit_'))
        self.citations = []
        for citation in citations:
            eId = citation.get('id')
            text = citation.get_text(strip=True)
            self.citations.append({
                    'eId' : eId,
                    'text' : text
                }
            )

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
        recitals = self.preamble.find_all('div', class_='eli-subdivision', id=lambda x: x and x.startswith('rct_'))
        self.recitals = []
        for recital in recitals:
            eId = recital.get('id')
            
            text = recital.get_text()            
            text = re.sub(r'\s+', ' ', text).strip()
            text = re.sub(r'^\(\d+\)', '', text).strip()
            
            self.recitals.append({
                    'eId' : eId,
                    'text' : text
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
        self.preamble_final = self.preamble.find_all('p', class_='oj-normal')[-1].get_text(strip=True)

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
        
        self.body = self.root.find('div', id=lambda x: x and x.startswith('enc_'))
        for a in self.body.find_all('a'):
            a.replace_with(' ')

    def get_chapters(self):
        """
        Extracts chapters from the HTML, grouping them by their IDs and headings.
        """
        
        chapters = self.body.find_all('div', id=lambda x: x and x.startswith('cpt_') and '.' not in x)
        self.chapters = []
        for chapter in chapters:
            eId = chapter.get('id')
            chapter_num = chapter.find('p', class_="oj-ti-section-1").get_text(strip=True)
            chapter_title = chapter.find('div', class_="eli-title").get_text(strip=True)
            self.chapters.append({
                'eId': eId,
                'num': chapter_num,
                'heading': chapter_title
            })

    def get_articles(self):
        """
        Extracts articles from the HTML. Each <div> with an id starting with "art" is treated as an article (eId).
        Subsequent subdivisions are processed based on the closest parent with an id.

        Returns:
            list[dict]: List of articles, each containing its eId and associated content.
        """
        
        articles = self.body.find_all('div', id=lambda x: x and x.startswith('art_') and '.' not in x)
        self.articles = []
        for article in articles:
            eId = article.get('id')  # Treat the id as the eId
            article_num = article.find('p', class_='oj-ti-art').get_text(strip=True)
            article_title_element = article.find('p', class_='oj-sti-art')
            if article_title_element is not None:
                article_title = article_title_element.get_text(strip=True)
            else:
                article_title = None
            
            # Extract paragraphs and lists within the article
            children = []
            
            # Handle articles with only paragraphs
            paragraphs = article.find_all('p', class_='oj-normal')            
            if paragraphs and len(article.find_all('table')) == 0:
                for paragraph in paragraphs:
                    text = ' '.join(paragraph.get_text(separator= ' ', strip=True).split())
                    
                    children.append({
                        # Get parent of the paragraph: Use the id of the parent div as the eId
                        'eId': paragraph.find_parent('div').get('id'),
                        'text': text
                    })
            # Handle articles with only tables as first child:
            elif article.find_all('table') and article.find_all('table')[0].find_parent('div') == article:
                intro = article.find('p', class_='oj-normal')
                children.append({
                    'eId': 0,
                    'text': intro.get_text(strip=True)
                })
                tables = article.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) == 2:
                            number = cols[0].get_text(strip=True)
                            text = ' '.join(cols[1].get_text(separator = ' ', strip=True).split())
                            
                            children.append({
                                'eId': number,
                                'text': text
                            })
            # Handle articles with paragraphs and tables by treating tables as part of the same paragraph
            elif article.find_all('div', id=lambda x: x and '.' in x):
                paragraphs = article.find_all('div', id=lambda x: x and '.' in x)
                for paragraph in paragraphs:
                    if not paragraph.get('class'):
                        children.append({
                                'eId': paragraph.get('id'),
                                'text': ' '.join(paragraph.get_text(separator = ' ', strip=True).split())
                        })
            
            # Store the article with its eId and subdivisions
            self.articles.append({
                'eId': eId,
                'num': article_num,
                'heading': article_title,
                'children': children
            })


    def get_conclusions(self):
        """
        Extracts conclusions from the HTML, if present.
        """
        conclusions_element = self.root.find('div', class_='oj-final')
        self.conclusions = conclusions_element.get_text(strip=True)

    def parse(self, file):
        return super().parse(file)
        

def main():
    parser = argparse.ArgumentParser(description='Parse an Cellar XHTML document and output the results to a JSON file.')
    parser.add_argument('--input', type=str, default='tests/data/html/c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.03/DOC_1.html', help='Path to the Cellar XHTML file to parse.')
    parser.add_argument('--output', type=str, default='tests/data/json/iopa_html.json', help='Path to the output JSON file.')
    args = parser.parse_args()
    
    html_parser = CellarHTMLParser()
    html_parser.parse(args.input)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        # Get the parser's attributes as a dictionary
        parser_dict = html_parser.__dict__
    
        # Filter out non-serializable attributes
        serializable_dict = {k: v for k, v in parser_dict.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))}
    
        # Write to a JSON file
        json.dump(serializable_dict, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()