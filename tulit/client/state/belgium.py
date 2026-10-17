"""
Client for Belgian legislation on eJustice: the Moniteur belge and Justel.

The Moniteur belge / Belgisch Staatsblad (FPS Justice) publishes acts as
adopted, in French and Dutch, and its Justel service publishes them as
amended. Both are addressed by ELI:

    https://www.ejustice.just.fgov.be/eli/<type>/<YYYY>/<MM>/<DD>/<numac>/<version>

where the type is constitution, loi, decret, ordonnance or arrete (in Dutch
grondwet, wet, decreet, ordonnantie, besluit), the date is the act's date,
the NUMAC its publication number, and the version 'moniteur' (Dutch
'staatsblad') for the publication or 'justel' for the consolidated text.

Justel keeps each earlier version of an act as a numbered archive; each
archive page lists them all with the date until which each was in force.
The server is slow and sometimes drops connections, and answers a valid
publication with HTTP 404: pages are judged by their content.
"""
import datetime
import os
import re
from typing import Any, Optional
from urllib.parse import urljoin

import requests
from lxml import html
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError

EJUSTICE = 'https://www.ejustice.just.fgov.be'
ELI = f'{EJUSTICE}/eli'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'
# Document types in French and Dutch
TYPES = {'constitution': 'grondwet', 'loi': 'wet', 'decret': 'decreet', 'ordonnance': 'ordonnantie',
         'arrete': 'besluit'}
PUBLICATION = {'fra': 'moniteur', 'nld': 'staatsblad'}
_ARCHIVE_ROW = re.compile(r"(\d{2}-\d{2}-\d{4})\s*(?:Voir texte ci-dessus|Zie tekst hier ?boven|"
                          r"Version archivée n°\s*(\d+)|Gearchiveerde versie nr\.?\s*(\d+))", re.IGNORECASE)
MONTHS = {
    'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4, 'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
    'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12,
    'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6, 'juli': 7, 'augustus': 8,
    'september': 9, 'oktober': 10, 'november': 11, 'december': 12,
}


def iso_date(text: Optional[str]) -> Optional[str]:
    """'05-09-2018' or '5 septembre 2018' -> '2018-09-05'."""
    if not text:
        return None
    match = re.search(r'(\d{2})-(\d{2})-(\d{4})', text)
    if match:
        day, month, year = match.groups()
        return datetime.date(int(year), int(month), int(day)).isoformat()
    match = re.search(r'(\d{1,2})(?:er)?\s+([a-zéû]+)\s+(\d{4})', text.lower())
    if match and match.group(2) in MONTHS:
        return datetime.date(int(match.group(3)), MONTHS[match.group(2)], int(match.group(1))).isoformat()
    return None


def _has_text(content: bytes) -> bool:
    return b'id="list-title-3"' in content or b'article-text' in content


