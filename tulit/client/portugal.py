import requests
from tulit.client.client import Client
import argparse
import os
import logging
import sys

class PortugalDREClient(Client):
    """
    Client for retrieving legal documents from the Portuguese DRE ELI portal.
    See: http://data.dre.pt/eli/
    """
    BASE_URL = "http://data.dre.pt/eli"

    def __init__(self, download_dir, log_dir, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        if proxies:
            self.session.proxies.update(proxies)
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_journal(self, series, number, year, supplement=0, lang='pt', fmt='html'):
        """
        Download an official journal Diário da República (Pillar I).
        series: '1', '1a', '1b', etc.
        number: number in the year
        year: year of publication
        supplement: supplement number (default 0)
        lang: language (default 'pt')
        fmt: 'html' or 'pdf' (default 'html')
        """
        url = f"{self.BASE_URL}/diario/{series}/{number}/{year}/{supplement}/{lang}/{fmt}"
        self.logger.info(f"Requesting journal: series={series}, number={number}, year={year}, supplement={supplement}, lang={lang}, fmt={fmt}")
        return self._download(url, f"dre_journal_{series}_{number}_{year}_{supplement}_{lang}.{fmt}", fmt)

    def get_legal_act(self, act_type, number, year, month, day, region, lang='pt', fmt='html'):
        """
        Download a legal act (Pillar II).
        act_type: e.g. 'lei', 'dec-lei', 'declegreg', etc.
        number: act number (may include suffix, e.g. '111-a')
        year, month, day: date of publication
        region: 'p', 'm', 'a'
        lang: language (default 'pt')
        fmt: 'html' or 'pdf' (default 'html')
        """
        self.logger.info(f"Requesting legal act: type={act_type}, number={number}, year={year}, month={month}, day={day}, region={region}, lang={lang}, fmt={fmt}")
        url = f"{self.BASE_URL}/{act_type}/{number}/{year}/{month}/{day}/{region}/dre/{lang}/{fmt}"
        return self._download(url, f"dre_act_{act_type}_{number}_{year}_{month}_{day}_{region}_{lang}.{fmt}", fmt)

    def get_consolidated(self, act_type, number, year, region, cons_date, lang='pt', fmt='html'):
        """
        Download a consolidated legal act (Pillar III).
        act_type: e.g. 'lei', 'dec-lei', 'declegreg', etc.
        number: act number
        year: year of publication
        region: 'p', 'm', 'a'
        cons_date: consolidation date as 'yyyymmdd'
        lang: language (default 'pt')
        fmt: 'html' or 'pdf' (default 'html')
        """
        self.logger.info(f"Requesting consolidated act: type={act_type}, number={number}, year={year}, region={region}, cons_date={cons_date}, lang={lang}, fmt={fmt}")
        url = f"{self.BASE_URL}/{act_type}/{number}/{year}/{region}/cons/{cons_date}/{lang}/{fmt}"
        return self._download(url, f"dre_cons_{act_type}_{number}_{year}_{region}_{cons_date}_{lang}.{fmt}", fmt)

    def _download(self, url, filename, fmt=None):
        self.logger.info(f"Downloading from URL: {url} to filename: {filename}")
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '')
            if fmt == 'pdf':
                if 'pdf' in content_type:
                    file_path = os.path.join(self.download_dir, filename)
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    return file_path
                else:
                    # Print the error response to the screen for user
                    print("Error: Expected PDF but got:")
                    print(response.text)
                    return None
            # For non-PDF, save as usual
            file_path = os.path.join(self.download_dir, filename)
            with open(file_path, "wb") as f:
                f.write(response.content)
            return file_path
        except requests.HTTPError as e:
            logging.error(f"HTTP error: {e} - {getattr(e.response, 'text', '')}")
            return None
        except Exception as e:
            logging.error(f"Error downloading from DRE: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(description='Download a document from the Portuguese DRE ELI portal.')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Journal
    journal_parser = subparsers.add_parser('journal')
    journal_parser.add_argument('--series', type=str, required=True)
    journal_parser.add_argument('--number', type=str, required=True)
    journal_parser.add_argument('--year', type=str, required=True)
    journal_parser.add_argument('--supplement', type=str, default='0')
    journal_parser.add_argument('--lang', type=str, default='pt')
    journal_parser.add_argument('--fmt', type=str, default='html')
    journal_parser.add_argument('--dir', type=str, default='./tests/data/portugal')
    journal_parser.add_argument('--logdir', type=str, default='./tests/logs')

    # Legal act
    act_parser = subparsers.add_parser('act')
    act_parser.add_argument('--type', type=str, required=True)
    act_parser.add_argument('--number', type=str, required=True)
    act_parser.add_argument('--year', type=str, required=True)
    act_parser.add_argument('--month', type=str, required=True)
    act_parser.add_argument('--day', type=str, required=True)
    act_parser.add_argument('--region', type=str, required=True)
    act_parser.add_argument('--lang', type=str, default='pt')
    act_parser.add_argument('--fmt', type=str, default='html')
    act_parser.add_argument('--dir', type=str, default='./tests/data/portugal')
    act_parser.add_argument('--logdir', type=str, default='./tests/logs')

    # Consolidated
    cons_parser = subparsers.add_parser('consolidated')
    cons_parser.add_argument('--type', type=str, required=True)
    cons_parser.add_argument('--number', type=str, required=True)
    cons_parser.add_argument('--year', type=str, required=True)
    cons_parser.add_argument('--region', type=str, required=True)
    cons_parser.add_argument('--cons_date', type=str, required=True)
    cons_parser.add_argument('--lang', type=str, default='pt')
    cons_parser.add_argument('--fmt', type=str, default='html')
    cons_parser.add_argument('--dir', type=str, default='./tests/data/portugal')
    cons_parser.add_argument('--logdir', type=str, default='./tests/logs')

    args = parser.parse_args()
    os.makedirs(args.dir, exist_ok=True)
    os.makedirs(args.logdir, exist_ok=True)
    client = PortugalDREClient(download_dir=args.dir, log_dir=args.logdir)
    file_path = None
    if args.command == 'journal':
        file_path = client.get_journal(args.series, args.number, args.year, args.supplement, args.lang, args.fmt)
    elif args.command == 'act':
        file_path = client.get_legal_act(args.type, args.number, args.year, args.month, args.day, args.region, args.lang, args.fmt)
    elif args.command == 'consolidated':
        file_path = client.get_consolidated(args.type, args.number, args.year, args.region, args.cons_date, args.lang, args.fmt)
    else:
        client.logger.error("Unknown command.")
    if file_path:
        logging.info(f"Downloaded to {file_path}")
        print(f"Downloaded to {file_path}")
    else:
        logging.error("Download failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
