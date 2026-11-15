"""
Client for the Official Gazette of the Republic of Cyprus (Επίσημη Εφημερίδα).

The Government Printing Office (Ministry of Finance) publishes each issue of
the Gazette as PDF on https://www.mof.gov.cy/mof/gpo/gazette.nsf; laws appear
in Annex One (Παράρτημα Πρώτο): Part I for general laws, Part II for budgets
and Part III for laws ratifying treaties. The site's full-text search covers
the PDFs, so a law is found by its number ('Αριθμός 125(Ι) του 2018').

Issues before about 2015 are scanned images without text, out of reach of
the search; the archive lists every issue from 2004 by year and month, so
those are found by their issue number ('Αρ. 4252', 23 July 2010) instead.
"""
import datetime
import os
import re
import urllib.parse
from typing import Any, Optional

import requests
from lxml import html
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError

GAZETTE = 'https://www.mof.gov.cy/mof/gpo/gazette.nsf'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'
_PDF = re.compile(rb'href="(?:\.\./)?(?P<path>[0-9A-F]{32}/\$file/[^"]+\.pdf)"', re.IGNORECASE)
_DETAILS = re.compile(r'Αριθμός Εφημερίδας:\s*(?P<issue>\w+)\s*Σελίδες:\s*(?P<pages>[\d\-–]+)\s*'
                      r'Ημερομηνία:\s*(?P<date>\d{2}/\d{2}/\d{4})')
_ARCHIVE_ROW = re.compile(r'(?P<date>\d{2}/\d{2}/\d{4}) - (?P<label>.*?) ?- Αρ\. (?P<issue>\w+)\b')
# Annex One part where each kind of law appears: I general, II budgets, III ratifications
PARTS = {'I': 'ΜΕΡΟΣ (Ι)', 'II': 'ΜΕΡΟΣ (ΙΙ)', 'III': 'ΜΕΡΟΣ (ΙΙΙ)'}


class CyprusGazetteClient(Client):
    """Finds and downloads laws in the Official Gazette of the Republic of Cyprus."""

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

    def _get(self, url: str) -> requests.Response:
        try:
            response = self.session.get(url, timeout=180)
        except requests.RequestException as e:
            raise NetworkError(f"Official Gazette request failed for {url}: {e}") from e
        if response.status_code == 404:
            raise FileLoadError(f"The Official Gazette has nothing at {url}")
        if response.status_code != 200:
            raise NetworkError(f"The Official Gazette returned HTTP {response.status_code} for {url}")
        return response

    def search(self, phrase: str) -> list[tuple[str, str]]:
        """Issues whose text holds an exact phrase: (link of the issue page, its description)."""
        query = urllib.parse.quote(f'"{phrase}"')
        response = self._get(f'{GAZETTE}/SearchResults-el/SearchResults-el?OpenForm&q=&p=1&w=&t=&s={query}'
                             f'&L=G&e=&i=1')
        root = html.fromstring(response.content.decode('utf-8', errors='replace'))
        return [(urllib.parse.urljoin(f'{GAZETTE}/SearchResults-el/', a.get('href')),
                 ' '.join(a.text_content().split())) for a in root.xpath('//a[contains(@href, "All/")]')]

    def find_law(self, number: str, part: str, year: str) -> str:
        """The issue page of law ``number``(``part``) of ``year`` ('125', 'I', '2018')."""
        greek = part.replace('I', 'Ι')
        hits = self.search(f'Αριθμός {number}({greek}) του {year}')
        section = PARTS.get(part, PARTS['I'])
        issue = next((link for link, title in hits if 'ΠΑΡΑΡΤΗΜΑ ΠΡΩΤΟ' in title and section in title), None)
        issue = issue or next((link for link, title in hits if 'ΠΑΡΑΡΤΗΜΑ ΠΡΩΤΟ' in title), None)
        if issue is None:
            raise FileLoadError(f"The Official Gazette has no law {number}({part})/{year}, or its search does not "
                                f"reach it (it covers issues from about 2015)")
        return issue

    def issue(self, link: str) -> dict[str, Any]:
        """The PDF link and the details (number, pages, date) of a Gazette issue page."""
        response = self._get(link.split('&highlight=')[0])
        match = _PDF.search(response.content)
        if not match:
            raise FileLoadError(f"The Official Gazette issue at {link} has no PDF")
        path = match.group('path').decode('utf-8')
        text = ' '.join(html.fromstring(response.content.decode('utf-8', errors='replace')).text_content().split())
        details = _DETAILS.search(text)
        found: dict[str, Any] = {'pdf': f"{GAZETTE}/All/{urllib.parse.quote(path, safe='/$')}"}
        if details:
            day, month, year = details.group('date').split('/')
            found.update(issue=details.group('issue'), pages=details.group('pages'),
                         date_publication=datetime.date(int(year), int(month), int(day)).isoformat())
        return found

    def download(self, number: str, part: str, year: str) -> tuple[str, dict[str, Any]]:
        """Download the Gazette issue holding a law; returns its path and the issue's details."""
        return self.download_issue(self.find_law(number, part, year))

    def archive_years(self) -> dict[int, str]:
        """The archive's years and the view position that expands each."""
        response = self._get(f'{GAZETTE}/dmlgazette_archive_gr/dmlgazette_archive_gr?OpenForm')
        root = html.fromstring(response.content.decode('utf-8', errors='replace'))
        years: dict[int, str] = {}
        for row in root.xpath('//tr'):
            text = ' '.join(row.text_content().split())
            link = next((href for href in row.xpath('.//a/@href') if 'Expand=' in href), None)
            if re.fullmatch(r'\d{4}', text) and link:
                years.setdefault(int(text), re.search(r'Expand=([\d.]+)', link).group(1))
        return years

    def find_issue(self, issue: str, year: int, month: Optional[int] = None) -> str:
        """The page of Annex One issue ``issue`` of ``year`` (in ``month``, when known), from the archive."""
        position = self.archive_years().get(year)
        if position is None:
            raise FileLoadError(f"The Official Gazette archive has no year {year}")
        for number in ([month] if month else range(1, 13)):
            # Each month lists its main part (.1) and its annexes (.2)
            response = self._get(f'{GAZETTE}/dmlgazette_archive_gr/dmlgazette_archive_gr?OpenForm&Start=1'
                                 f'&Count=9999&Expand={position}.{number}.2&Seq=4')
            root = html.fromstring(response.content.decode('utf-8', errors='replace'))
            for row in root.xpath('//tr'):
                match = _ARCHIVE_ROW.search(' '.join(row.text_content().split()))
                links = [href for href in row.xpath('.//a/@href') if '/All/' in href]
                if match and links and match.group('issue') == issue and (
                        not match.group('label').strip(' -') or 'ΠΑΡΑΡΤΗΜΑ ΠΡΩΤΟ' in match.group('label')):
                    return urllib.parse.urljoin(GAZETTE + '/', links[0])
        raise FileLoadError(f"The Official Gazette archive has no Annex One issue {issue} in {year}")

    def download_issue(self, link: str) -> tuple[str, dict[str, Any]]:
        """Download the PDF of a Gazette issue page; returns its path and the issue's details."""
        details = self.issue(link)
        name = f"{details.get('issue') or re.search(r'All/([0-9A-F]+)', link).group(1)}.pdf"
        target = os.path.join(self.download_dir, 'CY', name)
        if not os.path.exists(target):
            response = self._get(details['pdf'])
            if not response.content.startswith(b'%PDF'):
                raise FileLoadError(f"The Official Gazette did not return a PDF for {details['pdf']}")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as f:
                f.write(response.content)
        return target, details
