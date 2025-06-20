import logging
import requests
from tulit.client.client import Client
import argparse
import os

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

    def get_statute(self, year, number, lang="fi", doc_type="act"):
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
            filename = f"finlex_{year}_{number}.xml"
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


def main():
    parser = argparse.ArgumentParser(description='Download a statute XML from Finlex Open Data API.')
    parser.add_argument('--year', type=int, required=True, help='Year of the statute (e.g. 2024)')
    parser.add_argument('--number', type=int, required=True, help='Number of the statute (e.g. 123)')
    parser.add_argument('--dir', type=str, default='./tests/data/finlex', help='Directory to save the XML file')
    parser.add_argument('--logdir', type=str, default='./tests/logs', help='Directory for logs')
    args = parser.parse_args()

    os.makedirs(args.dir, exist_ok=True)
    os.makedirs(args.logdir, exist_ok=True)
    client = FinlexClient(download_dir=args.dir, log_dir=args.logdir)
    file_path = client.get_statute(year=args.year, number=args.number)
    if file_path:
        logging.info(f"Downloaded to {file_path}")
    else:
        logging.error("Download failed.")

if __name__ == "__main__":
    main()
