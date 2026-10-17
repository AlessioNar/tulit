"""
Client for the Austrian Rechtsinformationssystem des Bundes (RIS).

Consolidated federal law (Bundesrecht konsolidiert) is published through
the RIS open-data API, one XML document per paragraph (§), article or
annex. The client downloads every unit in force on a given date and writes
an ``index.json`` listing them in document order, which ``RISParser``
reads.

API documentation: https://data.bka.gv.at/ris/api/v2.6/
Licence: CC BY 4.0.
"""
import json
import os
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError

RIS_API = 'https://data.bka.gv.at/ris/api/v2.6/Bundesrecht'
RIS_ELI = 'https://www.ris.bka.gv.at/eli/'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'


class AustriaRISClient(Client):
    """Downloads consolidated Austrian federal law from the RIS open-data API."""

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        # Large laws need over a thousand requests: retry dropped connections and
        # transient server errors instead of failing the whole download
        retry = Retry(total=5, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=('GET',))
        self.session.mount('https://', HTTPAdapter(max_retries=retry))
        if proxies:
            self.session.proxies.update(proxies)

    def search(self, gesetzesnummer: str, date: str) -> list[dict[str, Any]]:
        """
        Metadata of every unit of a law in force on ``date``, in document order.

        Parameters
        ----------
        gesetzesnummer : str
            The RIS law number (Gesetzesnummer), e.g. '10001597'.
        date : str
            ISO date (YYYY-MM-DD).
        """
        references: list[dict[str, Any]] = []
        page = 1
        while True:
            params = {
                'Applikation': 'BrKons',
                'Gesetzesnummer': gesetzesnummer,
                'FassungVom': date,
                'DokumenteProSeite': 'OneHundred',
                'Seitennummer': page,
            }
            try:
                response = self.session.get(RIS_API, params=params, timeout=60)
                response.raise_for_status()
                results = response.json()['OgdSearchResult']['OgdDocumentResults']
            except (requests.RequestException, KeyError, ValueError) as e:
                raise NetworkError(f"RIS search failed for Gesetzesnummer {gesetzesnummer}: {e}") from e

            batch = results.get('OgdDocumentReference', [])
            if isinstance(batch, dict):
                batch = [batch]
            references.extend(batch)
            total = int(results['Hits']['#text'])
            if not batch or len(references) >= total:
                return references
            page += 1

    def download(self, gesetzesnummer: str, date: str) -> str:
        """
        Download a law as in force on ``date``.

        Returns
        -------
        str
            Folder holding one XML file per unit and ``index.json``.
        """
        references = self.search(gesetzesnummer, date)
        if not references:
            raise FileLoadError(f"No RIS law {gesetzesnummer} in force on {date}")

        folder = os.path.join(self.download_dir, 'AT', gesetzesnummer, date)
        os.makedirs(folder, exist_ok=True)
        units = []
        for reference in references:
            data = reference['Data']
            document_id = data['Metadaten']['Technisch']['ID']
            federal = data['Metadaten']['Bundesrecht']
            consolidated = federal.get('BrKons', {})
            xml_url = _content_url(data, 'Xml')
            if xml_url is None:
                self.logger.warning("No XML for RIS document %s", document_id)
                continue
            filename = f'{document_id}.xml'
            self._save(xml_url, os.path.join(folder, filename))
            units.append({
                'id': document_id,
                'file': filename,
                'unit': consolidated.get('ArtikelParagraphAnlage'),
                'type': consolidated.get('Dokumenttyp'),
                'short_title': federal.get('Kurztitel'),
                'title': federal.get('Titel'),
                'eli': federal.get('Eli'),
                'in_force_from': consolidated.get('Inkrafttretensdatum'),
                'in_force_to': consolidated.get('Ausserkrafttretensdatum'),
                'gazette': consolidated.get('StammnormPublikationsorgan'),
                'gazette_number': consolidated.get('StammnormBgblnummer'),
                'law_url': consolidated.get('GesamteRechtsvorschriftUrl'),
            })

        index = {'gesetzesnummer': gesetzesnummer, 'date': date, 'units': units}
        with open(os.path.join(folder, 'index.json'), 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        self.logger.info("Downloaded %d RIS units of %s to %s", len(units), gesetzesnummer, folder)
        return folder

    def _save(self, url: str, path: str) -> None:
        if os.path.exists(path):
            return
        try:
            response = self.session.get(url, timeout=60)
            response.raise_for_status()
        except requests.RequestException as e:
            raise NetworkError(f"Failed to download {url}: {e}") from e
        with open(path, 'wb') as f:
            f.write(response.content)


def law_eli(gazette: Optional[str], gazette_number: Optional[str]) -> Optional[str]:
    """
    ELI of the original publication of a law, from its gazette reference.

    'BGBl. I Nr.' and '165/1999' -> https://www.ris.bka.gv.at/eli/bgbl/i/1999/165
    Only federal law gazette (BGBl.) references from 1997 on have ELIs.
    """
    if not gazette or not gazette_number or not gazette.startswith('BGBl.'):
        return None
    part = gazette.replace('BGBl.', '').replace('Nr.', '').strip().lower()
    try:
        number, year = gazette_number.split('/')
    except ValueError:
        return None
    if part not in ('i', 'ii', 'iii') or not year.isdigit() or int(year) < 1997:
        return None
    return f'{RIS_ELI}bgbl/{part}/{year}/{number}'


def _content_url(data: dict[str, Any], data_type: str) -> Optional[str]:
    references = data.get('Dokumentliste', {}).get('ContentReference', [])
    if isinstance(references, dict):
        references = [references]
    for reference in references:
        if reference.get('ContentType') != 'MainDocument':
            continue
        urls = reference.get('Urls', {}).get('ContentUrl', [])
        if isinstance(urls, dict):
            urls = [urls]
        for url in urls:
            if url.get('DataType') == data_type:
                return url.get('Url')
    return None
