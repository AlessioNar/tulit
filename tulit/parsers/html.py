from bs4 import BeautifulSoup
from .parser import Parser

class HTMLParser(Parser):
    def __init__(self):
        """
        Initializes the HTML parser and sets up the BeautifulSoup instance.
        """
        super().__init__()
        self.root = None
        self.valid = True
        
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

    def get_meta(self):
        """
        Extracts metadata from the HTML.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None
            The extracted metadata is stored in the 'meta' attribute.
        """
        try:
            meta_elements = self.root.find_all('meta')
            for meta in meta_elements:
                name = meta.get('name')
                content = meta.get('content')
                if name and content:
                    self.meta[name] = content
            print(f"Metadata extracted: {len(self.meta)} entries.")
        except Exception as e:
            print(f"Error extracting metadata: {e}")
   
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
        if self.preamble:
            self.get_citations()
            self.get_recitals()
            print("Preamble extracted successfully.")
        else:
            self.preamble = None
            print("No preamble found.")
        

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
            citation_id = citation.get('id')
            citation_text = citation.get_text(strip=True)
            self.citations.append({
                    'eId' : citation_id,
                    'citation_text' : citation_text
                }
            )
        print(f"Citations extracted: {len(self.citations)}")

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
            recital_id = recital.get('id')
            recital_text = recital.get_text(strip=True)
            self.recitals.append({
                    'eId' : recital_id,
                    'recital_text' : recital_text
                }
            )
        print(f"Recitals extracted: {len(self.recitals)}")

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
        try:
            body_element = self.root.find('div', id=lambda x: x and x.startswith('enc_'))
            if body_element:
                self.body = body_element
                print("Body extracted successfully.")
            else:
                self.body = None
                print("No body found.")
        except Exception as e:
            print(f"Error extracting body: {e}")

    def get_chapters(self):
        """
        Extracts chapters from the HTML, grouping them by their IDs and headings.
        """
        try:
            chapters = self.body.find_all('div', id=lambda x: x and x.startswith('cpt_') and '.' not in x)
            self.chapters = []
            for chapter in chapters:
                chapter_id = chapter.get('id')
                chapter_num = chapter.find('p', class_="oj-ti-section-1").get_text(strip=True)
                chapter_title = chapter.find('div', class_="eli-title").get_text(strip=True)
                self.chapters.append({
                    'eId': chapter_id,
                    'chapter_num': chapter_num,
                    'chapter_heading': chapter_title
                })
            print(f"Chapters extracted: {len(self.chapters)}")
        except Exception as e:
            print(f"Error extracting chapters: {e}")

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
        try:
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
                    'article_text': subdivisions
                })

            print(f"Articles extracted: {len(self.articles)}")
        except Exception as e:
            print(f"Error extracting articles: {e}")


    def get_conclusions(self):
        """
        Extracts conclusions from the HTML, if present.
        """
        try:
            conclusions_element = self.root.find('div', class_='oj-final')
            if conclusions_element:
                self.conclusions = conclusions_element.get_text(strip=True)
                print("Conclusions extracted successfully.")
            else:
                self.conclusions = None
                print("No conclusions found.")
        except Exception as e:
            print(f"Error extracting conclusions: {e}")

    def parse(self, file: str):
        """
        Parses an HTML file and extracts all relevant sections.
        """
        self.get_root(file)
        #self.get_meta()
        self.get_preface()
        self.get_preamble()
        self.get_body()
        self.get_chapters()
        self.get_articles()
        self.get_conclusions()