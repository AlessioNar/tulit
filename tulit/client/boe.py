"""
Boletín Oficial del Estado (BOE) client.

This module contains the BOEClient class, which is used to download XML files from the BOE API endpoint.

The documentation for the BOE API can be found at https://www.boe.es/datosabiertos/documentos/APIsumarioBOE.pdf

"""

import requests
from tulit.client.client import Client
import argparse
import os

class BOEClient(Client):
    def __init__(self, download_dir, log_dir):
        super().__init__(download_dir=download_dir, log_dir=log_dir)

    def get_html(self, id):
        try:
            url = 'https://www.boe.es/diario_boe/xml.php?id='
            response = requests.get(url + id)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"An error occurred: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(description='Downloads an XML file from the BVeneto website.')
    parser.add_argument('--id', type=str, default='BOE-A-2001-11814', help='BOE Id of the document to download.')
    parser.add_argument('--file', type=str, default='boe.xml', help='Path to the output HTML file.')
    args = parser.parse_args()
    
    client = BOEClient(download_dir=args.file, log_dir='../tests/metadata/logs')
    html_content = client.get_html(args.id)

    if html_content:
        # Ensure the directory exists
        output_dir = os.path.abspath('./tests/data/xml/spain/')
        os.makedirs(output_dir, exist_ok=True)

        # Write the HTML content to a file
        try:
            with open(os.path.join(output_dir, os.path.basename(args.file)), 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"File saved successfully to {os.path.join(output_dir, os.path.basename(args.file))}")
        except PermissionError as e:
            print(f"Permission error: {e}")
        except Exception as e:
            print(f"An error occurred while writing the file: {e}")
    else:
        print("Failed to retrieve HTML content.")

if __name__ == "__main__":
    main()