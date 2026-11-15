"""
Clients for Swedish statutes (Svensk författningssamling, SFS).

- ``RiksdagenClient``: the Riksdag open data (data.riksdagen.se), which
  republishes the Government Offices' consolidated text of every statute,
  as in force now, with its metadata. API documentation: https://data.riksdagen.se
- ``SFSClient``: the official electronic SFS (svenskforfattningssamling.se),
  where the Government Offices have published every act as adopted, one PDF
  per SFS number, since 1 April 2018 (SFS 2018:160 onwards). Earlier acts
  appeared only in the printed SFS.
"""
import glob
import os
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError

RIKSDAGEN = 'https://data.riksdagen.se'
SFS = 'https://svenskforfattningssamling.se'
# The first act published in the electronic SFS (1 April 2018)
FIRST_ELECTRONIC = (2018, 160)
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'


def _session(proxies=None) -> requests.Session:
    session = requests.Session()
    session.headers['User-Agent'] = USER_AGENT
    retry = Retry(total=4, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=('GET', 'HEAD'))
    session.mount('https://', HTTPAdapter(max_retries=retry))
    if proxies:
        session.proxies.update(proxies)
    return session


class RiksdagenClient(Client):
    """Downloads consolidated Swedish statutes from the Riksdag open data."""

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = _session(proxies)

    def _get(self, url: str) -> requests.Response:
        try:
            response = self.session.get(url, timeout=120)
        except requests.RequestException as e:
            raise NetworkError(f"Riksdag open data request failed for {url}: {e}") from e
        if response.status_code == 404 or not response.content.strip():
            raise FileLoadError(f"The Riksdag open data has no document at {url}")
        if response.status_code != 200:
            raise NetworkError(f"The Riksdag open data returned HTTP {response.status_code} for {url}")
        return response

    def metadata(self, document_id: str) -> dict[str, Any]:
        """Metadata of a statute, e.g. 'sfs-2018-218': title, issue date ('datum'), last amendment ('subtitel')."""
        data = self._get(f'{RIKSDAGEN}/dokumentstatus/{document_id}.json').json()
        document = (data.get('dokumentstatus') or {}).get('dokument')
        if not document:
            raise FileLoadError(f"The Riksdag open data has no statute {document_id}")
        return document

    def download(self, document_id: str) -> str:
        """Download the consolidated HTML text of a statute and return its path."""
        target = os.path.join(self.download_dir, 'SE', f'{document_id}.html')
        if not os.path.exists(target):
            response = self._get(f'{RIKSDAGEN}/dokument/{document_id}.html')
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as f:
                f.write(response.content)
        return target


def pdf_url(year: int, number: str, month: int) -> str:
    """URL of an act in the electronic SFS: the PDFs are filed by the month they were uploaded in."""
    return f'{SFS}/sites/default/files/sfs/{year}-{month:02d}/SFS{year}-{number}.pdf'


def _months(year: int, number: str, issued: Optional[str]) -> list[int]:
    """
    The months to look for an act in, most likely first.

    An act is uploaded in the month it is issued or the next; without the
    issue date, SFS numbers run at roughly 1 500 a year.
    """
    if issued and issued[:4] == str(year):
        guess = int(issued[5:7])
    else:
        guess = min(12, 1 + int(''.join(c for c in number if c.isdigit())) * 12 // 1500)
    return sorted(range(1, 13), key=lambda month: (abs(month - guess - 0.4), month))


class SFSClient(Client):
    """Downloads acts as adopted from the official electronic Svensk författningssamling."""

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = _session(proxies)

    def _request(self, method: str, url: str) -> requests.Response:
        try:
            return self.session.request(method, url, timeout=120)
        except requests.RequestException as e:
            raise NetworkError(f"Svensk författningssamling request failed for {url}: {e}") from e

    def download(self, year: int, number: str, issued: Optional[str] = None) -> tuple[str, str]:
        """
        Download the PDF of SFS ``year``:``number`` and return its path and URL.

        ``issued``: the ISO date the act was issued, if known, to find it in fewer requests.
        """
        folder = os.path.join(self.download_dir, 'SE', 'sfs')
        cached = glob.glob(os.path.join(folder, f'{year}-[0-9][0-9]', f'SFS{year}-{number}.pdf'))
        if cached:
            month = int(os.path.basename(os.path.dirname(cached[0]))[5:])
            return cached[0], pdf_url(year, number, month)
        for month in _months(year, number, issued):
            url = pdf_url(year, number, month)
            response = self._request('HEAD', url)
            if response.status_code == 404:
                continue
            if response.status_code != 200:
                raise NetworkError(f"Svensk författningssamling returned HTTP {response.status_code} for {url}")
            response = self._request('GET', url)
            if response.status_code != 200 or not response.content.startswith(b'%PDF'):
                raise NetworkError(f"Svensk författningssamling returned no PDF for {url}")
            target = os.path.join(folder, f'{year}-{month:02d}', f'SFS{year}-{number}.pdf')
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as f:
                f.write(response.content)
            return target, url
        raise FileLoadError(f"Svensk författningssamling has no SFS {year}:{number} "
                            f"(not published in {year}, or not yet)")
