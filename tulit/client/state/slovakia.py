"""
Client for Slov-Lex, the Slovak legal information portal (Ministry of Justice).

Every act of the Collection of Laws (Zbierka zákonov) is published as
MetaLex XML at predictable static URLs, both as promulgated
(``vyhlasene_znenie.xml``) and for every consolidated version, named by the
date it applies from (``YYYYMMDD.xml``). The act's static index page lists
the versions.
"""
import os
import re
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError

STATIC = 'https://static.slov-lex.sk/static'
PORTAL = 'https://www.slov-lex.sk/ezbierky/pravne-predpisy'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'
ORIGINAL_FILE = 'vyhlasene_znenie'

_CITATION = re.compile(r'^(\d+)\s*/\s*(\d{4})(\s*(Z\.\s*z\.|Zb\.))?$')
_PATH = re.compile(r'^(?:SK/ZZ/)?(\d{4})/(\d+)$')


def act_path(identifier: str) -> str:
    """
    The Slov-Lex path of an act.

    '18/2018', '18/2018 Z. z.', '2018/18' and 'SK/ZZ/2018/18' -> 'SK/ZZ/2018/18'.
    """
    text = identifier.strip().strip('/')
    match = _CITATION.match(text)
    if match:
        return f'SK/ZZ/{match.group(2)}/{match.group(1)}'
    match = _PATH.match(text)
    if match:
        return f'SK/ZZ/{match.group(1)}/{match.group(2)}'
    raise ValueError(
        f"'{identifier}' is not a Slovak act identifier; use the citation number/year, "
        "e.g. '18/2018' or '460/1992'"
    )


class SlovLexClient(Client):
    """Downloads Slovak legislation as MetaLex XML from Slov-Lex."""

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        retry = Retry(total=4, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=('GET',))
        self.session.mount('https://', HTTPAdapter(max_retries=retry))
        if proxies:
            self.session.proxies.update(proxies)

    def versions(self, identifier: str) -> list[str]:
        """ISO dates of the consolidated versions of an act, oldest first."""
        path = act_path(identifier)
        html = self._get(f'{STATIC}/{path}/').text
        stamps = sorted(set(re.findall(r'href="(\d{8})\.html"', html)))
        return [f'{s[:4]}-{s[4:6]}-{s[6:]}' for s in stamps]

    def version_on(self, identifier: str, date: str) -> Optional[str]:
        """The date of the version in force on ``date`` (the latest applying on or before it)."""
        applicable = [v for v in self.versions(identifier) if v <= date]
        return applicable[-1] if applicable else None

    def download(self, identifier: str, version: Optional[str] = None) -> str:
        """
        Download an act as promulgated (``version=None``) or a consolidated
        version (its ISO date); returns the file path.
        """
        path = act_path(identifier)
        name = ORIGINAL_FILE if version is None else version.replace('-', '')
        target = os.path.join(self.download_dir, *path.split('/'), f'{name}.xml')
        if not os.path.exists(target):
            content = self._get(f'{STATIC}/xml/{path}/{name}.xml').content
            if b'metalex' not in content[:2000]:
                raise FileLoadError(f"Slov-Lex has no XML for {path} ({name})")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as f:
                f.write(content)
        return target

    def _get(self, url: str) -> requests.Response:
        try:
            response = self.session.get(url, timeout=60)
            if response.status_code == 404:
                raise FileLoadError(f"Not found on Slov-Lex: {url}")
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            raise NetworkError(f"Slov-Lex request failed for {url}: {e}") from e
