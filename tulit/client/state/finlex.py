import logging
import re
import requests
from tulit.client.client import Client
from tulit.parser.exceptions import ContentTypeError
import os

_LISTED = re.compile(r'/statute-consolidated/(?P<year>\d{4})/(?P<number>[\d-]+)/(?P<language>[a-z]{3})@(?P<version>\w*)$')


def _number_key(number):
    """'39-001' -> (39, 1), for comparing statute numbers as the API sorts them."""
    return tuple(int(part) for part in str(number).split('-') if part.isdigit())


class FinlexClient(Client):
    """
    Client for retrieving legal documents from the Finlex Open Data REST API.
    API docs: https://opendata.finlex.fi/finlex/avoindata/v1
    """
    BASE_URL = "https://opendata.finlex.fi/finlex/avoindata/v1"

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/xml",
            "Accept-Encoding": "gzip",
            # The API rejects requests without a User-Agent
            "User-Agent": "tulit (+https://github.com/AlessioNar/tulit)",
        })
        if proxies:
            self.session.proxies.update(proxies)
        self.logger = logging.getLogger(self.__class__.__name__)

    PAGE_SIZE = 10

    def _listing(self, year, page):
        """One page of the consolidated statutes of a year, sorted by number: (number, language, version)."""
        response = self.session.get(
            f"{self.BASE_URL}/akn/fi/act/statute-consolidated/list",
            params={'format': 'json', 'startYear': year, 'endYear': year, 'sortBy': 'number',
                    'limit': self.PAGE_SIZE, 'page': page},
            headers={'Accept': 'application/json'}, timeout=30)
        response.raise_for_status()
        found = []
        for item in response.json():
            match = _LISTED.search(item.get('akn_uri', ''))
            if match:
                found.append((match.group('number'), match.group('language'), match.group('version')))
        return found

    def versions(self, year, number, language="fin"):
        """
        The consolidated versions of a statute in a language, as the version ids Finlex gives them:
        '' for the text as first consolidated, else the amending statute ('20180817' for 817/2018).

        The listing has ten statutes a page, sorted by number: the pages holding the statute are
        found by bisection.
        """
        target = _number_key(number)
        pages = {}

        def page(n):
            if n not in pages:
                pages[n] = self._listing(year, n)
            return pages[n]

        # The first page whose last statute is not below the target
        low, high = 1, 1
        while page(high) and _number_key(page(high)[-1][0]) < target:
            low, high = high + 1, high * 2
        while low < high:
            middle = (low + high) // 2
            if page(middle) and _number_key(page(middle)[-1][0]) < target:
                low = middle + 1
            else:
                high = middle
        found, n = [], low
        while page(n):
            entries = [e for e in page(n) if _number_key(e[0]) == target]
            found.extend(version for listed, lang, version in entries if lang == language)
            if _number_key(page(n)[-1][0]) > target:
                break
            n += 1
        return sorted(set(found))

    def download(self, year, number, lang="fi", doc_type="act", fmt="xml",
                 consolidated=False, language="fin", version=""):
        """
        Download a statute from the Finlex Open Data API as Akoma Ntoso.

        Parameters
        ----------
        year, number : str or int
            The statute's year and number (e.g. 2018, 1050 for 1050/2018).
        lang : str
            Country segment of the Akoma Ntoso path (always 'fi').
        doc_type : str
            Akoma Ntoso document type ('act').
        fmt : str
            Expected format of the response ('xml').
        consolidated : bool
            Download the consolidated text in force (statute-consolidated)
            instead of the statute as adopted.
        language : str
            'fin' (Finnish) or 'swe' (Swedish).
        version : str
            A consolidated version (see ``versions``); '' is the text as first consolidated.

        Example endpoint: /akn/fi/act/statute-consolidated/2018/1050/fin@
        """
        kind = 'statute-consolidated' if consolidated else 'statute'
        url = f"{self.BASE_URL}/akn/{lang}/{doc_type}/{kind}/{year}/{number}/{language}%40{version}"
        try:
            self.logger.info(f"Requesting Finlex statute: year={year}, number={number}, lang={lang}, doc_type={doc_type}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '')
            if fmt == 'xml' and 'xml' not in content_type:
                raise ContentTypeError(f"Expected XML from Finlex but got: {content_type}", content_type)
            if fmt == 'pdf' and 'pdf' not in content_type:
                raise ContentTypeError(f"Expected PDF from Finlex but got: {content_type}", content_type)
            if fmt == 'html' and 'html' not in content_type:
                raise ContentTypeError(f"Expected HTML from Finlex but got: {content_type}", content_type)
            suffix = f"_consolidated{'_' + version if version else ''}" if consolidated else ''
            filename = f"finlex_{year}_{number}{suffix}_{language}.{fmt}"
            file_path = os.path.join(self.download_dir, filename)
            with open(file_path, "wb") as f:
                f.write(response.content)
            self.logger.info(f"Downloaded Finlex statute to {file_path}")
            return file_path
        except ContentTypeError:
            raise
        except requests.HTTPError as e:
            self.logger.error(f"HTTP error: {e} - {getattr(e.response, 'text', '')}")
            return None
        except Exception as e:
            self.logger.error(f"Error downloading Finlex statute: {e}")
            return None
