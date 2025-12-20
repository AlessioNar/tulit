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
            if fmt == 'pdf' and 'pdf' not in content_type:
                self.logger.error(f"Expected PDF response but got: {content_type}")
                sys.exit(1)
            if fmt == 'xml' and 'xml' not in content_type:
                self.logger.error(f"Expected XML response but got: {content_type}")
                sys.exit(1)
            if fmt == 'html' and 'html' not in content_type:
                self.logger.error(f"Expected HTML response but got: {content_type}")
                sys.exit(1)
            if fmt == 'json' and 'json' not in content_type:
                self.logger.error(f"Expected JSON response but got: {content_type}")
                sys.exit(1)
            if fmt == 'txt' and 'plain' not in content_type:
                self.logger.error(f"Expected TXT response but got: {content_type}")
                sys.exit(1)
            if fmt == 'xhtml' and 'xhtml' not in content_type:
                self.logger.error(f"Expected XHTML response but got: {content_type}")
                sys.exit(1)
            if fmt == 'zip' and 'zip' not in content_type:
                self.logger.error(f"Expected ZIP response but got: {content_type}")
                sys.exit(1)
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
