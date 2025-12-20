import logging
import requests
from tulit.client.client import Client
import argparse
import os
import sys

class FinlexClient(Client):
    """
    Client for retrieving legal documents from the Finlex Open Data REST API.
    API docs: https://opendata.finlex.fi/finlex/avoindata/v1
    """
    BASE_URL = "https://opendata.finlex.fi/finlex/avoindata/v1"

    def __init__(self, download_dir, log_dir, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/xml",
            "Accept-Encoding": "gzip"
        })
        if proxies:
            self.session.proxies.update(proxies)
        self.logger = logging.getLogger(self.__class__.__name__)

    def download(self, year, number, lang="fi", doc_type="act", fmt="xml"):
        """
        Download a statute XML from Finlex Open Data API.
        Example endpoint:
        /akn/fi/act/statute/2024/123/fin@
        """
        url = f"{self.BASE_URL}/akn/{lang}/{doc_type}/statute/{year}/{number}/fin%40"
        try:
            self.logger.info(f"Requesting Finlex statute: year={year}, number={number}, lang={lang}, doc_type={doc_type}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '')
            if fmt == 'xml' and 'xml' not in content_type:
                self.logger.error(f"Expected XML response but got: {content_type}")
                sys.exit(1)
            if fmt == 'pdf' and 'pdf' not in content_type:
                self.logger.error(f"Expected PDF response but got: {content_type}")
                sys.exit(1)
            if fmt == 'html' and 'html' not in content_type:
                self.logger.error(f"Expected HTML response but got: {content_type}")
                sys.exit(1)
            filename = f"finlex_{year}_{number}.{fmt}"
            file_path = os.path.join(self.download_dir, filename)
            with open(file_path, "wb") as f:
                f.write(response.content)
            self.logger.info(f"Downloaded Finlex statute to {file_path}")
            return file_path
        except requests.HTTPError as e:
            self.logger.error(f"HTTP error: {e} - {getattr(e.response, 'text', '')}")
            return None
        except Exception as e:
            self.logger.error(f"Error downloading Finlex statute: {e}")
            return None

