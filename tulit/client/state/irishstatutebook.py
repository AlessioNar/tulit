import logging
import requests
from tulit.client.client import Client
from tulit.parser.exceptions import ContentTypeError
import os

class IrishStatuteBookClient(Client):
    """
    Client for retrieving legal documents from the Irish Statute Book (ISB).
    Example: https://www.irishstatutebook.ie/eli/2012/act/10/enacted/en/xml
    """
    BASE_URL = "https://www.irishstatutebook.ie/eli"

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        if proxies:
            self.session.proxies.update(proxies)
        self.logger = logging.getLogger(self.__class__.__name__)

    def download(self, year, act_number, lang="en", status="enacted", fmt="xml"):
        """
        Download an Act XML from the Irish Statute Book.
        """
        url = f"{self.BASE_URL}/{year}/act/{act_number}/{status}/{lang}/xml"
        try:
            self.logger.info(f"Requesting ISB act: year={year}, act_number={act_number}, lang={lang}, status={status}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '')
            if fmt == 'xml' and 'xml' not in content_type:
                raise ContentTypeError(f"Expected XML response but got: {content_type}", content_type)
            if fmt == 'pdf' and 'pdf' not in content_type:
                raise ContentTypeError(f"Expected PDF response but got: {content_type}", content_type)
            if fmt == 'html' and 'html' not in content_type:
                raise ContentTypeError(f"Expected HTML response but got: {content_type}", content_type)
            filename = f"isb_{year}_act_{act_number}.{fmt}"
            file_path = os.path.join(self.download_dir, filename)
            with open(file_path, "wb") as f:
                f.write(response.content)
            self.logger.info(f"Downloaded ISB act to {file_path}")
            return file_path
        except ContentTypeError:
            raise
        except requests.HTTPError as e:
            self.logger.error(f"HTTP error: {e} - {getattr(e.response, 'text', '')}")
            return None
        except Exception as e:
            self.logger.error(f"Error downloading ISB act: {e}")
            return None
