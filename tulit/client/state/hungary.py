"""
Client for the Nemzeti Jogszabálytár (NJT), Hungary's official legislation database.

The Nemzeti Jogszabálytár (https://njt.jog.gov.hu, Ministry of Justice and
Magyar Közlönykiadó) holds each act as promulgated in the Magyar Közlöny
and in each of its time states (időállapot), addressed by its NJT id
('2011-112-00-00') and version:

- /jogszabaly/<id>.0 is the text as promulgated (közlönyállapot);
- /jogszabaly/<id>.<n> is time state n; /ajax/collectAllDocumentVersion.json
  lists them with the dates each came into force and expired.

ELI (https://njt.jog.gov.hu/eli/TV/2011/112[/kozlony|/YYYY-MM-DD]) redirects
to the matching NJT page, so citations are resolved through it.
"""
import datetime
import os
import re
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError

NJT = 'https://njt.jog.gov.hu'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'
_DOCUMENT = re.compile(r'/jogszabaly/(?P<id>\d{4}-\d+-\d{2}-\d{2})(?:\.(?P<version>\d+))?')
UNKNOWN = '3000-01-01'
"""NJT's date for a time state whose coming into force is not yet known."""


class NJTClient(Client):
    """Downloads Hungarian acts from the Nemzeti Jogszabálytár."""

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        retry = Retry(total=5, connect=5, read=5, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=('GET', 'POST'))
        self.session.mount('https://', HTTPAdapter(max_retries=retry))
        if proxies:
            self.session.proxies.update(proxies)

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        try:
            response = self.session.request(method, url, timeout=180, **kwargs)
        except requests.RequestException as e:
            raise NetworkError(f"NJT request failed for {url}: {e}") from e
        if response.status_code == 404:
            raise FileLoadError(f"The Nemzeti Jogszabálytár has nothing at {url}")
        if response.status_code != 200:
            raise NetworkError(f"The Nemzeti Jogszabálytár returned HTTP {response.status_code} for {url}")
        return response

    def resolve(self, eli_path: str) -> tuple[str, Optional[str]]:
        """The NJT id (and version) an ELI path ('TV/2011/112', 'R/2005/Korm/335/kozlony') leads to."""
        response = self._request('GET', f'{NJT}/eli/{eli_path.strip("/")}')
        match = _DOCUMENT.search(response.url)
        if not match:
            raise FileLoadError(f"The Nemzeti Jogszabálytár has no act for the ELI {NJT}/eli/{eli_path}")
        return match.group('id'), match.group('version')

    def versions(self, document_id: str) -> list[dict[str, Any]]:
        """Time states of an act, oldest first: {'version', 'from', 'until'} with ISO dates (None: open)."""
        response = self._request('POST', f'{NJT}/ajax/collectAllDocumentVersion.json',
                                 data={'documentId': document_id})
        found = []
        for item in response.json().get('data') or []:
            start = (item.get('comingIntoForce') or '')[:10] or None
            end = (item.get('expiresOn') or '')[:10] or None
            found.append({'version': int(item['version']), 'from': start,
                          'until': None if end in (None, UNKNOWN) else end})
        return sorted(found, key=lambda v: v['version'])

    @staticmethod
    def in_force(versions: list[dict[str, Any]], date: Optional[str] = None) -> Optional[dict[str, Any]]:
        """The time state in force on a date (today by default); None before the act came into force."""
        target = date or datetime.date.today().isoformat()
        known = [v for v in versions if v['from'] and v['from'] != UNKNOWN and v['from'] <= target
                 and (v['until'] is None or target < v['until'])]
        return known[-1] if known else None

    def download(self, document_id: str, version: int) -> str:
        """Download a version of an act (0: as promulgated) and return its path."""
        target = os.path.join(self.download_dir, 'HU', f'{document_id}.{version}.html')
        if os.path.exists(target):
            return target
        response = self._request('GET', f'{NJT}/jogszabaly/{document_id}.{version}')
        if b'id="jogszab"' not in response.content:
            raise FileLoadError(f"The Nemzeti Jogszabálytár has no text for {document_id}.{version}")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as f:
            f.write(response.content)
        return target

    @staticmethod
    def eli(path: str) -> Optional[str]:
        """The ELI an NJT page gives for its act."""
        with open(path, encoding='utf-8', errors='replace') as f:
            match = re.search(r'https://njt\.jog\.gov\.hu/eli/[A-Za-z_]+(?:/[\w]+)+', f.read())
        return match.group(0) if match else None
