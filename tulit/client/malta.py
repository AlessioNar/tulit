import logging
import requests
from tulit.client.client import Client
import argparse
import os
import sys

class MaltaLegislationClient(Client):
    """
    Client for retrieving legal documents from the Maltese ELI portal.
    See: https://legislation.mt/eli
    """
    BASE_URL = "https://legislation.mt/eli"

    def __init__(self, download_dir, log_dir, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        if proxies:
            self.session.proxies.update(proxies)
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_document(self, eli_path, lang=None, fmt=None):
        """
        Download a document from the Maltese ELI portal.
        eli_path: str, e.g. 'cap/9', 'sl/9.24', 'ln/2015/433', 'lcbl/49/2004/10'
        lang: 'mlt' or 'eng' (optional)
        fmt: 'pdf', 'xml', 'html' (optional, currently only 'pdf' is supported)
        """
        url = f"{self.BASE_URL}/{eli_path}"
        if lang:
            url += f"/{lang}"
        if fmt:
            url += f"/{fmt}"
        try:
            self.logger.info(f"Requesting Malta legislation: eli_path={eli_path}, lang={lang}, fmt={fmt}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '')
            if fmt == 'pdf' and 'pdf' not in content_type:
                self.logger.error(f"Expected PDF response but got: {content_type}")
                sys.exit(1)
            if fmt == 'xml' and 'xml' not in content_type:
                self.logger.error(f"Expected XML response but got: {content_type}")
                sys.exit(1)
            if fmt == 'html' and 'html' not in content_type:
                self.logger.error(f"Expected HTML response but got: {content_type}")
                sys.exit(1)
            ext = fmt if fmt else 'pdf' if 'pdf' in url else 'html'
            filename = f"malta_{eli_path.replace('/', '_')}{'_' + lang if lang else ''}.{ext}"
            if fmt == 'pdf':
                if 'pdf' in content_type:
                    file_path = os.path.join(self.download_dir, filename)
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    self.logger.info(f"PDF downloaded successfully: {file_path}")
                    return file_path
                else:
                    self.logger.error(f"Expected PDF but got {content_type}. Not saving file.")
                    sys.exit(1)
            # For non-PDF, save as usual
            file_path = os.path.join(self.download_dir, filename)
            with open(file_path, "wb") as f:
                f.write(response.content)
            self.logger.info(f"File downloaded successfully: {file_path}")
            return file_path
        except requests.HTTPError as e:
            self.logger.error(f"HTTP error: {e} - {getattr(e.response, 'text', '')}")
            return None
        except Exception as e:
            self.logger.error(f"Error downloading Malta legislation: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(description='Download a document from the Maltese ELI portal.')
    parser.add_argument('--eli_path', type=str, required=True, help="ELI path, e.g. 'cap/9', 'sl/9.24', 'ln/2015/433', 'lcbl/49/2004/10'")
    parser.add_argument('--lang', type=str, default=None, help="Language code, e.g. 'mlt' or 'eng'")
    parser.add_argument('--fmt', type=str, default=None, help="Format, e.g. 'pdf', 'xml', 'html'")
    parser.add_argument('--dir', type=str, default='./tests/data/malta', help='Directory to save the file')
    parser.add_argument('--logdir', type=str, default='./tests/logs', help='Directory for logs')
    args = parser.parse_args()

    os.makedirs(args.dir, exist_ok=True)
    os.makedirs(args.logdir, exist_ok=True)
    client = MaltaLegislationClient(download_dir=args.dir, log_dir=args.logdir)
    file_path = client.get_document(eli_path=args.eli_path, lang=args.lang, fmt=args.fmt)
    if file_path:
        logging.info(f"Downloaded to {file_path}")
    else:
        logging.error("Download failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
