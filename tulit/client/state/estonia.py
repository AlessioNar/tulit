"""
Client for Riigi Teataja, the Estonian State Gazette.

Every text of an act is published separately: the original text (algtekst)
and each consolidated text (terviktekst) in force for a period. The texts
of one act share a group id (terviktekstiGrupiID). The search API lists
them with their validity periods; the public API serves each text as XML.

Run by the Ministry of Justice and Digital Affairs.
"""
import os
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError

RIIGI_TEATAJA = 'https://www.riigiteataja.ee'
PUBLIC_API = f'{RIIGI_TEATAJA}/public-api/api/v1'
SEARCH_API = f'{RIIGI_TEATAJA}/api/oigusakt_otsing/1/otsi'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'
PAGE_SIZE = 200


class RiigiTeatajaClient(Client):
    """Finds and downloads the texts of Estonian acts from Riigi Teataja."""

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        retry = Retry(total=4, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=('GET',))
        self.session.mount('https://', HTTPAdapter(max_retries=retry))
        if proxies:
            self.session.proxies.update(proxies)

    def _get(self, url: str, **params: Any) -> requests.Response:
        try:
            response = self.session.get(url, params=params or None, timeout=60)
        except requests.RequestException as e:
            raise NetworkError(f"Riigi Teataja request failed for {url}: {e}") from e
        if response.status_code in (400, 404):
            raise FileLoadError(f"Riigi Teataja has no document at {url}")
        if response.status_code != 200:
            raise NetworkError(f"Riigi Teataja returned HTTP {response.status_code} for {url}")
        return response

    def act(self, global_id: str) -> dict[str, Any]:
        """Metadata of one text of an act: group id ('grupiId'), title, abbreviation, validity."""
        data = self._get(f'{PUBLIC_API}/akt/{global_id}').json()
        parameters = data.get('aktiParameetrid') or {}
        return {
            'global_id': str(data.get('kehtivId') or global_id),
            'group_id': data.get('grupiId'),
            'text_type': data.get('tekstiliik'),
            'title': parameters.get('pealkiri'),
            'abbreviation': parameters.get('lyhend'),
        }

    def search(self, **criteria: str) -> list[dict[str, Any]]:
        """Every text matching the search criteria (e.g. pealkiri=..., lyhend=...)."""
        texts: list[dict[str, Any]] = []
        page = 1
        while True:
            data = self._get(SEARCH_API, leht=page, limiit=PAGE_SIZE, **criteria).json()
            batch = data.get('aktid') or []
            texts.extend(batch)
            total = (data.get('metaandmed') or {}).get('kokku', 0)
            if not batch or len(texts) >= total:
                return texts
            page += 1

    def texts(self, group_id: int, title: Optional[str] = None,
              abbreviation: Optional[str] = None) -> list[dict[str, Any]]:
        """
        The texts of one act (its group), oldest first.

        Each has 'globaalID', 'tekst' ('algtekst', 'terviktekst' or both) and
        'kehtivus' ({'algus', 'lopp'}).
        """
        criteria = {'lyhend': abbreviation} if abbreviation else {'pealkiri': title or ''}
        texts = [t for t in self.search(**criteria) if t.get('terviktekstID') == group_id]
        return sorted(texts, key=lambda t: ((t.get('kehtivus') or {}).get('algus') or '', t['globaalID']))

    def download(self, global_id: str) -> str:
        """Download the XML of one text and return its path."""
        target = os.path.join(self.download_dir, 'EE', f'{global_id}.xml')
        if not os.path.exists(target):
            response = self._get(f'{PUBLIC_API}/akt/{global_id}/xml')
            if b'<oigusakt' not in response.content[:2000]:
                raise FileLoadError(f"Riigi Teataja returned no act XML for {global_id}")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as f:
                f.write(response.content)
        return target
