from tulit.parsers.html.xhtml import HTMLParser
import json

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
            text = recital.get_text(strip=True)
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
                'chapter_num': chapter_num,
                'chapter_heading': chapter_title
            })
            

    def get_lists(self, parent_id: str, container):
        """
        Parses HTML tables representing lists and generates Akoma Ntoso-style eIds.

        Args:
            parent_id (str): The eId of the parent element (e.g., article or subdivision).
            container (BeautifulSoup Tag): The container holding the <table> elements.

        Returns:
            list[dict]: List of list elements with eIds and corresponding text content.
        """
        lists = []
        list_counter = 0

        # Find all <table> elements within the container
        tables = container.find_all('table')

        for table in tables:
            list_counter += 1
            list_eId = f"{parent_id}__list_{list_counter}"

            # Process each row (<tr>) within the table
            points = []
            point_counter = 0

            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) >= 2:
                    # Extract point number (e.g., (a)) and content
                    point_counter += 1
                    point_eId = f"{list_eId}__point_{point_counter}"
                    point_num = cols[0].get_text(strip=True)  # First column: point number
                    point_text = cols[1].get_text(" ", strip=True)  # Second column: point text

                    # Clean text
                    point_text = self._clean_text(point_text)

                    points.append({
                        'eId': point_eId,
                        'num': point_num,
                        'text': point_text
                    })

            # Add the list with its points
            lists.append({
                'eId': list_eId,
                'points': points
            })

        return lists


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
            # Group <p> tags by their closest parent with an id
            content_map = {}
            for p in article.find_all('p', class_='oj-normal'):  # Filter <p> with class 'oj-normal'
                current_element = p
                parent_eId = None
                # Traverse upward to find the closest parent with an id
                while current_element:
                    parent_eId = current_element.get('id')
                    if parent_eId:
                        break
                    current_element = current_element.parent
                if parent_eId:
                    # Add text from the <p> to the appropriate parent_eId group
                    if parent_eId not in content_map:
                        content_map[parent_eId] = []
                    content_map[parent_eId].append(p.get_text(strip=True))
            # Combine grouped content into structured output
            subdivisions = []
            for sub_eId, texts in content_map.items():
                subdivisions.append({
                    'eId': sub_eId,
                    'text': ' '.join(texts)  # Combine all <p> texts for the subdivision
                })
            # Store the article with its eId and subdivisions
            self.articles.append({
                'eId': eId,
                'article_num': article_num,
                'article_title': article_title,
                'children': subdivisions
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
    parser = CellarHTMLParser()
    file_to_parse = 'tests/data/html/c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.03/DOC_1.html'
    
    output_file = 'tests/data/json/iopa_html.json'
    

    parser.parse(file_to_parse)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Get the parser's attributes as a dictionary
        parser_dict = parser.__dict__
    
        # Filter out non-serializable attributes
        serializable_dict = {k: v for k, v in parser_dict.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))}
    
        # Write to a JSON file
        json.dump(serializable_dict, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()