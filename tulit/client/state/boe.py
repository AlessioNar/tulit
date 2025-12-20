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
    def __init__(self, download_dir, log_dir):
        super().__init__(download_dir=download_dir, log_dir=log_dir)
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_html(self, id, fmt=None):
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


def main():
    parser = argparse.ArgumentParser(description='Downloads an XML file from the BVeneto website.')
    parser.add_argument('--id', type=str, default='BOE-A-2001-11814', help='BOE Id of the document to download.')
    parser.add_argument('--file', type=str, default='boe.xml', help='Path to the output HTML file.')
    args = parser.parse_args()
    
    client = BOEClient(download_dir=args.file, log_dir='../tests/metadata/logs')
    html_content = client.get_html(args.id, fmt=os.path.splitext(args.file)[1][1:])

    if html_content:
        # Ensure the directory exists
        output_dir = os.path.abspath('./tests/data/xml/spain/')
        os.makedirs(output_dir, exist_ok=True)

        # Write the HTML content to a file
        try:
            with open(os.path.join(output_dir, os.path.basename(args.file)), 'w', encoding='utf-8') as f:
                f.write(html_content)
            logging.info(f"File saved successfully to {os.path.join(output_dir, os.path.basename(args.file))}")
        except PermissionError as e:
            logging.error(f"Permission error: {e}")
            sys.exit(1)
        except Exception as e:
            logging.error(f"An error occurred while writing the file: {e}")
            sys.exit(1)
    else:
        logging.error("Failed to retrieve HTML content.")
        sys.exit(1)

if __name__ == "__main__":
    main()