"""
Austria: Rechtsinformationssystem des Bundes (RIS).

Consolidated law is addressed by its RIS Gesetzesnummer, the law as adopted
by its Federal Law Gazette reference (BGBl. I Nr. 5/2024) or ELI.
"""
import datetime
import json
import os
import re
from typing import Any, Optional

from lxml import etree

from tulit.client.state.austria import AustriaRISClient, law_eli
from tulit.parser.exceptions import FileLoadError, UnsupportedError
from tulit.sources.base import CONSOLIDATED, ORIGINAL, Retrieval, Source

_GAZETTE = re.compile(
    r'^(?:BGBl\.?\s*)?(?P<part>I{1,3})\s*(?:Nr\.?\s*)?(?P<number>\d+)\s*/\s*(?P<year>\d{4})$', re.IGNORECASE)
_GAZETTE_ID = re.compile(r'^BGBLA_(?P<year>\d{4})_(?P<part>I{1,3})_(?P<number>\d+)$', re.IGNORECASE)
_GAZETTE_ELI = re.compile(r'eli/bgbl/(?P<part>i{1,3})/(?P<year>\d{4})/(?P<number>\d+)', re.IGNORECASE)
_GESETZESNUMMER = re.compile(r'^\d{8}$')
_MONTHS = ('Jänner', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August',
           'September', 'Oktober', 'November', 'Dezember')


def gazette_reference(identifier: str) -> Optional[tuple[str, str, str]]:
    """'BGBl. I Nr. 5/2024', 'I 5/2024', 'BGBLA_2024_I_5' or a BGBl. ELI -> ('I', '2024', '5')."""
    text = identifier.strip()
    match = _GAZETTE.match(text) or _GAZETTE_ID.match(text) or _GAZETTE_ELI.search(text)
    if not match:
        return None
    return match.group('part').upper(), match.group('year'), match.group('number')


def _issue_date(path: str) -> Optional[str]:
    """Publication date of a gazette issue ('Ausgegeben am 26. Februar 2024')."""
    root = etree.parse(path).getroot()
    for element in root.iter('{*}addat'):
        match = re.search(r'(\d{1,2})\.\s*(\w+)\s+(\d{4})', ''.join(element.itertext()))
        if match and match.group(2) in _MONTHS:
            month = _MONTHS.index(match.group(2)) + 1
            return datetime.date(int(match.group(3)), month, int(match.group(1))).isoformat()
    return None


class AustriaSource(Source):
    code = 'AT'
    name = 'Austria'
    source_name = 'Rechtsinformationssystem des Bundes (RIS)'
    versions = (ORIGINAL, CONSOLIDATED)
    languages = ('deu',)
    identifier_help = ("a RIS Gesetzesnummer for consolidated law (e.g. '10001597' for the Datenschutzgesetz) "
                       "or a Federal Law Gazette reference for the law as adopted (e.g. 'BGBl. I Nr. 5/2024')")
    eli_patterns = (re.compile(
        r'^(?P<id>https?://www\.ris\.bka\.gv\.at/eli/bgbl/(i|ii|iii)/\d{4}/\d+)(/.*)?$', re.IGNORECASE),)
    version_from_identifier = True

    def retrieve(
        self,
        identifier: str,
        version: Optional[str],
        date: Optional[str],
        language: Optional[str],
        download_dir: str,
        metadata: bool = True,
        **options: Any,
    ) -> Retrieval:
        client = AustriaRISClient(download_dir=download_dir)
        gazette = gazette_reference(identifier)
        if gazette is None and not _GESETZESNUMMER.match(identifier.strip()):
            raise UnsupportedError(f"'{identifier}' is not a RIS Gesetzesnummer or a BGBl. reference; "
                                   f"use {self.identifier_help}")
        version = version or (ORIGINAL if gazette else CONSOLIDATED)

        if version == CONSOLIDATED:
            if gazette:
                raise UnsupportedError("Consolidated law is addressed by its RIS Gesetzesnummer "
                                       "(e.g. '10001597'), not by a gazette reference")
            return self._consolidated(client, identifier.strip(), date, version)

        if date:
            raise UnsupportedError("A date selects a consolidated version; the original version has none")
        if gazette is None:
            gazette = client.gazette_reference(identifier.strip())
            if gazette is None:
                raise FileLoadError(f"RIS has no Federal Law Gazette reference for law {identifier}")
        part, year, number = gazette
        path = client.download_gazette(part, year, number)
        published = _issue_date(path)
        return Retrieval(
            path=path,
            parser='ris-bgbl',
            version=version,
            language='deu',
            version_date=published,
            meta={
                'eli': law_eli(f'BGBl. {part} Nr.', f'{number}/{year}'),
                'date_document': published,
                'source': f'https://www.ris.bka.gv.at/Dokumente/BgblAuth/BGBLA_{year}_{part}_{number}/'
                          f'BGBLA_{year}_{part}_{number}.xml',
            },
        )

    def _consolidated(self, client: AustriaRISClient, gesetzesnummer: str,
                      date: Optional[str], version: str) -> Retrieval:
        date = date or datetime.date.today().isoformat()
        folder = client.download(gesetzesnummer, date)

        with open(os.path.join(folder, 'index.json'), encoding='utf-8') as f:
            units = json.load(f)['units']
        first = units[0] if units else {}
        meta = {
            'eli': law_eli(first.get('gazette'), first.get('gazette_number')),
            'in_force': True,
            'source': first.get('law_url'),
        }
        return Retrieval(
            path=folder,
            parser='ris',
            version=version,
            language='deu',
            version_date=date,
            meta=meta,
        )
