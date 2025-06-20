import logging
import requests
from tulit.client.client import Client
import argparse
import os

class VenetoClient(Client):
    def __init__(self, download_dir, log_dir):
        super().__init__(download_dir=download_dir, log_dir=log_dir)
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_html(self, url):
        try:
            self.logger.info(f"Requesting Veneto HTML from URL: {url}")
            response = requests.get(url)
            response.raise_for_status()
            self.logger.info(f"Successfully retrieved Veneto HTML from {url}")
            return response.text
        except requests.RequestException as e:
            self.logger.error(f"An error occurred: {e}")
            return None
    
def main():
    parser = argparse.ArgumentParser(description='Downloads an HTML file from the Veneto website.')
    parser.add_argument('--url', type=str, default='https://www.consiglioveneto.it/web/crv/dettaglio-legge?numeroDocumento=10&id=69599315&backLink=https%3A%2F%2Fwww.consiglioveneto.it%2Fleggi-regionali%3Fp_p_id&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&pageTitle=&tab=vigente&annoSelezionato=2024', help='URL of the HTML file to download.')
    parser.add_argument('--file', type=str, default='esg.html', help='Path to the output HTML file.')
    args = parser.parse_args()
    
    client = VenetoClient(download_dir=args.file, log_dir='../tests/metadata/logs')
    html_content = client.get_html(args.url)

    if html_content:
        # Ensure the directory exists
        output_dir = os.path.abspath('./tests/data/html/veneto')
        os.makedirs(output_dir, exist_ok=True)

        # Write the HTML content to a file
        try:
            with open(os.path.join(output_dir, os.path.basename(args.file)), 'w', encoding='utf-8') as f:
                f.write(html_content)
            logging.info(f"File saved successfully to {os.path.join(output_dir, os.path.basename(args.file))}")
        except PermissionError as e:
            logging.error(f"Permission error: {e}")
        except Exception as e:
            logging.error(f"An error occurred while writing the file: {e}")
    else:
        logging.error("Failed to retrieve HTML content.")

if __name__ == "__main__":
    main()