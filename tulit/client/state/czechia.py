"""
Client for e-Sbírka, the electronic Collection of Laws of the Czech Republic.

Every act has metadata and a series of versions (znění), each addressed by
the date it applies from: '/sb/2019/110/2025-08-01'. Asking for a date
returns the version in force on that date. The text of a version is served
as fragments, page by page; the client saves the metadata and all the
fragments as one JSON document, which ``EsbirkaParser`` reads.

Since 2024 the consolidated versions in e-Sbírka are legally binding.
"""
import json
import os
from typing import Any
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError

ESBIRKA = 'https://e-sbirka.gov.cz'
API = f'{ESBIRKA}/sbr-cache/dokumenty-sbirky'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'


class EsbirkaClient(Client):
    """Downloads versions of Czech acts from e-Sbírka."""

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT, 'Accept': 'application/json'})
        retry = Retry(total=4, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=('GET',))
        self.session.mount('https://', HTTPAdapter(max_retries=retry))
        if proxies:
            self.session.proxies.update(proxies)

    def _get(self, url: str, **params: Any) -> dict[str, Any]:
        try:
            response = self.session.get(url, params=params or None, timeout=120)
        except requests.RequestException as e:
            raise NetworkError(f"e-Sbírka request failed for {url}: {e}") from e
        if response.status_code in (400, 404):
            raise FileLoadError(f"e-Sbírka has no document at {url}")
        if response.status_code != 200:
            raise NetworkError(f"e-Sbírka returned HTTP {response.status_code} for {url}")
        try:
            data = response.json()
        except ValueError as e:
            raise NetworkError(f"e-Sbírka returned no JSON for {url}") from e
        if not data.get('staleUrl') and 'seznam' not in data:
            raise FileLoadError(f"e-Sbírka has no version at {url}")
        return data

    def metadata(self, path: str) -> dict[str, Any]:
        """
        Metadata of an act or of one of its versions.

        '/sb/2019/110' gives the current version, '/sb/2019/110/2020-01-01' the
        version in force on that date; 'staleUrl' names the version returned.
        """
        return self._get(f"{API}/{quote(path, safe='')}")

    def download(self, version_path: str) -> str:
        """Download a version ('/sb/2019/110/2025-08-01') with its metadata as one JSON document."""
        target = os.path.join(self.download_dir, 'CZ', version_path.strip('/').replace('/', '_') + '.json')
        if os.path.exists(target):
            return target
        metadata = self.metadata(version_path)
        fragments: list[dict[str, Any]] = []
        page = 0
        while True:
            data = self._get(f"{API}/{quote(version_path, safe='')}/fragmenty", cisloStranky=page)
            fragments.extend(data.get('seznam') or [])
            page += 1
            if page >= int(data.get('pocetStranek') or 1):
                break
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'w', encoding='utf-8') as f:
            json.dump({'metadata': metadata, 'fragments': fragments}, f, ensure_ascii=False)
        return target
