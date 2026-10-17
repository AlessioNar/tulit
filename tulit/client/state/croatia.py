"""
Client for Narodne novine, the Official Gazette of the Republic of Croatia.

Every item of the official part of the gazette has an ELI
(https://narodne-novine.nn.hr/eli/sluzbeni/<year>/<issue>/<item>), which
serves its text as HTML and, under /rdf, its ELI metadata. Some recent
items are published only as PDF.
"""
import os
from typing import Any, Optional

import requests
from lxml import etree
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError

NN_ELI = 'https://narodne-novine.nn.hr/eli/sluzbeni'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'
ELI = 'http://data.europa.eu/eli/ontology#'
RDF = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'


class NarodneNovineClient(Client):
    """Downloads acts and their ELI metadata from Narodne novine."""

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        retry = Retry(total=4, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=('GET',))
        self.session.mount('https://', HTTPAdapter(max_retries=retry))
        if proxies:
            self.session.proxies.update(proxies)

    def _get(self, url: str) -> requests.Response:
        try:
            response = self.session.get(url, timeout=120)
        except requests.RequestException as e:
            raise NetworkError(f"Narodne novine request failed for {url}: {e}") from e
        if response.status_code == 404 or 'stranica404' in response.url:
            raise FileLoadError(f"Narodne novine has no item at {url}")
        if response.status_code != 200:
            raise NetworkError(f"Narodne novine returned HTTP {response.status_code} for {url}")
        return response

    def download(self, year: str, issue: str, item: str) -> str:
        """Download the HTML of an item ('2018', '42', '805') and return its path."""
        target = os.path.join(self.download_dir, 'HR', f'{year}_{issue}_{item}.html')
        if not os.path.exists(target):
            response = self._get(f'{NN_ELI}/{year}/{issue}/{item}')
            if 'Nije pronađeno' in response.text[:3000]:
                raise FileLoadError(f"Narodne novine has no item {year}/{issue}/{item}")
            if b'sl-content' not in response.content:
                raise FileLoadError(f"Narodne novine publishes item {year}/{issue}/{item} only as PDF "
                                    f"({NN_ELI}/{year}/{issue}/{item}/pdf)")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as f:
                f.write(response.content)
        return target

    def metadata(self, year: str, issue: str, item: str) -> dict[str, Any]:
        """ELI metadata of an item: title, dates and the acts it repeals or amends (empty if unavailable)."""
        try:
            response = self._get(f'{NN_ELI}/{year}/{issue}/{item}/rdf')
            root = etree.fromstring(response.content)
        except (FileLoadError, etree.XMLSyntaxError):
            return {}

        def values(name: str) -> list[str]:
            return [e.get(f'{{{RDF}}}resource') or (e.text or '').strip() for e in root.iter(f'{{{ELI}}}{name}')]

        def first(name: str) -> Optional[str]:
            found = values(name)
            return found[0] if found else None

        return {
            'title': first('title'),
            'date_document': first('date_document'),
            'date_publication': first('date_publication'),
            'repeals': values('repeals'),
            'amends': values('changes') + values('amends'),
        }
