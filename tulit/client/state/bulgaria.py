"""
Client for the State Gazette of the Republic of Bulgaria (Държавен вестник).

The National Assembly publishes the State Gazette on https://dv.parliament.bg.
Each act of its official section since 2003 is a 'material' with its own
page (DVWeb/showMaterialDV.jsp?idMat=<id>); the site's material search
(a JavaServer Faces form) finds materials by issue number, year and title.
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

DV = 'https://dv.parliament.bg/DVWeb'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'
_HEADER = re.compile(r'брой:\s*(?P<issue>\d+[а-я]?),\s*от дата\s*(?P<date>\d{1,2}\.\d{1,2}\.\d{4})(?:\s*г\.)?',
                     re.IGNORECASE)
_RESULT = re.compile(r'Брой\s+(?P<issue>\d+[а-я]?),\s*(?P<date>\d{1,2}\.\d{1,2}\.\d{4})\s*(?P<rest>.*?)\s*стр\.\s*\d+',
                     re.IGNORECASE)


def iso_date(text: str) -> Optional[str]:
    """'20.5.2016' -> '2016-05-20'."""
    match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', text or '')
    if not match:
        return None
    day, month, year = match.groups()
    return datetime.date(int(year), int(month), int(day)).isoformat()


class StateGazetteClient(Client):
    """Finds and downloads acts published in the Bulgarian State Gazette."""

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        retry = Retry(total=4, connect=4, read=4, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=('GET', 'POST'))
        self.session.mount('https://', HTTPAdapter(max_retries=retry))
        if proxies:
            self.session.proxies.update(proxies)

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        try:
            response = self.session.request(method, url, timeout=120, **kwargs)
        except requests.RequestException as e:
            raise NetworkError(f"State Gazette request failed for {url}: {e}") from e
        if response.status_code != 200:
            raise NetworkError(f"The State Gazette returned HTTP {response.status_code} for {url}")
        return response

    def download(self, material: str) -> str:
        """Download a material (idMat) and return its path."""
        target = os.path.join(self.download_dir, 'BG', f'{material}.html')
        if os.path.exists(target):
            return target
        response = self._request('GET', f'{DV}/showMaterialDV.jsp', params={'idMat': material})
        if b'tdHead1' not in response.content:
            raise FileLoadError(f"The State Gazette has no material {material}")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as f:
            f.write(response.content)
        return target

    @staticmethod
    def metadata(path: str) -> dict[str, Any]:
        """Issue, date, section and title of a downloaded material."""
        root = html.parse(path, html.HTMLParser(encoding='utf-8')).getroot()
        found: dict[str, Any] = {}
        title = root.xpath('//span[@class="tdHead1"]')
        if title:
            found['title'] = ' '.join(title[0].text_content().split())
        marks = [' '.join(span.text_content().split()) for span in root.xpath('//span[@class="mark"]')]
        header = next((mark for mark in marks if _HEADER.search(mark)), '')
        match = _HEADER.search(header)
        if match:
            found['issue'] = match.group('issue')
            found['date_publication'] = iso_date(match.group('date'))
            section = header[match.end():].strip(' \xa0')
            if section:
                found['section'] = section
        page = next((mark for mark in marks if re.fullmatch(r'стр\.\s*\d+', mark)), None)
        if page:
            found['page'] = page.replace('стр.', '').strip()
        return found

    def search(self, title: Optional[str] = None, issue: Optional[str] = None,
               year: Optional[int] = None) -> list[dict[str, Any]]:
        """
        Materials of the official section matching a title, issue number and year (the site's material search,
        which covers the issues since 2003). Returns their idMat, issue, date, issuer and title.
        """
        start = self._request('GET', f'{DV}/index.faces')
        tabs = html.fromstring(start.content.decode('utf-8', errors='replace')).xpath('//form[@id="_idJsp2"]')
        if not tabs:
            raise NetworkError("The State Gazette search page has changed")
        tabs = tabs[0]
        link = next((a.get('onclick') for a in tabs.xpath('.//a[@onclick]')
                     if "['active_tab','3']" in (a.get('onclick') or '')), None)
        if link is None:
            raise NetworkError("The State Gazette search page has changed")
        clicked = re.search(r"'(_idJsp2:[^']+)'", link).group(1)
        data = {'_idJsp2_SUBMIT': '1', '_idJsp2:_idcl': clicked, 'active_tab': '3',
                'javax.faces.ViewState': tabs.xpath('.//input[@name="javax.faces.ViewState"]/@value')[0]}
        page = self._request('POST', f'{DV}/index.faces', data=data)
        forms = html.fromstring(page.content.decode('utf-8', errors='replace')).xpath('//form[@id="search_form"]')
        if not forms:
            raise NetworkError("The State Gazette search form has changed")
        form = forms[0]
        fields: dict[str, str] = {}
        for field in form.xpath('.//input[@type="hidden" or @type="text"]'):
            fields[field.get('name')] = field.get('value') or ''
        for select in form.xpath('.//select'):
            fields[select.get('name')] = (select.xpath('./option[@selected]/@value') or [''])[0]
        # The text fields, in the order the form shows them: words, issue, issuer, place, title
        texts = [field.get('name') for field in form.xpath('.//input[@type="text"]')
                 if not field.get('name', '').endswith(('from_date', 'to_date'))]
        if len(texts) < 5:
            raise NetworkError("The State Gazette search form has changed")
        fields[texts[1]] = issue or ''
        fields[texts[4]] = title or ''
        if year:
            fields['search_form:from_date'] = f'01.01.{year}'
            fields['search_form:to_date'] = f'31.12.{year}'
        fields['search_form:btnFind.x'] = '5'
        fields['search_form:btnFind.y'] = '5'
        result = self._request('POST', f'{DV}/searchDV.faces', data=fields)
        root = html.fromstring(result.content.decode('utf-8', errors='replace'))
        found = []
        for anchor in root.xpath('//a[contains(@href, "idMat=")]'):
            material = re.search(r'idMat=(\d+)', anchor.get('href')).group(1)
            # The row describing the material encloses the table holding its link
            match = None
            for row in anchor.iterancestors('tr'):
                match = _RESULT.search(' '.join(' '.join(row.itertext()).split()))
                if match:
                    break
            if not match:
                continue
            found.append({'material': material, 'issue': match.group('issue'),
                          'date_publication': iso_date(match.group('date')), 'title': match.group('rest')})
        return found
