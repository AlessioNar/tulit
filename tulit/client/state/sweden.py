"""
Client for the Riksdag open data (data.riksdagen.se), Swedish statutes (SFS).

The Riksdag republishes the Government Offices' consolidated text of every
statute in the Swedish Code of Statutes (Svensk författningssamling), as in
force now, with its metadata.

API documentation: https://data.riksdagen.se
"""
import os
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError

RIKSDAGEN = 'https://data.riksdagen.se'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'


class RiksdagenClient(Client):
    """Downloads consolidated Swedish statutes from the Riksdag open data."""

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
