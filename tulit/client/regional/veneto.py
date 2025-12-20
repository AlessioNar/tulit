import logging
import requests
from tulit.client.client import Client
import argparse
import os
import sys

class VenetoClient(Client):
    def __init__(self, download_dir, log_dir, proxies=None):
        super().__init__(download_dir=download_dir, log_dir=log_dir, proxies=proxies)
        self.logger = logging.getLogger(self.__class__.__name__)

    def download(self, url, fmt=None):
        try:
            self.logger.info(f"Requesting Veneto HTML from URL: {url}")
            response = requests.get(url)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '')
            if fmt:
                if fmt == 'html' and 'html' not in content_type:
                    self.logger.error(f"Expected HTML response but got: {content_type}")
                    sys.exit(1)
                if fmt == 'xml' and 'xml' not in content_type:
                    self.logger.error(f"Expected XML response but got: {content_type}")
                    sys.exit(1)
                if fmt == 'pdf' and 'pdf' not in content_type:
                    self.logger.error(f"Expected PDF response but got: {content_type}")
                    sys.exit(1)
            self.logger.info(f"Successfully retrieved Veneto HTML from {url}")
            return response.text
        except requests.RequestException as e:
            self.logger.error(f"An error occurred: {e}")
            return None