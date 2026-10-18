"""
Clients for the Diário da República Eletrónico (diariodarepublica.pt, data.dre.pt).

``PortugalDREClient`` downloads acts as published, by their ELI, as the PDF of
the gazette. ``PortugalConsolidatedClient`` reads the consolidated legislation
(Legislação Consolidada) through the JSON screen services the site's
OutSystems pages call.
"""
import datetime
import json
import logging
import os
import re
from typing import Any, Optional
from urllib.parse import unquote

import requests

from tulit.client.client import Client
from tulit.parser.exceptions import ContentTypeError, FileLoadError, NetworkError


class PortugalDREClient(Client):
    """
    Client for retrieving legal documents from the Portuguese DRE ELI portal.
    See: http://data.dre.pt/eli/
    """
    BASE_URL = "http://data.dre.pt/eli"

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        if proxies:
            self.session.proxies.update(proxies)
        self.logger = logging.getLogger(self.__class__.__name__)

    def download(self, document_type, series=None, number=None, year=None, supplement=0, act_type=None,
                 month=None, day=None, region=None, cons_date=None, lang='pt', fmt='pdf'):
        """
        Download documents from the Portuguese DRE ELI portal.

        Parameters
        ----------
        document_type : str
            Type of document: 'journal', 'legal_act', or 'consolidated'
        series : str, optional
            For journals: series ('1', '1a', '1b', etc.)
        number : str, optional
            Document number in the year
        year : str, optional
            Year of publication
        supplement : int, optional
            For journals: supplement number (default 0)
        act_type : str, optional
            For legal acts: type ('lei', 'dec-lei', 'declegreg', etc.)
        month : str, optional
            For legal acts: month of publication
        day : str, optional
            For legal acts: day of publication
        region : str, optional
            For legal acts: region ('p', 'm', 'a')
        cons_date : str, optional
            For consolidated acts: consolidation date as 'yyyymmdd'
        lang : str, optional
            Language (default 'pt')
        fmt : str, optional
            Format: 'pdf' (default) or 'html'. The site now renders HTML with
            JavaScript, so HTML requests fail with ContentTypeError; PDF works.

        Returns
        -------
        str or None
            Path to downloaded file or None if failed
        """
        if document_type == 'journal':
            if not all([series, number, year]):
                raise ValueError("Journal downloads require series, number, and year")
            url = f"{self.BASE_URL}/diario/{series}/{number}/{year}/{supplement}/{lang}/{fmt}"
            filename = f"dre_journal_{series}_{number}_{year}_{supplement}_{lang}.{fmt}"
            self.logger.info(f"Requesting journal: series={series}, number={number}, year={year}, "
                             f"supplement={supplement}, lang={lang}, fmt={fmt}")

        elif document_type == 'legal_act':
            if not all([act_type, number, year, month, day, region]):
                raise ValueError("Legal act downloads require act_type, number, year, month, day, and region")
            url = f"{self.BASE_URL}/{act_type}/{number}/{year}/{month}/{day}/{region}/dre/{lang}/{fmt}"
            filename = f"dre_act_{act_type}_{number}_{year}_{month}_{day}_{region}_{lang}.{fmt}"
            self.logger.info(f"Requesting legal act: type={act_type}, number={number}, year={year}, "
                             f"month={month}, day={day}, region={region}, lang={lang}, fmt={fmt}")

        elif document_type == 'consolidated':
            if not all([act_type, number, year, region, cons_date]):
                raise ValueError("Consolidated act downloads require act_type, number, year, region, and cons_date")
            url = f"{self.BASE_URL}/{act_type}/{number}/{year}/{region}/cons/{cons_date}/{lang}/{fmt}"
            filename = f"dre_cons_{act_type}_{number}_{year}_{region}_{cons_date}_{lang}.{fmt}"
            self.logger.info(f"Requesting consolidated act: type={act_type}, number={number}, year={year}, "
                             f"region={region}, cons_date={cons_date}, lang={lang}, fmt={fmt}")

        else:
            raise ValueError(f"Unknown document_type: {document_type}. Must be 'journal', 'legal_act', or "
                             f"'consolidated'")

        return self._download(url, filename, fmt)

    def _download(self, url, filename, fmt=None):
        self.logger.info(f"Downloading from URL: {url} to filename: {filename}")
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            if '/dr/error' in str(response.url):
                # An unknown ELI (or an act older than the ELI register) redirects to an error page
                self.logger.error(f"Diário da República has no document at {url}")
                return None
            content_type = response.headers.get('Content-Type', '')
            if fmt == 'pdf' and 'pdf' not in content_type:
                raise ContentTypeError(f"Expected PDF response but got: {content_type}", content_type)
            if fmt == 'xml' and 'xml' not in content_type:
                raise ContentTypeError(f"Expected XML response but got: {content_type}", content_type)
            if fmt == 'html' and 'html' not in content_type:
                raise ContentTypeError(f"Expected HTML response but got: {content_type}", content_type)
            if (fmt in ('html', 'xhtml') and b'OutSystemsApp' in response.content
                    and b'reactContainer' in response.content):
                # diariodarepublica.pt now renders its pages with JavaScript: the HTML
                # holds no legal text, only the PDF can be retrieved directly
                raise ContentTypeError(
                    "Diário da República returned a JavaScript application page without the text; "
                    "use fmt='pdf'", content_type)
            if fmt == 'json' and 'json' not in content_type:
                raise ContentTypeError(f"Expected JSON response but got: {content_type}", content_type)
            if fmt == 'txt' and 'plain' not in content_type:
                raise ContentTypeError(f"Expected TXT response but got: {content_type}", content_type)
            if fmt == 'xhtml' and 'xhtml' not in content_type:
                raise ContentTypeError(f"Expected XHTML response but got: {content_type}", content_type)
            if fmt == 'zip' and 'zip' not in content_type:
                raise ContentTypeError(f"Expected ZIP response but got: {content_type}", content_type)
            file_path = os.path.join(self.download_dir, filename)
            with open(file_path, "wb") as f:
                f.write(response.content)
            return file_path
        except ContentTypeError:
            raise
        except requests.HTTPError as e:
            logging.error(f"HTTP error: {e} - {getattr(e.response, 'text', '')}")
            return None
        except Exception as e:
            logging.error(f"Error downloading from DRE: {e}")
            return None


