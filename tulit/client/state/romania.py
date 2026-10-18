"""
Client for the Portal Legislativ of the Romanian Ministry of Justice (legislatie.just.ro).

The portal's free web service (SOAP) searches the legislation database by
number, year, title or text and returns each act with its metadata and its
text as published in Monitorul Oficial (official republications are records
of their own). Its address is plain HTTP; every search needs a token from
``GetToken``.

    http://legislatie.just.ro/apiws/FreeWebService.svc/SOAP

The consolidated forms of an act ("forma consolidată") are not in the web
service. The portal's page of an act, served over HTTPS only, shows its
latest form and lists all of them under "istoric consolidări", each with the
date it applies from and a page of its own:

    https://legislatie.just.ro/Public/DetaliiDocument/<id>

The pages answer only clients that present themselves as a browser, and not
every network reaches them (the web service is plain HTTP and is reachable
where the pages are not).
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
PAGE_HEADERS = {'User-Agent': f'Mozilla/5.0 (X11; Linux x86_64) {USER_AGENT}',
                'Accept': 'text/html,application/xhtml+xml', 'Accept-Language': 'ro-RO,ro;q=0.9'}
NS = 'http://schemas.datacontract.org/2004/07/FreeWebService'
SOAP = 'http://schemas.xmlsoap.org/soap/envelope/'
MONTHS = ('ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie', 'iulie', 'august', 'septembrie',
          'octombrie', 'noiembrie', 'decembrie')
_DATE = re.compile(r'(\d{1,2})\s+(%s)\s+(\d{4})' % '|'.join(MONTHS), re.IGNORECASE)
FIELDS = ('DataVigoare', 'Emitent', 'LinkHtml', 'Numar', 'Publicatie', 'TipAct', 'Titlu')
# An entry of the history of an act's forms: <a title='Consolidarea din 06.12.2024' ... href='.../291512'>
_FORM = re.compile(r"<a\s+title=['\"](?P<kind>Consolidarea|Republicarea) din (?P<day>\d{2})\.(?P<month>\d{2})\."
                   r"(?P<year>\d{4})['\"](?P<attributes>[^>]*)>")
_FORM_LINK = re.compile(r"href=['\"][^'\"]*?DetaliiDocument/(?P<id>\d+)(?P<query>\?[^'\"]*)?['\"]")
# The id of the form a page shows: <input type="hidden" id="id_act" name="id_act" value="304533" />
_SHOWN = re.compile(r"<input\b[^>]*\bid=['\"]id_act['\"][^>]*>")
_VALUE = re.compile(r"\bvalue=['\"](?P<id>\d+)['\"]")


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


def document_id(path: str) -> str:
    """The portal's id of a downloaded record ('.../DetaliiDocument/203151' -> '203151')."""
    link = etree.parse(path).getroot().findtext(f'{{{NS}}}LinkHtml') or ''
    match = re.search(r'DetaliiDocument/(\d+)', link)
    if not match:
        raise FileLoadError(f"{path} gives no Portal Legislativ document id")
    return match.group(1)


def act_forms(page: str) -> list[dict[str, Any]]:
    """
    The forms of an act its page lists, newest first: {'date', 'kind', 'id', 'url'}, with the
    date the form applies from and its kind, 'consolidation' or 'republication'.

    The form the page shows is listed without a link; its id is the page's own.
    """
    shown = shown_form(page)
    forms = []
    for match in _FORM.finditer(page):
        link = _FORM_LINK.search(match.group('attributes'))
        if link:
            form_id, query = link.group('id'), link.group('query') or ''
        elif shown:
            form_id, query = shown, ''
        else:
            continue
        forms.append({'date': f"{match.group('year')}-{match.group('month')}-{match.group('day')}",
                      'kind': 'consolidation' if match.group('kind') == 'Consolidarea' else 'republication',
                      'id': form_id, 'url': f'{PORTAL}/{form_id}{query}'})
    return forms


