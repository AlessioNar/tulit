import logging
import requests
from tulit.client.client import Client
from tulit.parser.exceptions import ContentTypeError
import os

class FinlexClient(Client):
    """
    Client for retrieving legal documents from the Finlex Open Data REST API.
    API docs: https://opendata.finlex.fi/finlex/avoindata/v1
    """
    BASE_URL = "https://opendata.finlex.fi/finlex/avoindata/v1"

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/xml",
            "Accept-Encoding": "gzip",
            # The API rejects requests without a User-Agent
            "User-Agent": "tulit (+https://github.com/AlessioNar/tulit)",
        })
        if proxies:
            self.session.proxies.update(proxies)
        self.logger = logging.getLogger(self.__class__.__name__)

    def download(self, year, number, lang="fi", doc_type="act", fmt="xml",
                 consolidated=False, language="fin"):
        """
        Download a statute from the Finlex Open Data API as Akoma Ntoso.

        Parameters
        ----------
        year, number : str or int
            The statute's year and number (e.g. 2018, 1050 for 1050/2018).
        lang : str
            Country segment of the Akoma Ntoso path (always 'fi').
        doc_type : str
            Akoma Ntoso document type ('act').
        fmt : str
            Expected format of the response ('xml').
        consolidated : bool
            Download the consolidated text in force (statute-consolidated)
            instead of the statute as adopted.
        language : str
            'fin' (Finnish) or 'swe' (Swedish).

        Example endpoint: /akn/fi/act/statute-consolidated/2018/1050/fin@
        """
        kind = 'statute-consolidated' if consolidated else 'statute'
        url = f"{self.BASE_URL}/akn/{lang}/{doc_type}/{kind}/{year}/{number}/{language}%40"
        try:
            self.logger.info(f"Requesting Finlex statute: year={year}, number={number}, lang={lang}, doc_type={doc_type}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '')
            if fmt == 'xml' and 'xml' not in content_type:
                raise ContentTypeError(f"Expected XML from Finlex but got: {content_type}", content_type)
            if fmt == 'pdf' and 'pdf' not in content_type:
                raise ContentTypeError(f"Expected PDF from Finlex but got: {content_type}", content_type)
            if fmt == 'html' and 'html' not in content_type:
                raise ContentTypeError(f"Expected HTML from Finlex but got: {content_type}", content_type)
            suffix = '_consolidated' if consolidated else ''
            filename = f"finlex_{year}_{number}{suffix}_{language}.{fmt}"
            file_path = os.path.join(self.download_dir, filename)
            with open(file_path, "wb") as f:
                f.write(response.content)
            self.logger.info(f"Downloaded Finlex statute to {file_path}")
            return file_path
        except ContentTypeError:
            raise
        except requests.HTTPError as e:
            self.logger.error(f"HTTP error: {e} - {getattr(e.response, 'text', '')}")
            return None
        except Exception as e:
            self.logger.error(f"Error downloading Finlex statute: {e}")
            return None

