"""
Client for the German Federal Law Gazette (Bundesgesetzblatt, BGBl.): acts as promulgated.

Since 1 January 2023 the Gazette is promulgated electronically on the
Verkündungsplattform of the Federal Ministry of Justice,
https://www.recht.bund.de. Each promulgation has an ELI permalink
('https://www.recht.bund.de/eli/bund/bgbl-1/2024/149' for BGBl. 2024 I
Nr. 149) whose page gives the title, the dates and the authentic PDF of the
text ('regelungstext.pdf'), followed by any annexes published apart
('anlage1.pdf', ...). The platform publishes no XML of promulgations.

The issues of 1949 to 2022, printed on paper, are kept in the archive at
https://www.bgbl.de, run by the Bundesanzeiger Verlag, to which
recht.bund.de refers for them. Each act there is a PDF named after the
Gazette part, year and first page ('bgbl117s2097.pdf' for BGBl. I 2017
S. 2097); acts starting on the same page take a letter ('bgbl251s0151b.pdf').
The archive's viewer opens a session ('start.xav'), finds a document by its
name ('text.xav') and serves its PDF ('media.xav').
"""
import datetime
import html
import os
import re
import urllib.parse
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError

RECHT = 'https://www.recht.bund.de'
ARCHIVE = 'https://www.bgbl.de/xaver/bgbl/'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'

_PDF_LINK = re.compile(r'href="(?:https://www\.recht\.bund\.de)?(/bgbl/\d/\d{4}/[\w-]+/(\w+)\.pdf)'
                       r'\?__blob=publicationFile[^"]*"', re.IGNORECASE)
_FIELD = re.compile(r'<strong>\s*([^<:]+?):?\s*</strong>\s*<span>\s*([^<]*?)\s*</span>')
_PDF_FILE = re.compile(r'pdffile="([^"]+)"', re.IGNORECASE)


def german_date(text: Optional[str]) -> Optional[str]:
    """'13.05.2024' -> '2024-05-13'."""
    match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', text or '')
    if not match:
        return None
    day, month, year = (int(group) for group in match.groups())
    try:
        return datetime.date(year, month, day).isoformat()
    except ValueError:
        return None


def promulgation_url(part: str, year: str, number: str) -> str:
    """ELI permalink of a promulgation on recht.bund.de: part '1' or '2', year and number ('149', '1a')."""
    return f'{RECHT}/eli/bund/bgbl-{part}/{year}/{number}'


def archive_name(part: str, year: str, page: str) -> str:
    """Name of an act in the bgbl.de archive: ('1', '2017', '2097') -> 'bgbl117s2097.pdf'."""
    return f'bgbl{part}{year[2:]}s{page}.pdf'


def archive_url(name: str) -> str:
    """Link opening an act of the bgbl.de archive in its viewer."""
    return f'{ARCHIVE}start.xav?startbk=Bundesanzeiger_BGBl&jumpTo={name}'


