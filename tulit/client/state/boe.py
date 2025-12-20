"""
Boletín Oficial del Estado (BOE) client.

This module contains the BOEClient class, which is used to download XML files from the BOE API endpoint.

The documentation for the BOE API can be found at https://www.boe.es/datosabiertos/documentos/APIsumarioBOE.pdf

"""

import logging
import os
import requests
from tulit.client.client import Client
import argparse
import sys

class BOEClient(Client):
    def __init__(self, download_dir, log_dir, proxies=None):
        super().__init__(download_dir=download_dir, log_dir=log_dir, proxies=proxies)
        self.logger = logging.getLogger(self.__class__.__name__)

    def download(self, id, fmt=None):
        try:
            url = 'https://www.boe.es/diario_boe/xml.php?id='
            self.logger.info(f"Requesting BOE document with id: {id}")
            response = requests.get(url + id)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '')
            if fmt:
                if fmt == 'xml' and 'xml' not in content_type:
                    self.logger.error(f"Expected XML response but got: {content_type}")
                    sys.exit(1)
                if fmt == 'html' and 'html' not in content_type:
                    self.logger.error(f"Expected HTML response but got: {content_type}")
                    sys.exit(1)
                if fmt == 'pdf' and 'pdf' not in content_type:
                    self.logger.error(f"Expected PDF response but got: {content_type}")
                    sys.exit(1)
            self.logger.info(f"Successfully retrieved BOE document: {id}")
            return response.text
        except requests.RequestException as e:
            self.logger.error(f"An error occurred: {e}")
            return None