DRE = 'https://diariodarepublica.pt'
DRE_ELI = 'https://data.dre.pt/eli'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'
# The page of a consolidated act: /dr/legislacao-consolidada/decreto-lei/1995-34437675[-<version id>]
CONSOLIDATED_PAGE = re.compile(r'/dr/legislacao-consolidada/(?P<tipo>[a-z][a-z\-]*)/(?P<year>\d{4})-(?P<id>\d+)')
# OutSystems gives every anonymous visitor this CSRF token
ANONYMOUS_CSRF = 'T6C+9iB49TLra4jEsMeSckDMNhQ='
# Screen services the consolidated legislation pages call: (module, screen, action, API version).
# The API versions change when the site is redeployed; they are then read again from the page scripts.
SCREEN_SERVICES = {
    'diploma': ('LegislacaoConsolidada', 'LegCons_Detalhe', 'DataActionGetDiplomaFragByIdAndApplicationSetting',
                'nc_pvjc74SJq_vOvUM4nCg'),
    'text': ('LegislacaoConsolidada', 'LegCons_Detalhe', 'DataActionGetData', '0J5toCe4aZFDi88AoH0G0Q'),
    'codes': ('MenusParaPesquisa', 'LegislacaoPorCodigo', 'DataActionGetCodigos', '8PR5RObK8y_eLLk_RGAS7Q'),
}


def consolidated_page(url: str) -> Optional[tuple[str, str, str]]:
    """'https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2009-34546475' -> ('lei', '2009', '34546475')."""
    match = CONSOLIDATED_PAGE.search(url)
    return (match.group('tipo'), match.group('year'), match.group('id')) if match else None