class BundesgesetzblattClient(Client):
    """Finds and downloads acts of the Federal Law Gazette as promulgated."""

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        retry = Retry(total=4, connect=4, read=4, backoff_factor=1,
                      status_forcelist=(429, 500, 502, 503, 504), allowed_methods=('GET',))
        self.session.mount('https://', HTTPAdapter(max_retries=retry))
        if proxies:
            self.session.proxies.update(proxies)
        self._archive: Optional[dict[str, str]] = None

    def _get(self, url: str, **kwargs: Any) -> requests.Response:
        try:
            return self.session.get(url, timeout=kwargs.pop('timeout', 120), **kwargs)
        except requests.RequestException as e:
            raise NetworkError(f"Federal Law Gazette request failed for {url}: {e}") from e

    def _save(self, content: bytes, name: str) -> str:
        target = os.path.join(self.download_dir, 'DE', 'bgbl', name)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as f:
            f.write(content)
        return target

    # ===== recht.bund.de (2023-) =====

    def promulgation(self, part: str, year: str, number: str) -> dict[str, Any]:
        """
        A promulgation on recht.bund.de: its title, citation, type, dates and
        the paths of its PDFs ('pdfs': the text first, then any annexes).
        """
        url = promulgation_url(part, year, number)
        response = self._get(url)
        if response.status_code == 404:
            raise FileLoadError(f"recht.bund.de has no promulgation BGBl. {year} {'I' * int(part)} Nr. {number}")
        if response.status_code != 200:
            raise NetworkError(f"recht.bund.de returned HTTP {response.status_code} for {url}")
        page = response.text
        fields = {html.unescape(label).strip(): ' '.join(html.unescape(value).split())
                  for label, value in _FIELD.findall(page)}
        title = re.search(r'<h1 id="introH">\s*<span>(.*?)</span>', page, re.S)
        citation = re.search(r'<h2 class="h3">\s*(BGBl\.[^<]*?)\s+vom\s', page)
        pdfs: list[tuple[str, str]] = []
        for path, name in _PDF_LINK.findall(page):
            if name.lower() not in {n.lower() for _, n in pdfs}:
                pdfs.append((path, name))
        # The text first, then the annexes in their order
        pdfs.sort(key=lambda item: (not item[1].lower().startswith('regelungstext'),
                                    int(re.sub(r'\D', '', item[1]) or 0)))
        if not pdfs:
            raise FileLoadError(f"recht.bund.de lists no PDF for {url}")
        return {
            'url': url,
            'title': ' '.join(html.unescape(title.group(1)).split()) if title else None,
            'citation': citation.group(1) if citation else None,
            'type': fields.get('Typ'),
            'date_publication': german_date(fields.get('Veröffentlichungsdatum')),
            'date_document': german_date(fields.get('Ausfertigungsdatum')),
            'pdf_urls': [f'{RECHT}{path}?__blob=publicationFile' for path, _ in pdfs],
        }

    def download_promulgation(self, promulgation: dict[str, Any], part: str, year: str,
                              number: str) -> list[str]:
        """Download the PDFs of a promulgation (the text, then any annexes); returns their paths."""
        paths = []
        for url in promulgation['pdf_urls']:
            name = url.split('?')[0].rsplit('/', 1)[-1].lower()
            target = os.path.join(self.download_dir, 'DE', 'bgbl', f'bgbl{part}_{year}_{number}_{name}')
            if not os.path.exists(target):
                response = self._get(url, timeout=300)
                if response.status_code != 200 or not response.content.startswith(b'%PDF'):
                    raise FileLoadError(f"recht.bund.de did not return a PDF for {url}")
                self._save(response.content, os.path.basename(target))
            paths.append(target)
        return paths

    # ===== bgbl.de archive (1949-2022) =====

    def _archive_session(self) -> dict[str, str]:
        if self._archive is None:
            self._get(f'{ARCHIVE}start.xav?startbk=Bundesanzeiger_BGBl')
            response = self._get(f'{ARCHIVE}start.xav', params={'nocomm': 'final', 'SID': '', 'startbk': 'bgbl',
                                                                'bk': 'bgbl', 'start': ''})
            try:
                data = response.json()
            except ValueError as e:
                raise NetworkError("The bgbl.de archive did not open a session") from e
            self._archive = {'sid': data.get('sid') or '', 'csrf': data.get('csrftoken') or ''}
        return self._archive

    def archive_document(self, name: str) -> Optional[dict[str, Any]]:
        """
        An act of the bgbl.de archive by its name ('bgbl117s2097.pdf'): the
        path of its PDF in the archive, its title and the issue it appeared in
        ('Nr. 44 vom 05.07.2017'); None when the archive has no such document.
        """
        session = self._archive_session()
        response = self._get(f'{ARCHIVE}text.xav', params={
            'SID': session['sid'], 'tf': 'xaver.component.Text_0', 'tocf': '', 'qmf': '',
            'hlf': 'xaver.component.Hitlist_0', 'bk': 'bgbl', 'start': f"//*[@attr_id='{name}']"})
        try:
            data = response.json()
        except ValueError as e:
            raise NetworkError(f"The bgbl.de archive returned no document data for {name}") from e
        found = _PDF_FILE.search(data.get('innerhtml') or '')
        if not found or not found.group(1).endswith(name):
            return None
        path = found.group(1)
        trail = [urllib.parse.unquote(item.get('txt') or '') for item in data.get('topub') or []]
        issue = next((t for t in trail if re.match(r'Nr\.\s*\d+', t)), None)
        return {
            'path': path,
            'title': ' '.join(trail[-1].split()) if trail else None,
            'issue': issue,
            'date_publication': german_date(issue),
        }

    def download_archive(self, document: dict[str, Any]) -> str:
        """Download the PDF of an act found with ``archive_document``."""
        path = document['path']
        target = os.path.join(self.download_dir, 'DE', 'bgbl', path.rsplit('/', 1)[-1])
        if os.path.exists(target):
            return target
        session = self._archive_session()
        quoted = urllib.parse.quote(path, safe='')
        url = (f"{ARCHIVE}media.xav/{urllib.parse.quote(path.replace('/', '_'), safe='')}"
               f"?SID={urllib.parse.quote(session['sid'])}&name={quoted}&medianame={quoted}"
               f"&bk=bgbl&_csrf={urllib.parse.quote(session['csrf'])}")
        response = self._get(url, timeout=300)
        if response.status_code != 200 or not response.content.startswith(b'%PDF'):
            raise FileLoadError(f"The bgbl.de archive did not return the PDF of {path}")
        return self._save(response.content, os.path.basename(target))
