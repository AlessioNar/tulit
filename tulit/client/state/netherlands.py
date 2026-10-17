"""
Client for the Basiswettenbestand (BWB), the consolidated Dutch legislation behind wetten.overheid.nl.

The SRU 2.0 search service returns, for a BWB identifier and a date, the
consolidated version (toestand) in force on that date, with the location of
its XML in the official publications repository.

Acts as adopted are published in the Staatsblad; the official publications
repository holds their XML from 1995 on.

Run by KOOP for the Ministry of the Interior. Licence: CC0.
SRU documentation: https://data.overheid.nl (Handleiding SRU 2.0).
"""
import datetime
import os
import re
from typing import Any, Optional

import requests
from lxml import etree
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError

SRU_ENDPOINT = 'https://zoekservice.overheid.nl/sru/Search'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'
BWB_ID = re.compile(r'^BWB[RV]\d{7}$')
REPOSITORY = 'https://repository.officiele-overheidspublicaties.nl/officielepublicaties'
PUBLICATION_ID = re.compile(r'^stb-(\d{4})-(\d+)$')


class BWBClient(Client):
    """Downloads consolidated Dutch legislation (BWB toestand XML)."""

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT, 'Accept': 'application/xml'})
        retry = Retry(total=4, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=('GET',))
        self.session.mount('https://', HTTPAdapter(max_retries=retry))
        if proxies:
            self.session.proxies.update(proxies)

    def search(self, bwb_id: str, date: str) -> Optional[dict[str, Any]]:
        """
        Metadata of the version of a regulation in force on ``date``, or None.

        The result holds the SRU record fields, e.g. 'title', 'type',
        'geldigheidsperiode_startdatum' and 'locatie_toestand' (the XML).
        """
        if not BWB_ID.match(bwb_id):
            raise ValueError(f"'{bwb_id}' is not a BWB identifier (e.g. 'BWBR0001854')")
        params = {
            'operation': 'searchRetrieve',
            'version': '2.0',
            'x-connection': 'BWB',
            'query': f'dcterms.identifier=={bwb_id} and overheidbwb.geldigheidsdatum=={date}',
            'maximumRecords': '10',
        }
        try:
            response = self.session.get(SRU_ENDPOINT, params=params, timeout=60)
            response.raise_for_status()
            root = etree.fromstring(response.content)
        except (requests.RequestException, etree.XMLSyntaxError) as e:
            raise NetworkError(f"BWB search failed for {bwb_id}: {e}") from e

        for record in root.iter('{*}recordData'):
            fields: dict[str, Any] = {}
            for element in record.iter():
                if isinstance(element.tag, str) and element.text and element.text.strip():
                    fields.setdefault(etree.QName(element).localname, element.text.strip())
            if fields.get('identifier') == bwb_id and fields.get('locatie_toestand'):
                return fields
        return None

    def download(self, bwb_id: str, date: str) -> tuple[str, dict[str, Any]]:
        """
        Download the version of a regulation in force on ``date``.

        Returns
        -------
        tuple
            (path of the toestand XML, SRU metadata of that version)
        """
        record = self.search(bwb_id, date)
        if record is None:
            raise FileLoadError(f"No version of {bwb_id} in force on {date} in the BWB")
        url = record['locatie_toestand']
        target = os.path.join(self.download_dir, 'NL', bwb_id, os.path.basename(url))
        if not os.path.exists(target):
            try:
                response = self.session.get(url, timeout=120)
                response.raise_for_status()
            except requests.RequestException as e:
                raise NetworkError(f"Failed to download {url}: {e}") from e
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as f:
                f.write(response.content)
        return target, record

    def original_publication(self, bwb_id: str) -> Optional[str]:
        """
        The Staatsblad issue that first published a regulation ('stb-2018-144'), or None.

        Read from the 'oorspronkelijk' metadata of its current consolidated version.
        """
        path, _ = self.download(bwb_id, datetime.date.today().isoformat())
        root = etree.parse(path).getroot()
        publication = root.find('.//oorspronkelijk/publicatie')
        if publication is None or publication.get('soort') != 'Stb':
            return None
        year, number = publication.findtext('publicatiejaar'), publication.findtext('publicatienr')
        return publication.get('urlidentifier') or (f'stb-{year}-{number}' if year and number else None)

    def download_publication(self, publication_id: str) -> str:
        """Download the XML of a Staatsblad issue ('stb-2018-144') and return its path."""
        match = PUBLICATION_ID.match(publication_id)
        if not match:
            raise ValueError(f"'{publication_id}' is not a Staatsblad identifier (e.g. 'stb-2018-144')")
        url = f'{REPOSITORY}/stb/{match.group(1)}/{publication_id}/1/xml/{publication_id}.xml'
        target = os.path.join(self.download_dir, 'NL', 'stb', f'{publication_id}.xml')
        if not os.path.exists(target):
            try:
                response = self.session.get(url, timeout=120)
            except requests.RequestException as e:
                raise NetworkError(f"Failed to download {url}: {e}") from e
            if response.status_code in (204, 404):
                raise FileLoadError(f"The official publications repository has no XML for {publication_id} "
                                    f"(XML is available from 1995)")
            if response.status_code != 200 or b'officiele-publicatie' not in response.content[:2000]:
                raise NetworkError(f"Unexpected response for {url}: HTTP {response.status_code}")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as f:
                f.write(response.content)
        return target
