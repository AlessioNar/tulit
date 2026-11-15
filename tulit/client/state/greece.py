"""
Client for the Greek Government Gazette (Εφημερίδα της Κυβερνήσεως, ΦΕΚ).

The National Printing House (Εθνικό Τυπογραφείο) runs the Gazette's search
at https://search.et.gr, whose API finds laws, presidential decrees and acts
of legislative content by number and year ('/searchlegislation') and issues
by part, number and year ('/simplesearch'). Each issue is a PDF in the
National Printing House's storage, named after its year, part and number:

    https://ia37rg02wpsa01.blob.core.windows.net/fek/01/2019/20190100137.pdf

for Part A (Τεύχος Α΄, group 01), issue 137 of 2019.
"""
import datetime
import json
import os
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError

API = 'https://searchetv99.azurewebsites.net/api'
STORAGE = 'https://ia37rg02wpsa01.blob.core.windows.net/fek'
SEARCH = 'https://search.et.gr'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'
# Catalogues of the legislation search: law, presidential decree, act of legislative content
CATALOGUES = {'law': '1', 'decree': '2', 'act': '3'}
# Parts (τεύχη) of the Gazette and their group numbers
PARTS = {'Α': '1', 'Β': '2', 'Γ': '3', 'Δ': '4'}


def pdf_url(part: str, number: str, year: str) -> str:
    """The PDF of an issue: part group ('1' for Α), issue number and year."""
    group = part.zfill(2)
    return f'{STORAGE}/{group}/{year}/{year}{group}{number.zfill(5)}.pdf'


def _date(text: Optional[str]) -> Optional[str]:
    """'08/29/2019 00:00:00' -> '2019-08-29'."""
    if not text:
        return None
    try:
        return datetime.datetime.strptime(text.split(' ')[0], '%m/%d/%Y').date().isoformat()
    except ValueError:
        return None


class GovernmentGazetteClient(Client):
    """Finds and downloads acts in the Greek Government Gazette."""

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        retry = Retry(total=4, connect=4, read=4, backoff_factor=1,
                      status_forcelist=(429, 500, 502, 503, 504), allowed_methods=('GET', 'POST'))
        self.session.mount('https://', HTTPAdapter(max_retries=retry))
        if proxies:
            self.session.proxies.update(proxies)

    def _search(self, endpoint: str, body: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            response = self.session.post(f'{API}/{endpoint}', json=body, timeout=120)
        except requests.RequestException as e:
            raise NetworkError(f"Government Gazette search failed: {e}") from e
        if response.status_code != 200:
            raise NetworkError(f"Government Gazette search returned HTTP {response.status_code}")
        found = response.json()
        if found.get('status') != 'ok':
            raise NetworkError(f"Government Gazette search failed: {found.get('message')}")
        return json.loads(found.get('data') or '[]')

    @staticmethod
    def _issue(row: dict[str, Any]) -> dict[str, Any]:
        return {
            'part': row.get('search_IssueGroupID'),
            'issue': row.get('search_DocumentNumber'),
            'label': row.get('search_PrimaryLabel'),
            'date_document': _date(row.get('search_IssueDate')),
            'date_publication': _date(row.get('search_PublicationDate')),
            'pages': row.get('search_Pages'),
            'title': row.get('search_Description'),
        }

    def find_act(self, kind: str, number: str, year: str) -> dict[str, Any]:
        """The issue publishing law (or decree, or act of legislative content) ``number`` of ``year``."""
        rows = self._search('searchlegislation', {'legislationCatalogues': CATALOGUES[kind],
                                                  'legislationNumber': number, 'selectYear': [year]})
        rows = [row for row in rows if row.get('search_LawProtocolNumber') == number] or rows
        if not rows:
            raise FileLoadError(f"The Government Gazette has no {kind} {number}/{year}")
        return self._issue(rows[0])

    def find_issue(self, part: str, number: str, year: str) -> dict[str, Any]:
        """An issue of the Gazette: part group ('1' for Α), number and year."""
        rows = self._search('simplesearch', {'selectYear': [year], 'selectIssue': [part], 'documentNumber': number})
        rows = [row for row in rows if row.get('search_DocumentNumber') == number]
        if not rows:
            raise FileLoadError(f"The Government Gazette has no issue {number}/{year} in part {part}")
        return self._issue(rows[0])

    def download(self, issue: dict[str, Any], year: str) -> str:
        """Download the PDF of an issue and return its path."""
        url = pdf_url(issue['part'], issue['issue'], year)
        target = os.path.join(self.download_dir, 'GR', os.path.basename(url))
        if not os.path.exists(target):
            try:
                response = self.session.get(url, timeout=300)
            except requests.RequestException as e:
                raise NetworkError(f"Government Gazette request failed for {url}: {e}") from e
            if response.status_code == 404:
                raise FileLoadError(f"The Government Gazette has no PDF at {url}")
            if not response.content.startswith(b'%PDF'):
                raise FileLoadError(f"The Government Gazette did not return a PDF for {url}")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as f:
                f.write(response.content)
        return target
