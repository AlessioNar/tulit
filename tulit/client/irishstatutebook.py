import logging
import requests
from tulit.client.client import Client
import argparse
import os

class IrishStatuteBookClient(Client):
    """
    Client for retrieving legal documents from the Irish Statute Book (ISB).
    Example: https://www.irishstatutebook.ie/eli/2012/act/10/enacted/en/xml
    """
    BASE_URL = "https://www.irishstatutebook.ie/eli"

    def __init__(self, download_dir, log_dir, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        if proxies:
            self.session.proxies.update(proxies)
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_act(self, year, act_number, lang="en", status="enacted"):
        """
        Download an Act XML from the Irish Statute Book.
        """
        url = f"{self.BASE_URL}/{year}/act/{act_number}/{status}/{lang}/xml"
        try:
            self.logger.info(f"Requesting ISB act: year={year}, act_number={act_number}, lang={lang}, status={status}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            filename = f"isb_{year}_act_{act_number}.xml"
            file_path = os.path.join(self.download_dir, filename)
            with open(file_path, "wb") as f:
                f.write(response.content)
            self.logger.info(f"Downloaded ISB act to {file_path}")
            return file_path
        except requests.HTTPError as e:
            self.logger.error(f"HTTP error: {e} - {getattr(e.response, 'text', '')}")
            return None
        except Exception as e:
            self.logger.error(f"Error downloading ISB act: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(description='Download an Act XML from the Irish Statute Book.')
    parser.add_argument('--year', type=int, required=True, help='Year of the Act (e.g. 2012)')
    parser.add_argument('--act_number', type=int, required=True, help='Number of the Act (e.g. 10)')
    parser.add_argument('--dir', type=str, default='./tests/data/isb', help='Directory to save the XML file')
    parser.add_argument('--logdir', type=str, default='./tests/logs', help='Directory for logs')
    args = parser.parse_args()

    os.makedirs(args.dir, exist_ok=True)
    os.makedirs(args.logdir, exist_ok=True)
    client = IrishStatuteBookClient(download_dir=args.dir, log_dir=args.logdir)
    file_path = client.get_act(year=args.year, act_number=args.act_number)
    if file_path:
        logging.info(f"Downloaded to {file_path}")
        print(f"Downloaded to {file_path}")
    else:
        logging.error("Download failed.")
        print("Download failed.")

if __name__ == "__main__":
    main()
