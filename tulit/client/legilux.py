import logging
import requests
import sys
from tulit.client.client import Client

class LegiluxClient(Client):
    def __init__(self, download_dir, log_dir):
        super().__init__(download_dir, log_dir)
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.endpoint = "https://legilux.public.lu/eli/etat/leg/loi"

    def build_request_url(self, eli) -> str:
        self.logger.info(f"Building request URL for ELI: {eli}")
        url = eli
        return url
    
    def fetch_content(self, url):
        self.logger.info(f"Fetching content from URL: {url}")
        headers = {"Accept": "application/xml"}
        response = requests.get(url, headers=headers)
        return response

    def download(self, eli):
        file_paths = []
        url = self.build_request_url(eli)
        response = self.fetch_content(url)
        # Extract filename from ELI - handle both /loi/ and /constitution/ paths
        if '/loi/' in eli:
            filename = eli.split('loi/')[1].replace('/', '_')
        elif '/constitution/' in eli:
            filename = eli.split('constitution/')[1].replace('/', '_')
        else:
            # Fallback: use last parts of ELI
            filename = '_'.join(eli.split('/')[-4:])
        filename = filename + '.xml' if not filename.endswith('.xml') else filename
        if response.status_code == 200:
            file_paths.append(self.handle_response(response, filename=filename))
            self.logger.info(f"Document downloaded successfully and saved to {file_paths}")
            print(f"Document downloaded successfully and saved to {file_paths}")
            return file_paths
        else:
            self.logger.error(f"Failed to download document. Status code: {response.status_code}")
            print(f"Failed to download document. Status code: {response.status_code}")
            sys.exit(1)
            return None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Download a document from Legilux')
    parser.add_argument('--eli', type=str, required=True, help='ELI URL of the document')
    parser.add_argument('--dir', type=str, default='./tests/data/legilux', help='Download directory')
    parser.add_argument('--logdir', type=str, default='./tests/metadata/logs', help='Log directory')
    
    args = parser.parse_args()
    
    downloader = LegiluxClient(download_dir=args.dir, log_dir=args.logdir)
    documents = downloader.download(eli=args.eli)
    if documents:
        logging.info(f"Downloaded documents: {documents}")
    else:
        logging.error("No documents downloaded.")
        sys.exit(1)