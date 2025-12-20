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

    def download(self, document_type, series=None, number=None, year=None, supplement=0, act_type=None, month=None, day=None, region=None, cons_date=None, lang='pt', fmt='html'):
        """
        Download documents from the Portuguese DRE ELI portal.
        
        Parameters
        ----------
        document_type : str
            Type of document: 'journal', 'legal_act', or 'consolidated'
        series : str, optional
            For journals: series ('1', '1a', '1b', etc.)
        number : str, optional
            Document number in the year
        year : str, optional
            Year of publication
        supplement : int, optional
            For journals: supplement number (default 0)
        act_type : str, optional
            For legal acts: type ('lei', 'dec-lei', 'declegreg', etc.)
        month : str, optional
            For legal acts: month of publication
        day : str, optional
            For legal acts: day of publication
        region : str, optional
            For legal acts: region ('p', 'm', 'a')
        cons_date : str, optional
            For consolidated acts: consolidation date as 'yyyymmdd'
        lang : str, optional
            Language (default 'pt')
        fmt : str, optional
            Format: 'html' or 'pdf' (default 'html')
            
        Returns
        -------
        str or None
            Path to downloaded file or None if failed
        """
        if document_type == 'journal':
            if not all([series, number, year]):
                raise ValueError("Journal downloads require series, number, and year")
            url = f"{self.BASE_URL}/diario/{series}/{number}/{year}/{supplement}/{lang}/{fmt}"
            filename = f"dre_journal_{series}_{number}_{year}_{supplement}_{lang}.{fmt}"
            self.logger.info(f"Requesting journal: series={series}, number={number}, year={year}, supplement={supplement}, lang={lang}, fmt={fmt}")
            
        elif document_type == 'legal_act':
            if not all([act_type, number, year, month, day, region]):
                raise ValueError("Legal act downloads require act_type, number, year, month, day, and region")
            url = f"{self.BASE_URL}/{act_type}/{number}/{year}/{month}/{day}/{region}/dre/{lang}/{fmt}"
            filename = f"dre_act_{act_type}_{number}_{year}_{month}_{day}_{region}_{lang}.{fmt}"
            self.logger.info(f"Requesting legal act: type={act_type}, number={number}, year={year}, month={month}, day={day}, region={region}, lang={lang}, fmt={fmt}")
            
        elif document_type == 'consolidated':
            if not all([act_type, number, year, region, cons_date]):
                raise ValueError("Consolidated act downloads require act_type, number, year, region, and cons_date")
            url = f"{self.BASE_URL}/{act_type}/{number}/{year}/{region}/cons/{cons_date}/{lang}/{fmt}"
            filename = f"dre_cons_{act_type}_{number}_{year}_{region}_{cons_date}_{lang}.{fmt}"
            self.logger.info(f"Requesting consolidated act: type={act_type}, number={number}, year={year}, region={region}, cons_date={cons_date}, lang={lang}, fmt={fmt}")
            
        else:
            raise ValueError(f"Unknown document_type: {document_type}. Must be 'journal', 'legal_act', or 'consolidated'")
            
        return self._download(url, filename, fmt)

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
