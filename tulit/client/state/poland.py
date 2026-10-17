"""
Client for the Sejm ELI API (api.sejm.gov.pl), the Polish Journal of Laws.

Every act published in the Dziennik Ustaw (DU) or Monitor Polski (MP) has
JSON metadata and, for most acts, its text as HTML. Official consolidated
texts (teksty jednolite) are separate acts, announcements of the Marshal of
the Sejm, listed in the metadata of the act they consolidate.

API documentation: https://api.sejm.gov.pl/eli.html
"""
import os
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError

ELI_API = 'https://api.sejm.gov.pl/eli/acts'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'


class SejmELIClient(Client):
    """Downloads Polish acts and their metadata from the Sejm ELI API."""

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
            raise NetworkError(f"Sejm ELI API request failed for {url}: {e}") from e
        if response.status_code == 404:
            raise FileLoadError(f"The Sejm ELI API has no act at {url}")
        if response.status_code != 200:
            raise NetworkError(f"The Sejm ELI API returned HTTP {response.status_code} for {url}")
        return response

    def act(self, eli: str) -> dict[str, Any]:
        """Metadata of an act, e.g. 'DU/2018/1000'."""
        return self._get(f'{ELI_API}/{eli}').json()

    def download_text(self, eli: str) -> str:
        """Download the HTML text of an act and return its path."""
        target = os.path.join(self.download_dir, 'PL', eli.replace('/', '_') + '.html')
        if not os.path.exists(target):
            response = self._get(f'{ELI_API}/{eli}/text.html')
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as f:
                f.write(response.content)
        return target
