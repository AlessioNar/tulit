"""
Client for Latvian legislation: likumi.lv and Latvijas Vēstnesis.

Latvijas Vēstnesis, the official publisher, runs both sites, under the same
identifier for each act:

- vestnesis.lv (https://www.vestnesis.lv/ta/id/<id>) holds the official
  publication of the act as adopted;
- likumi.lv (https://likumi.lv/ta/id/<id>) holds the consolidated text
  (systematised versions, redakcijas); the version in force on a date is at
  /ta/id/<id>/redakcijas-datums/<YYYY>/<MM>/<DD>. Its 'Tiesību akta pase'
  gives the act's metadata (type, issuer, dates, publication).
"""
import datetime
import os
import re
from typing import Any, Optional

import requests
from lxml import html
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError

LIKUMI = 'https://likumi.lv/ta/id'
VESTNESIS = 'https://www.vestnesis.lv/ta/id'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'
_DATE = re.compile(r'(\d{2})\.(\d{2})\.(\d{4})')
FIELDS = {
    'Nosaukums': 'title', 'Izdevējs': 'issuer', 'Veids': 'type', 'Pieņemts': 'date_document',
    'Stājas spēkā': 'date_in_force', 'Zaudē spēku': 'date_no_longer_in_force', 'Publicēts': 'publication',
    'OP numurs': 'op_number',
}


def iso_date(text: Optional[str]) -> Optional[str]:
    """'05.07.2018.' -> '2018-07-05'."""
    match = _DATE.search(text or '')
    if not match:
        return None
    day, month, year = match.groups()
    return datetime.date(int(year), int(month), int(day)).isoformat()


class LikumiClient(Client):
    """Downloads Latvian acts from likumi.lv (consolidated) and vestnesis.lv (as published)."""

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
            raise NetworkError(f"Request failed for {url}: {e}") from e
        if response.status_code == 404:
            raise FileLoadError(f"No act at {url}")
        if response.status_code != 200:
            raise NetworkError(f"HTTP {response.status_code} for {url}")
        return response

    def _save(self, name: str, content: bytes) -> str:
        target = os.path.join(self.download_dir, 'LV', name)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as f:
            f.write(content)
        return target

    def download(self, act_id: str, date: Optional[str] = None) -> str:
        """Download an act from likumi.lv, as in force today or on a date (YYYY-MM-DD), and return its path."""
        name = f'{act_id}_{date}.html' if date else f'{act_id}.html'
        target = os.path.join(self.download_dir, 'LV', name)
        if os.path.exists(target):
            return target
        url = f'{LIKUMI}/{act_id}'
        if date:
            year, month, day = date.split('-')
            url = f'{url}/redakcijas-datums/{year}/{month}/{day}'
        response = self._get(url)
        if b'doc-body' not in response.content and b'neko-body' not in response.content:
            raise FileLoadError(f"likumi.lv has no text for act {act_id}")
        return self._save(name, response.content)

    def download_publication(self, act_id: str) -> str:
        """Download the official publication of an act in Latvijas Vēstnesis and return its path."""
        name = f'{act_id}_op.html'
        target = os.path.join(self.download_dir, 'LV', name)
        if os.path.exists(target):
            return target
        response = self._get(f'{VESTNESIS}/{act_id}')
        root = html.fromstring(response.content)
        content = root.xpath('//div[@class="docContent"]')
        # Unknown identifiers lead to the home page; early issues hold no text
        if not content or len(' '.join(content[0].itertext()).split()) < 20:
            raise FileLoadError(f"Latvijas Vēstnesis has no text for act {act_id}")
        return self._save(name, response.content)

    def versions(self, path: str) -> list[str]:
        """Dates (YYYY-MM-DD) of the versions an act's likumi.lv page links to (its amendments), oldest first."""
        root = html.parse(path).getroot()
        dates = {f'{y}-{m}-{d}' for href in root.xpath('//a/@href')
                 for y, m, d in re.findall(r'redakcijas-datums/(\d{4})/(\d{2})/(\d{2})', href)}
        return sorted(dates)

    @staticmethod
    def metadata(path: str) -> dict[str, Any]:
        """The 'Tiesību akta pase' of an act downloaded from likumi.lv: title, type, issuer, dates."""
        root = html.parse(path, html.HTMLParser(encoding='utf-8')).getroot()
        found: dict[str, Any] = {}
        for label in root.xpath('//div[contains(@class, "pase-container")]//font[contains(@class, "fclg2")]'):
            name = ' '.join((label.text_content() or '').split()).rstrip(':')
            key = FIELDS.get(name)
            if key is None:
                continue
            parent = label.getparent()
            value = ' '.join(parent.text_content().split())
            value = value[len(' '.join(label.text_content().split())):].strip()
            found[key] = value
        for key in ('date_document', 'date_in_force', 'date_no_longer_in_force'):
            if key in found:
                found[key] = iso_date(found[key])
        if 'publication' in found:
            found['date_publication'] = iso_date(found['publication'])
        return found
