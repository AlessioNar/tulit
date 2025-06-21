import logging
import requests
import argparse
import os
import sys

class GermanyELIClient:
    """
    Client for retrieving legal documents from the German ELI endpoint.
    Example ELI: https://testphase.rechtsinformationen.bund.de/norms/eli/bund/banz-at/2025/130/2025-05-05/1/deu/regelungstext-1/hauptteil-1_art-1
    """
    def __init__(self, download_dir, log_dir):
        self.download_dir = download_dir
        self.log_dir = log_dir
        self.logger = logging.getLogger(self.__class__.__name__)
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(name)s %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(self.log_dir, 'germany_eli_client.log'), encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

    def get_html(self, eli_url, fmt='html'):
        try:
            self.logger.info(f"Requesting German ELI HTML from URL: {eli_url}")
            response = requests.get(eli_url)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '')
            if fmt == 'html' and 'html' not in content_type:
                self.logger.error(f"Expected HTML response but got: {content_type}")
                sys.exit(1)
            self.logger.info(f"Successfully retrieved German ELI HTML from {eli_url}")
            return response.text
        except requests.RequestException as e:
            self.logger.error(f"An error occurred: {e}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Download an HTML file from the German ELI endpoint.')
    parser.add_argument('--eli_url', type=str, required=True, help='ELI URL of the German legal document.')
    parser.add_argument('--file', type=str, default='germany_eli.html', help='Path to the output HTML file.')
    parser.add_argument('--dir', type=str, default='./tests/data/html/germany', help='Directory to save the HTML file.')
    parser.add_argument('--logdir', type=str, default='./tests/logs', help='Directory for logs.')
    args = parser.parse_args()

    client = GermanyELIClient(download_dir=args.dir, log_dir=args.logdir)
    html_content = client.get_html(args.eli_url, fmt='html')

    if html_content:
        output_dir = os.path.abspath(args.dir)
        os.makedirs(output_dir, exist_ok=True)
        try:
            file_path = os.path.join(output_dir, os.path.basename(args.file))
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logging.info(f"File saved successfully to {file_path}")
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
