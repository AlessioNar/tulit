"""
Client for the Portal Legislativ of the Romanian Ministry of Justice (legislatie.just.ro).

The portal's free web service (SOAP) searches the legislation database by
number, year, title or text and returns each act with its metadata and its
text as published in Monitorul Oficial. Its address is plain HTTP; the
portal's web pages, served over HTTPS, are not reachable from every network,
while the web service is.

    http://legislatie.just.ro/apiws/FreeWebService.svc/SOAP

Every search needs a token from ``GetToken``.
"""
import datetime
import os
import re
import unicodedata
from typing import Any, Optional

import requests
from lxml import etree
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError

SERVICE = 'http://legislatie.just.ro/apiws/FreeWebService.svc/SOAP'
PORTAL = 'https://legislatie.just.ro/Public/DetaliiDocument'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'
NS = 'http://schemas.datacontract.org/2004/07/FreeWebService'
SOAP = 'http://schemas.xmlsoap.org/soap/envelope/'
MONTHS = ('ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie', 'iulie', 'august', 'septembrie',
          'octombrie', 'noiembrie', 'decembrie')
_DATE = re.compile(r'(\d{1,2})\s+(%s)\s+(\d{4})' % '|'.join(MONTHS), re.IGNORECASE)
FIELDS = ('DataVigoare', 'Emitent', 'LinkHtml', 'Numar', 'Publicatie', 'TipAct', 'Titlu')


def iso_date(text: Optional[str]) -> Optional[str]:
    """'18 iulie 2018' -> '2018-07-18'."""
    match = _DATE.search(text or '')
    if not match:
        return None
    day, month, year = match.groups()
    return datetime.date(int(year), MONTHS.index(month.lower()) + 1, int(day)).isoformat()


def fold(text: str) -> str:
    """Upper case with the cedilla letters (Ş, Ţ) written as the comma-below ones (Ș, Ț)."""
    return ' '.join(text.upper().replace('Ş', 'Ș').replace('Ţ', 'Ț').split())


class PortalLegislativClient(Client):
    """Searches and downloads Romanian acts through the Portal Legislativ web service."""

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        retry = Retry(total=4, connect=4, read=4, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=('POST',))
        self.session.mount('http://', HTTPAdapter(max_retries=retry))
        if proxies:
            self.session.proxies.update(proxies)
        self._token: Optional[str] = None

    def _call(self, action: str, body: str) -> etree._Element:
        envelope = f'<s:Envelope xmlns:s="{SOAP}"><s:Body>{body}</s:Body></s:Envelope>'
        try:
            response = self.session.post(SERVICE, data=envelope.encode('utf-8'), timeout=180, headers={
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': f'"http://tempuri.org/IFreeWebService/{action}"'})
        except requests.RequestException as e:
            raise NetworkError(f"Portal Legislativ request failed: {e}") from e
        if response.status_code != 200:
            raise NetworkError(f"Portal Legislativ returned HTTP {response.status_code} for {action}")
        try:
            return etree.fromstring(response.content)
        except etree.XMLSyntaxError as e:
            raise NetworkError(f"Portal Legislativ returned an unreadable answer for {action}: {e}") from e

    def token(self) -> str:
        if self._token is None:
            root = self._call('GetToken', '<GetToken xmlns="http://tempuri.org/"/>')
            self._token = (root.findtext('.//{http://tempuri.org/}GetTokenResult') or '').strip()
            if not self._token:
                raise NetworkError("Portal Legislativ gave no token")
        return self._token

    def search(self, year: str = '', number: str = '', title: str = '', text: str = '',
               page: int = 0, size: int = 10) -> list[etree._Element]:
        """One page of acts matching a number, a year, words of the title or of the text."""
        def escape(value: str) -> str:
            return value.replace('&', '&amp;').replace('<', '&lt;')

        model = (f'<SearchModel xmlns:a="{NS}"><a:NumarPagina>{page}</a:NumarPagina>'
                 f'<a:RezultatePagina>{size}</a:RezultatePagina><a:SearchAn>{escape(year)}</a:SearchAn>'
                 f'<a:SearchNumar>{escape(number)}</a:SearchNumar><a:SearchText>{escape(text)}</a:SearchText>'
                 f'<a:SearchTitlu>{escape(title)}</a:SearchTitlu></SearchModel>')
        root = self._call('Search', f'<Search xmlns="http://tempuri.org/">{model}'
                                    f'<tokenKey>{self.token()}</tokenKey></Search>')
        return root.findall(f'.//{{{NS}}}Legi')

    def find(self, kind: str, number: str, year: str, pages: int = 10) -> etree._Element:
        """The act of a type ('LEGE', 'HOTĂRÂRE', ...) with a number, adopted in a year."""
        wanted = fold(kind)
        for page in range(pages):
            acts = self.search(year=year, number=number, page=page)
            for act in acts:
                title = act.findtext(f'{{{NS}}}Titlu') or ''
                if fold(act.findtext(f'{{{NS}}}TipAct') or '') == wanted and \
                        re.search(rf'\bnr\.\s*{re.escape(number)}\s+din\s+[^\n]*?\b{year}\b', title):
                    return act
            if len(acts) < 10:
                break
        raise FileLoadError(f"Portal Legislativ has no {kind} nr. {number}/{year}")

    def download(self, kind: str, number: str, year: str) -> str:
        """Download an act and return the path of its record (metadata and text, as XML)."""
        ascii_kind = unicodedata.normalize('NFKD', fold(kind)).encode('ascii', 'ignore').decode()
        name = re.sub(r'\W+', '_', ascii_kind).lower()
        target = os.path.join(self.download_dir, 'RO', f'{name}_{number}_{year}.xml')
        if os.path.exists(target):
            return target
        act = self.find(kind, number, year)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as f:
            f.write(etree.tostring(act, xml_declaration=True, encoding='utf-8'))
        return target

    @staticmethod
    def metadata(path: str) -> dict[str, Any]:
        """Type, issuer, title, dates and publication of a downloaded act."""
        root = etree.parse(path).getroot()
        values = {field: ' '.join((root.findtext(f'{{{NS}}}{field}') or '').split()) for field in FIELDS}
        title = values['Titlu']
        found: dict[str, Any] = {
            'type': values['TipAct'] or None,
            'issuer': values['Emitent'] or None,
            'title': re.split(r'\s+EMITENT\b', title)[0].strip() or None,
            'date_document': iso_date(re.split(r'\s+privind\s|\s+pentru\s', title)[0]),
            'date_in_force': values['DataVigoare'] or None,
            'source': values['LinkHtml'].replace('http://', 'https://') or None,
        }
        publication = re.search(r'Monitorul Oficial\s+nr\.\s*\S+\s+din\s+\d{1,2}\s+\w+\s+\d{4}', title, re.IGNORECASE)
        if publication:
            found['publication'] = publication.group(0)
            found['date_publication'] = iso_date(publication.group(0))
        return found
