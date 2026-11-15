"""
Client for Italian legislation on Normattiva.

Normattiva (https://www.normattiva.it), run by the Istituto Poligrafico e
Zecca dello Stato for the Presidency of the Council of Ministers, is the
official portal of Italian state legislation. It exports each act as Akoma
Ntoso as in force on any date: on the date of its publication in the
Gazzetta Ufficiale the export is the original text (its ELI alias ends in
/ORIGINAL), on a later date the consolidated text in force then.

An act is addressed by its URN ('urn:nir:stato:decreto.legislativo:2018;101')
or by the date of the Gazzetta Ufficiale and its code ('2018-09-04',
'18G00129'). The export needs the session that opening the act's page
creates, and the server refuses clients that do not present themselves as
browsers, so the client sends a browser-compatible User-Agent.
"""
import os
import re
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError

NORMATTIVA = 'https://www.normattiva.it'
GAZZETTA = 'https://www.gazzettaufficiale.it'
# Normattiva closes the connection to clients that do not name themselves Mozilla-compatible
USER_AGENT = 'Mozilla/5.0 (compatible; tulit; +https://pypi.org/project/tulit/)'
_EXPORT = re.compile(r'caricaAKN\?dataGU=(?P<date>\d{8})&(?:amp;)?codiceRedaz=(?P<code>\w+)')
_TITLE = re.compile(r'<title>\s*(?P<title>[^<]*?)\s*-\s*Normattiva\s*</title>')


class NormattivaAKNClient(Client):
    """Downloads Italian acts from Normattiva as Akoma Ntoso, as published or as in force on a date."""

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        # Normattiva resets connections now and then: retry them too
        retry = Retry(total=6, connect=6, read=6, backoff_factor=2,
                      status_forcelist=(429, 500, 502, 503, 504), allowed_methods=('GET',))
        self.session.mount('https://', HTTPAdapter(max_retries=retry))
        if proxies:
            self.session.proxies.update(proxies)

    def _get(self, url: str) -> requests.Response:
        try:
            response = self.session.get(url, timeout=180)
        except requests.RequestException as e:
            raise NetworkError(f"Normattiva request failed for {url}: {e}") from e
        if response.status_code != 200:
            raise NetworkError(f"Normattiva returned HTTP {response.status_code} for {url}")
        return response

    def resolve(self, urn: str) -> dict[str, Any]:
        """
        The Gazzetta Ufficiale date and code of the act a URN names, and its title.

        Opening the act's page also starts the session the export needs.
        """
        response = self._get(f'{NORMATTIVA}/uri-res/N2Ls?{urn}')
        match = _EXPORT.search(response.text)
        if not match:
            raise FileLoadError(f"Normattiva has no act {urn}")
        date = match.group('date')
        title = _TITLE.search(response.text)
        return {'date': f'{date[:4]}-{date[4:6]}-{date[6:]}', 'code': match.group('code'),
                'title': title.group('title') if title else None}

    def open_act(self, date: str, code: str) -> None:
        """Open the page of an act given by its Gazzetta Ufficiale date and code, starting the session."""
        year, month, day = date.split('-')
        response = self._get(f'{NORMATTIVA}/eli/id/{year}/{month}/{day}/{code}/CONSOLIDATED')
        if not _EXPORT.search(response.text):
            raise FileLoadError(f"Normattiva has no act published on {date} with code {code}")

    def download(self, date: str, code: str, in_force: Optional[str] = None) -> str:
        """
        Download the Akoma Ntoso of an act as in force on ``in_force`` (YYYY-MM-DD; the date of publication
        gives the original text) and return its path. The act's page must have been opened first.
        """
        in_force = in_force or date
        target = os.path.join(self.download_dir, 'IT', f'{code}_{in_force}.xml')
        if os.path.exists(target):
            return target
        if in_force == date:
            # The export follows the version the session shows: open the original one
            self._get(f'{NORMATTIVA}/atto/caricaDettaglioAtto?atto.dataPubblicazioneGazzetta={date}'
                      f'&atto.codiceRedazionale={code}&tipoDettaglio=originario&qId=')
        response = self._get(f"{NORMATTIVA}/do/atto/caricaAKN?dataGU={date.replace('-', '')}&codiceRedaz={code}"
                             f"&dataVigenza={in_force.replace('-', '')}")
        if b'akomaNtoso' not in response.content[:500]:
            raise FileLoadError(f"Normattiva did not export act {code} as in force on {in_force}")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as f:
            f.write(response.content)
        return target

    @staticmethod
    def gazzetta_eli(date: str, code: str) -> str:
        """The ELI of the act's publication in the Gazzetta Ufficiale."""
        year, month, day = date.split('-')
        return f'{GAZZETTA}/eli/id/{year}/{month}/{day}/{code}/sg'
