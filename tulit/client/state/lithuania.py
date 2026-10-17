"""
Client for Lithuanian legislation: the Register of Legal Acts on e-seimas.lrs.lt.

The Register of Legal Acts (Teisės aktų registras, TAR) is where Lithuanian
acts are officially published; the Seimas portal e-seimas.lrs.lt serves its
documents, each under a document id ('TAIS.29193' or a 32-character id):

- /portal/legalAct/lt/TAD/<id>: the act's card (type, dates, TAR
  identification code, publication);
- /rs/legalact/TAD/<id>/: the act's text as adopted;
- /portal/legalActEditions/lt/TAD/<id>: its consolidated versions
  (suvestinės redakcijos), each from a date, with the text at
  /rs/actualedition/<id>/<version>/.

An act is found by its TAR identification code ('2018-11733') or its
number ('XIII-1426') through the portal's detailed search, a JSF form.
"""
import os
import re
from typing import Any, Optional

import requests
from lxml import html
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError

ESEIMAS = 'https://e-seimas.lrs.lt'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'
LITHUANIAN = 'clsDHSLanguage.1'
SEARCH_FIELDS = {'registration': 'paramRegistrationNo', 'number': 'paramAdoptionNo'}
_FIELD_PREFIX = 'searchCompositeComponent:contentForm:searchParamPane:j_id_31:'
_DOCUMENT = re.compile(r'/portal/legalAct/lt/TAD/(?P<id>[0-9A-Za-z.]+?)(?:/(?P<version>[A-Za-z]{10}|asr))?(?:[?#]|$)')
LABELS = {'Rūšis': 'type', 'Priėmimo data': 'date_document', 'Registravimo duomenys': 'registration',
          'Dokumento Nr.': 'number', 'Paskelbta': 'publication', 'Priėmė': 'issuer'}


class EseimasClient(Client):
    """Finds and downloads Lithuanian acts and their consolidated versions from e-seimas.lrs.lt."""

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        retry = Retry(total=4, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=('GET', 'POST'))
        self.session.mount('https://', HTTPAdapter(max_retries=retry))
        if proxies:
            self.session.proxies.update(proxies)

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        try:
            response = self.session.request(method, url, timeout=240, **kwargs)
        except requests.RequestException as e:
            raise NetworkError(f"e-seimas request failed for {url}: {e}") from e
        if response.status_code == 404:
            raise FileLoadError(f"e-seimas has no document at {url}")
        if response.status_code != 200:
            raise NetworkError(f"e-seimas returned HTTP {response.status_code} for {url}")
        return response

    @staticmethod
    def _page(response: requests.Response):
        return html.fromstring(response.content.decode('utf-8', errors='replace'))

    def search(self, field: str, value: str) -> list[dict[str, Optional[str]]]:
        """
        Acts whose TAR identification code (``field='registration'``) or number (``'number'``) is ``value``.

        Each result gives the document ``id``, its ``title`` and, when it has one, the id of the act whose
        consolidated version is in force (``consolidated``).
        """
        page = self._page(self._request('GET', f'{ESEIMAS}/portal/legalActSearch/lt'))
        forms = page.xpath('//form[@id="searchCompositeComponent:contentForm"]')
        if not forms:
            raise NetworkError("The e-seimas search form has changed")
        form = forms[0]
        data: dict[str, str] = {}
        for field_input in form.xpath('.//input'):
            name, kind = field_input.get('name'), field_input.get('type') or 'text'
            if not name or kind in ('submit', 'button', 'image'):
                continue
            if kind in ('radio', 'checkbox'):
                if field_input.get('checked') is not None:
                    data[name] = field_input.get('value') or 'on'
                continue
            data[name] = field_input.get('value') or ''
        for select in form.xpath('.//select'):
            options = select.xpath('./option[@selected]') or select.xpath('./option')
            if select.get('name') and options:
                data[select.get('name')] = options[0].get('value') or ''
        data[_FIELD_PREFIX + SEARCH_FIELDS[field]] = value
        # Acts in Lithuanian, not their translations
        data[_FIELD_PREFIX + 'paramLanguage_input'] = LITHUANIAN
        data['searchCompositeComponent:contentForm:searchParamPane:searchButton'] = ''
        results = self._page(self._request('POST', ESEIMAS + form.get('action'), data=data))
        found: list[dict[str, Optional[str]]] = []
        for link in results.xpath('//a[contains(@href, "/portal/legalAct/lt/TAD/")]'):
            match = _DOCUMENT.search(link.get('href'))
            if not match:
                continue
            if match.group('version') == 'asr':
                if found and found[-1]['consolidated'] is None:
                    found[-1]['consolidated'] = match.group('id')
                continue
            found.append({'id': match.group('id'), 'title': ' '.join(link.text_content().split()),
                          'consolidated': None})
        return found

    def find(self, field: str, value: str) -> dict[str, Optional[str]]:
        """The act a TAR identification code or a number names."""
        found = self.search(field, value)
        if not found:
            raise FileLoadError(f"The Register of Legal Acts has no act {value}")
        return found[0]

    def _save(self, url: str, name: str) -> str:
        target = os.path.join(self.download_dir, 'LT', name)
        if os.path.exists(target):
            return target
        response = self._request('GET', url)
        if b'MsoNormal' not in response.content and b'<body' not in response.content:
            raise FileLoadError(f"e-seimas returned no text at {url}")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as f:
            f.write(response.content)
        return target

    def download(self, document: str) -> str:
        """Download the text of an act as adopted and return its path."""
        return self._save(f'{ESEIMAS}/rs/legalact/TAD/{document}/', f'{document}.html')

    def download_version(self, document: str, version: str) -> str:
        """Download a consolidated version of an act and return its path."""
        return self._save(f'{ESEIMAS}/rs/actualedition/{document}/{version}/', f'{document}_{version}.html')

    def versions(self, document: str) -> list[tuple[str, str]]:
        """The consolidated versions of an act: (date from which it applies, version id), oldest first."""
        page = self._page(self._request('GET', f'{ESEIMAS}/portal/legalActEditions/lt/TAD/{document}'))
        found = set()
        for link in page.xpath('//a[contains(@href, "/portal/legalAct/lt/TAD/")]'):
            match = _DOCUMENT.search(link.get('href'))
            date = re.search(r'(\d{4}-\d{2}-\d{2})', link.text_content())
            if match and match.group('version') and match.group('version') != 'asr' and date:
                found.add((date.group(1), match.group('version')))
        return sorted(found)

    def metadata(self, document: str) -> dict[str, Any]:
        """The act's card: type, issuer, adoption date, TAR code, number, publication and entry into force."""
        page = self._page(self._request('GET', f'{ESEIMAS}/portal/legalAct/lt/TAD/{document}'))
        cells = [' '.join(cell.text_content().split()) for cell in page.xpath('//td')]
        found: dict[str, Any] = {}
        for label, value in zip(cells, cells[1:]):
            key = LABELS.get(label.rstrip(':').strip())
            if key and key not in found and value:
                found[key] = re.sub(r'\s*\$\(function.*$', '', value).strip()
        registration = re.search(r'Nr\. (\d{4}-\d{5})', found.pop('registration', ''))
        if registration:
            found['tar'] = registration.group(1)
        text = ' '.join(page.text_content().split())
        in_force = re.search(r'Įsigalioja (\d{4}-\d{2}-\d{2})', text)
        if in_force:
            found['date_in_force'] = in_force.group(1)
        if 'publication' in found:
            found['publication'] = found['publication'].split('$(')[0].strip()
        return found