class EJusticeClient(Client):
    """Downloads Belgian acts from the Moniteur belge and Justel."""

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        # The server drops connections now and then: retry them too
        retry = Retry(total=6, connect=6, read=6, backoff_factor=2,
                      status_forcelist=(429, 500, 502, 503, 504), allowed_methods=('GET',))
        self.session.mount('https://', HTTPAdapter(max_retries=retry))
        if proxies:
            self.session.proxies.update(proxies)

    def _get(self, url: str) -> bytes:
        try:
            response = self.session.get(url, timeout=180)
        except requests.RequestException as e:
            raise NetworkError(f"eJustice request failed for {url}: {e}") from e
        if response.status_code >= 500:
            raise NetworkError(f"eJustice returned HTTP {response.status_code} for {url}")
        if re.search(rb'(avant le 1 juin 1997|voor 1 juni 1997|v\xf3\xf3r 1 juni 1997)',
                     response.content):
            raise FileLoadError(f"eJustice publishes {url} only as PDF (texts published before June 1997)")
        # A publication comes with HTTP 404 too: what counts is whether the page holds a text
        if not _has_text(response.content):
            raise FileLoadError(f"eJustice has no text at {url}")
        return response.content

    def _save(self, name: str, content: bytes) -> str:
        target = os.path.join(self.download_dir, 'BE', name)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as f:
            f.write(content)
        return target

    @staticmethod
    def eli(doc_type: str, date: str, numac: str, language: str = 'fra', version: Optional[str] = None) -> str:
        """The ELI of an act ('loi', '2018-07-30', '2018040581') in a language, with a version if given."""
        year, month, day = date.split('-')
        name = TYPES[doc_type] if language == 'nld' else doc_type
        uri = f'{ELI}/{name}/{year}/{month}/{day}/{numac}'
        if version == 'justel':
            return f'{uri}/justel'
        if version:
            return f'{uri}/{PUBLICATION[language]}'
        return uri

    def download(self, doc_type: str, date: str, numac: str, language: str = 'fra',
                 consolidated: bool = False) -> str:
        """Download an act as published (or, with ``consolidated``, from Justel) and return its path."""
        version = 'justel' if consolidated else 'publication'
        target = os.path.join(self.download_dir, 'BE', f'{numac}_{language}_{version}.html')
        if os.path.exists(target):
            return target
        url = self.eli(doc_type, date, numac, language, 'justel' if consolidated else 'publication')
        return self._save(os.path.basename(target), self._get(url))

    def download_scan(self, doc_type: str, date: str, numac: str, language: str = 'fra') -> tuple[str, Optional[int]]:
        """
        Download the scanned issue of the Moniteur belge that published an act before June 1997.

        Returns the PDF's path and the page where the act starts.
        """
        url = self.eli(doc_type, date, numac, language, 'publication')
        try:
            page = self.session.get(url, timeout=180)
        except requests.RequestException as e:
            raise NetworkError(f"eJustice request failed for {url}: {e}") from e
        match = re.search(rb'href="(/mopdf/[^"#]+\.pdf)(?:#page=(\d+))?', page.content)
        if not match:
            raise FileLoadError(f"eJustice gives no scanned issue for {url}")
        target = os.path.join(self.download_dir, 'BE', f'{numac}_{language}_scan.pdf')
        if not os.path.exists(target):
            try:
                response = self.session.get(EJUSTICE + match.group(1).decode(), timeout=600)
            except requests.RequestException as e:
                raise NetworkError(f"eJustice request failed for {match.group(1).decode()}: {e}") from e
            if not response.content.startswith(b'%PDF'):
                raise FileLoadError(f"eJustice did not return a PDF for {match.group(1).decode()}")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as f:
                f.write(response.content)
        self.scan_url = EJUSTICE + match.group(1).decode()
        return target, int(match.group(2)) if match.group(2) else None

    @staticmethod
    def archive_link(path: str) -> Optional[tuple[int, str]]:
        """The number and link of the latest archive named on a Justel page, if any."""
        root = html.parse(path).getroot()
        for href in root.xpath('//div[@id="list-title-1"]//a/@href'):
            match = re.search(r'[?&]arch=(\d+)', href)
            if match:
                return int(match.group(1)), urljoin(f'{EJUSTICE}/cgi_loi/', href)
        return None

    def download_archive(self, link: str, numac: str, language: str, number: int) -> str:
        """Download archive ``number`` of an act, given the link of any of its archives, and return its path."""
        target = os.path.join(self.download_dir, 'BE', f'{numac}_{language}_justel_{number:03d}.html')
        if os.path.exists(target):
            return target
        url = re.sub(r'([?&]arch=)\d+', lambda m: f'{m.group(1)}{number:03d}', link)
        return self._save(os.path.basename(target), self._get(url))

    @staticmethod
    def archives(path: str) -> list[tuple[int, str]]:
        """
        The archives listed on a Justel archive page: (number, date until which it was in force), oldest first.
        """
        root = html.parse(path).getroot()
        # The box shares its id with the report to the King, where there is one
        boxes = root.xpath('//div[@id="list-title-sw_roi"]')
        own = re.search(r'[?&]arch=(\d+)', ' '.join(root.xpath('//div[@id="list-title-1"]//a/@href')))
        text = ' '.join(' '.join(box.text_content().split()) for box in boxes)
        found = []
        for until, *numbers in _ARCHIVE_ROW.findall(text):
            number = next((n for n in numbers if n), None)
            if number is None and own:
                # 'Voir texte ci-dessus': the archive shown on this page, one after the one it links to
                number = str(int(own.group(1)) + 1)
            if number:
                found.append((int(number), iso_date(until)))
        return sorted(found)

    @staticmethod
    def article_count(path: str) -> int:
        """The number of articles in a Justel text (early archives of old acts hold only those they changed)."""
        root = html.parse(path).getroot()
        return len(root.xpath('//div[@id="list-title-3"]//a[starts-with(@name, "Art")]'))

    @staticmethod
    def metadata(path: str) -> dict[str, Any]:
        """Title, issuer, publication and entry into force, and the acts it amends, from a Justel page."""
        root = html.parse(path).getroot()
        box = root.xpath('//div[@id="list-title-1"]')
        if not box:
            return {}
        found: dict[str, Any] = {}
        title = box[0].xpath('.//p[contains(@class, "list-item--title")]')
        if title:
            found['title'] = re.sub(r'\s*\((NOTE|NOTA)\s*:.*$', '', ' '.join(title[0].text_content().split()))
        for paragraph in box[0].xpath('.//p[strong]'):
            label = ' '.join(paragraph.xpath('string(strong)').split()).rstrip(' :')
            value = ' '.join(paragraph.text_content().split())[len(label):].lstrip(' :')
            if label in ('Source', 'Bron'):
                found['issuer'] = value
            elif label in ('Publication', 'Publicatie'):
                found['date_publication'] = iso_date(value)
            elif label in ('Entrée en vigueur', 'Inwerkingtreding'):
                found['date_in_force'] = iso_date(value)
        found['amends'] = [a.text_content().strip() for a in box[0].xpath('.//span[@class="tag-small"]/a')]
        return found
