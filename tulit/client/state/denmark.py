"""
Client for Retsinformation, the official Danish legal information system.

Every act is available as LexDania XML at its ELI (``/eli/lta/{year}/{number}/xml``
or ``/eli/accn/{accession number}/xml``). Original acts (lov, LOV) and their
consolidations (lovbekendtgørelse, LBK) are separate documents: an LBK names
the act it consolidates in its introduction ("Herved bekendtgøres lov nr. 502
af 23. maj 2018 ..."), which links the two.

Run by Civilstyrelsen (Ministry of Justice).
"""
import os
import re
from typing import Any, Optional

import requests
from lxml import etree
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError

RETSINFORMATION = 'https://www.retsinformation.dk'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'

MONTHS = {
    'januar': 1, 'februar': 2, 'marts': 3, 'april': 4, 'maj': 5, 'juni': 6,
    'juli': 7, 'august': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12,
}
_CONSOLIDATED_ACT = re.compile(
    r'bekendtgøres\s+lov\s+nr\.?\s*(\d+)\s+af\s+(\d{1,2})\.\s*(\w+)\s+(\d{4})', re.IGNORECASE)
_ELI_PATH = re.compile(r'^(lta/\d{4}/\d+|accn/[A-Z]\d+)$')


def normalise_eli_path(identifier: str) -> str:
    """'lta/2018/502', 'eli/lta/2018/502' or a full ELI URI -> 'lta/2018/502'."""
    path = re.sub(r'^https?://(www\.)?retsinformation\.dk/', '', identifier.strip()).strip('/')
    path = re.sub(r'^eli/', '', path)
    path = re.sub(r'/(xml|pdf|html)$', '', path)
    if not _ELI_PATH.match(path):
        raise ValueError(
            f"'{identifier}' is not a Retsinformation identifier; use e.g. 'lta/2018/502' "
            "or 'accn/A20180050230'"
        )
    return path


def consolidated_act(root: etree._Element) -> Optional[tuple[str, str]]:
    """
    The act an LBK consolidates, from its introduction.

    Returns (ELI path, ISO date of the act), e.g. ('lta/2018/502', '2018-05-23'),
    or None if the document is not a consolidation of a lov.
    """
    intro = root.find('.//Indledning')
    if intro is None:
        return None
    match = _CONSOLIDATED_ACT.search(' '.join(''.join(intro.itertext()).split()))
    if not match:
        return None
    number, day, month, year = match.groups()
    month_number = MONTHS.get(month.lower())
    date = f'{year}-{month_number:02d}-{int(day):02d}' if month_number else None
    return f'lta/{year}/{number}', date


class RetsinformationClient(Client):
    """Downloads Danish legislation as LexDania XML from Retsinformation."""

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        retry = Retry(total=4, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=('GET',))
        self.session.mount('https://', HTTPAdapter(max_retries=retry))
        if proxies:
            self.session.proxies.update(proxies)

    def download(self, identifier: str) -> str:
        """Download the LexDania XML of an act; returns the file path."""
        path = normalise_eli_path(identifier)
        target = os.path.join(self.download_dir, 'DK', path.replace('/', '_') + '.xml')
        if not os.path.exists(target):
            content = self._get(f'{RETSINFORMATION}/eli/{path}/xml').content
            if not content.lstrip().startswith(b'<?xml') and b'<Dokument' not in content[:500]:
                raise FileLoadError(f"Retsinformation has no XML document for {path}")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as f:
                f.write(content)
        return target

    def search(self, text: str) -> list[dict[str, Any]]:
        """Documents matching ``text`` in the Retsinformation search."""
        response = self._get(f'{RETSINFORMATION}/api/documentsearch', params={'t': text})
        try:
            return response.json().get('documents', [])
        except ValueError as e:
            raise NetworkError(f"Unexpected Retsinformation search response: {e}") from e

    def find_consolidation(self, act_path: str, title: str) -> Optional[str]:
        """
        The current consolidation (LBK) of an act, or None.

        Searches Retsinformation for the act's title and keeps the in-force
        consolidations whose introduction names exactly this act.
        """
        for document in self.search(title):
            link = (document.get('retsinfoLink') or '').strip('/')
            if document.get('isHistoryFlag') or not str(document.get('documentTypeEliCode', '')).startswith('LBK'):
                continue
            candidate = link.removeprefix('eli/')
            try:
                root = etree.parse(self.download(candidate)).getroot()
            except (FileLoadError, NetworkError, ValueError, etree.XMLSyntaxError):
                continue
            found = consolidated_act(root)
            if found and found[0] == act_path:
                return candidate
        return None

    def _get(self, url: str, params: Optional[dict] = None) -> requests.Response:
        try:
            response = self.session.get(url, params=params, timeout=60)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            raise NetworkError(f"Retsinformation request failed for {url}: {e}") from e
