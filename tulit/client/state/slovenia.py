"""
Client for PISRS, the legal information system of the Republic of Slovenia.

PISRS (https://pisrs.si, Ministry of Justice) holds each act of the Register
predpisov under an id ('ZAKO7959' for the Zakon o varstvu osebnih podatkov)
with its metadata, its text as published in the Official Gazette (Uradni
list RS) and its unofficial consolidated versions (neuradno prečiščeno
besedilo, NPB), each as HTML. Its JSON API is the one its web pages use:

- /api/rezultat/zbirka/id/<id>: the act's metadata and versions (or /sop/<SOP>, by the act's
  number in the Official Gazette, '2022-01-4187');
- /api/datoteke/integracije/<file id>: the HTML of a version;
- /api/filter/filter: search by words of the title or by gazette issue.
"""
import os
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError

PISRS = 'https://pisrs.si'
API = f'{PISRS}/api'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'
REGISTER = 'Register predpisov'


class PisrsClient(Client):
    """Finds and downloads Slovenian acts from PISRS."""

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        # Retry dropped connections too; searches are POST requests without side effects
        retry = Retry(total=5, connect=5, read=5, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=('GET', 'POST'))
        self.session.mount('https://', HTTPAdapter(max_retries=retry))
        if proxies:
            self.session.proxies.update(proxies)

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        try:
            response = self.session.request(method, url, timeout=120, **kwargs)
        except requests.RequestException as e:
            raise NetworkError(f"PISRS request failed for {url}: {e}") from e
        if response.status_code == 404:
            raise FileLoadError(f"PISRS has nothing at {url}")
        if response.status_code != 200:
            raise NetworkError(f"PISRS returned HTTP {response.status_code} for {url}")
        return response

    def record(self, act_id: str, key: str = 'id') -> dict[str, Any]:
        """Metadata and versions of an act, by PISRS id ('ZAKO7959') or, with ``key='sop'``, gazette number."""
        try:
            found = self._request('GET', f'{API}/rezultat/zbirka/{key}/{act_id}').json()
        except ValueError as e:
            raise FileLoadError(f"PISRS returned no record for {act_id}") from e
        data = found.get('data') if isinstance(found, dict) else None
        if not data or not data.get('evidencniPodatki'):
            raise FileLoadError(f"PISRS has no act {act_id}")
        return data

    def search(self, title: Optional[str] = None, issue: Optional[tuple[str, str]] = None) -> list[dict[str, Any]]:
        """Acts of the Register whose title holds ``title``, or published in gazette ``issue`` (number, year)."""
        body: dict[str, Any] = {'nazivZbirke': [REGISTER]}
        if title:
            body.update(simpleSearch=True, besedilo={'word1': title, 'word1InTitle': True, 'word1InContent': False})
        if issue:
            body['uradniListObjava'] = {'stevilkaObjave': issue[0], 'letoObjave': issue[1]}
        found = self._request('POST', f'{API}/filter/filter', json=body).json()
        return ((found or {}).get('data') or {}).get('seznam') or []

    @staticmethod
    def versions(record: dict[str, Any]) -> list[dict[str, Any]]:
        """The versions of an act, oldest first: name ('Osnovni', 'NPB 1', ...), date it applies from, HTML file id."""
        dates = {v['id']: v.get('datumZacetkaUporabe')
                 for v in (record.get('besedilo') or {}).get('npbVerzije') or []}
        found = []
        for entry in record.get('datoteke') or []:
            version = entry.get('npbVerzija') or {}
            html_id = next((f['id'] for f in entry.get('datoteke') or [] if f.get('tip') == 'HTML_DOCUMENT'), None)
            if html_id is None:
                continue
            name = version.get('naziv') or ''
            number = 0 if name == 'Osnovni' else int(''.join(c for c in name if c.isdigit()) or 0)
            found.append({'name': name, 'number': number, 'html': html_id,
                          'date': version.get('datumZacetkaUporabe') or dates.get(version.get('id'))})
        return sorted(found, key=lambda v: v['number'])

    def download(self, act_id: str, version: dict[str, Any]) -> str:
        """Download the HTML of a version of an act and return its path."""
        target = os.path.join(self.download_dir, 'SI', f"{act_id}_{version['number']}.html")
        if os.path.exists(target):
            return target
        response = self._request('GET', f"{API}/datoteke/integracije/{version['html']}")
        if b'mainText' not in response.content:
            raise FileLoadError(f"PISRS returned no text for {act_id} ({version['name']})")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as f:
            f.write(response.content)
        return target