class PortugalConsolidatedClient(Client):
    """
    Reads consolidated Portuguese legislation (Legislação Consolidada) from the Diário da República.

    The pages of diariodarepublica.pt are an OutSystems application: the text
    of a consolidated act, as in force on a date, comes from the screen
    services its page calls, as JSON fragments (the act, its divisions,
    articles, annexes and signature, each in the version valid on that date).
    """

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        if proxies:
            self.session.proxies.update(proxies)
        self._module_version: Optional[str] = None
        self._api = {name: service[3] for name, service in SCREEN_SERVICES.items()}

    def resolve_eli(self, act_type: str, number: str, year: str, region: str = 'p',
                    date: str = '19000101') -> Optional[tuple[str, str, str]]:
        """
        The consolidated page of an act from its ELI parts, or None when the act is not consolidated.

        data.dre.pt redirects a consolidated ELI (``lei/7/2009/p/cons/<date>/pt/html``)
        to the act's page; an act without a consolidated version goes to an error page.
        """
        url = f'{DRE_ELI}/{act_type}/{number}/{year}/{region}/cons/{date}/pt/html'
        try:
            response = self.session.get(url, timeout=60)
        except requests.RequestException as e:
            raise NetworkError(f"Diário da República did not answer for {url}: {e}") from e
        return consolidated_page(unquote(response.url))

    def codes(self) -> list[dict[str, str]]:
        """The codes listed under 'Legislação por código': designation and consolidated page."""
        data = self._call('codes', {'SearchText': ''})
        found = []
        for item in (data.get('CodigosList') or {}).get('List') or []:
            fragment = item.get('DiplomaFrag') or {}
            if fragment.get('Designacao') and fragment.get('LinkSiteMap'):
                found.append({'designation': fragment['Designacao'].strip(), 'page': fragment['LinkSiteMap']})
        return found

    def download(self, tipo: str, year: str, fragment_id: str, date: str) -> str:
        """
        Save the consolidated act at /dr/legislacao-consolidada/<tipo>/<year>-<fragment_id>, as in force on
        ``date`` (ISO), as one JSON document; returns its path.
        """
        page = f'{DRE}/dr/legislacao-consolidada/{tipo}/{year}-{fragment_id}'
        variables = self._variables(tipo, year, fragment_id, date)
        diploma = self._diploma(variables, page)
        detail = diploma['ConsolidadaConteudoDetalhe']
        legis_id = detail['DiplomaFrag']['DiplomaLegisId']
        variables.update({'DiplomaLegisId': legis_id, 'GetDiplomaFragByIdAndApplicationSetting': diploma})
        text = self._call('text', variables)
        fragments = (text.get('LegConsBase') or {}).get('List') or []
        if not fragments:
            raise FileLoadError(f"Diário da República returned no text for the consolidated act at {page}")
        document = {
            'page': page,
            'date': date,
            'diploma': detail,
            'consolidation': {key: value for key, value in text.items() if key != 'LegConsBase'},
            'fragments': fragments,
        }
        path = os.path.join(self.download_dir, f'dre_cons_{tipo}_{year}_{fragment_id}_{date}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(document, f, ensure_ascii=False)
        return path

    def diploma(self, tipo: str, year: str, fragment_id: str) -> dict[str, Any]:
        """The details of a consolidated act: designation, publication (DiplomaLegis), type (TipoDiploma)."""
        page = f'{DRE}/dr/legislacao-consolidada/{tipo}/{year}-{fragment_id}'
        variables = self._variables(tipo, year, fragment_id, datetime.date.today().isoformat())
        return self._diploma(variables, page)['ConsolidadaConteudoDetalhe']

    @staticmethod
    def _variables(tipo: str, year: str, fragment_id: str, date: str) -> dict[str, Any]:
        """The variables of the consolidated act's page the screen services read."""
        return {'Tipo': tipo, 'Key': f'{year}-{fragment_id}', 'DiplomaFragId': fragment_id, 'Ano': int(year),
                'DataSelecionada': date, 'DataAux': date}

    def _diploma(self, variables: dict[str, Any], page: str) -> dict[str, Any]:
        diploma = self._call('diploma', variables)
        detail = diploma.get('ConsolidadaConteudoDetalhe') or {}
        legis_id = (detail.get('DiplomaFrag') or {}).get('DiplomaLegisId')
        if not legis_id or legis_id == '0':
            raise FileLoadError(f"Diário da República has no consolidated act at {page}")
        return diploma

    def _call(self, name: str, variables: dict[str, Any]) -> dict[str, Any]:
        """Call a screen service with the screen's variables and return its data."""
        module, screen, action, _ = SCREEN_SERVICES[name]
        url = f'{DRE}/dr/screenservices/dr/{module}/{screen}/{action}'
        for attempt in range(2):
            body = {'versionInfo': {'moduleVersion': self._version(), 'apiVersion': self._api[name]},
                    'viewName': f'{module}.{screen}', 'screenData': {'variables': variables}, 'clientVariables': {}}
            try:
                response = self.session.post(url, json=body, timeout=180,
                                             headers={'X-CSRFToken': ANONYMOUS_CSRF, 'Accept': 'application/json'})
                response.raise_for_status()
                reply = response.json()
            except requests.RequestException as e:
                raise NetworkError(f"Diário da República did not answer {action}: {e}") from e
            except ValueError as e:
                raise NetworkError(f"Diário da República did not answer {action} with JSON") from e
            info = reply.get('versionInfo') or {}
            if info.get('hasModuleVersionChanged') or info.get('hasApiVersionChanged'):
                if attempt == 0:
                    # The site was redeployed: read the current versions and ask again
                    self._refresh(name, api=bool(info.get('hasApiVersionChanged')))
                    continue
                raise NetworkError(f"Diário da República changed its {screen} service; tulit cannot read it")
            if reply.get('exception'):
                raise NetworkError(f"Diário da República failed on {action}: "
                                   f"{reply['exception'].get('message', reply['exception'])}")
            return reply.get('data') or {}
        raise NetworkError(f"Diário da República did not answer {action}")  # pragma: no cover

    def _version(self) -> str:
        if self._module_version is None:
            try:
                response = self.session.get(f'{DRE}/dr/moduleservices/moduleversioninfo', timeout=60)
                response.raise_for_status()
                self._module_version = response.json()['versionToken']
            except (requests.RequestException, ValueError, KeyError) as e:
                raise NetworkError(f"Cannot read the version of the Diário da República application: {e}") from e
        return self._module_version

    def _refresh(self, name: str, api: bool) -> None:
        """Read the module version again and, if needed, the API version of a screen service from its script."""
        self._module_version = None
        if not api:
            return
        module, screen, action, _ = SCREEN_SERVICES[name]
        script = f'{DRE}/dr/scripts/dr.{module}.{screen}.mvc.js'
        try:
            response = self.session.get(script, params={'v': self._version()}, timeout=60)
            response.raise_for_status()
        except requests.RequestException as e:
            raise NetworkError(f"Cannot read {script}: {e}") from e
        match = re.search(rf'"screenservices/dr/{module}/{screen}/{action}", "([^"]+)"', response.text)
        if match:
            self._api[name] = match.group(1)