def shown_form(page: str) -> Optional[str]:
    """The id of the form a page shows."""
    match = _SHOWN.search(page)
    value = _VALUE.search(match.group(0)) if match else None
    return value.group('id') if value else None


class PortalLegislativClient(Client):
    """Searches and downloads Romanian acts through the Portal Legislativ web service and pages."""

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        retry = Retry(total=4, connect=4, read=4, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=('POST',))
        self.session.mount('http://', HTTPAdapter(max_retries=retry))
        self.session.mount('https://', HTTPAdapter(max_retries=Retry(
            total=3, connect=3, read=3, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504))))
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

    def find(self, kind: str, number: str, year: str, pages: int = 10, title: str = '') -> etree._Element:
        """
        The act of a type ('LEGE', 'HOTĂRÂRE', ...) with a number, adopted in a year, as published.

        An act without a number (the Constitution, the text of a code) has
        number '0' and is searched by words of its ``title``.
        """
        wanted = fold(kind)
        numbered = number != '0'
        # Titles write thousands with a dot: 'HOTĂRÂRE nr. 1.425 din 11 octombrie 2006'
        digits = r'\.?'.join(re.escape(digit) for digit in number)
        dated = (rf'\bnr\.\s*{digits}\s+din\s+[^\n]*?\b{year}\b' if numbered
                 else rf'\bdin\s+[^\n]*?\b{year}\b')
        for page in range(pages):
            acts = self.search(year=year, number=number if numbered else '', title=title, page=page)
            for act in acts:
                title_found = act.findtext(f'{{{NS}}}Titlu') or ''
                # Official republications are records of their own: the act is the one as published
                if fold(act.findtext(f'{{{NS}}}TipAct') or '') == wanted and re.search(dated, title_found) \
                        and not re.search(r'republicat', title_found, re.IGNORECASE):
                    return act
            if len(acts) < 10:
                break
        raise FileLoadError(f"Portal Legislativ has no {kind} nr. {number}/{year}")

    def download(self, kind: str, number: str, year: str, title: str = '') -> str:
        """Download an act and return the path of its record (metadata and text, as XML)."""
        ascii_kind = unicodedata.normalize('NFKD', fold(kind)).encode('ascii', 'ignore').decode()
        name = re.sub(r'\W+', '_', ascii_kind).lower()
        target = os.path.join(self.download_dir, 'RO', f'{name}_{number}_{year}.xml')
        if os.path.exists(target):
            return target
        act = self.find(kind, number, year, title=title)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as f:
            f.write(etree.tostring(act, xml_declaration=True, encoding='utf-8'))
        return target

    def download_page(self, url: str) -> str:
        """Download a page of the portal (an act in one of its forms) and return its path."""
        match = re.search(r'DetaliiDocument/(\d+)(\?isFormaDeBaza=True)?', url, re.IGNORECASE)
        if not match:
            raise ValueError(f"{url} is not the page of a document of the Portal Legislativ")
        name = f"{match.group(1)}{'_baza' if match.group(2) else ''}.html"
        target = os.path.join(self.download_dir, 'RO', 'pages', name)
        if os.path.exists(target):
            return target
        try:
            response = self.session.get(url, headers=PAGE_HEADERS, timeout=300)
        except requests.RequestException as e:
            raise NetworkError(f"Portal Legislativ page {url} could not be reached (the pages are served "
                               f"over HTTPS only and some networks do not reach them): {e}") from e
        if response.status_code == 404:
            raise FileLoadError(f"Portal Legislativ has no page {url}")
        if response.status_code != 200:
            raise NetworkError(f"Portal Legislativ returned HTTP {response.status_code} for {url}")
        # The pages are UTF-8, whatever the headers say
        if b'S_DEN' not in response.content:
            raise FileLoadError(f"Portal Legislativ page {url} holds no act text")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as f:
            f.write(response.content)
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
