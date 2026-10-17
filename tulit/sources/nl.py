"""
Netherlands: Basiswettenbestand (wetten.overheid.nl) and the Staatsblad.

Consolidated law is addressed by its BWB identifier, an act as adopted by
its Staatsblad identifier ('stb-2018-144' or 'Stb. 2018, 144').
"""
import datetime
import re
from typing import Any, Optional

from lxml import etree

from tulit.client.state.netherlands import BWB_ID, BWBClient
from tulit.parser.exceptions import FileLoadError
from tulit.sources.base import CONSOLIDATED, ORIGINAL, Retrieval, Source

OFFICIAL_PUBLICATIONS = 'https://zoek.officielebekendmakingen.nl'
_STAATSBLAD = re.compile(r'^(?:stb-(?P<year>\d{4})-(?P<number>\d+)|'
                         r'(?:Stb\.?|Staatsblad)\s*(?P<year2>\d{4}),?\s*(?:nr\.?\s*)?(?P<number2>\d+))$',
                         re.IGNORECASE)


def staatsblad_id(identifier: str) -> Optional[str]:
    """'stb-2018-144', 'Stb. 2018, 144' or 'Staatsblad 2018, 144' -> 'stb-2018-144'."""
    match = _STAATSBLAD.match(identifier.strip())
    if not match:
        return None
    year = match.group('year') or match.group('year2')
    number = match.group('number') or match.group('number2')
    return f'stb-{year}-{number}'


def _publication_date(path: str) -> Optional[str]:
    """Signing date of the act ('dagtekening'), as ISO date."""
    root = etree.parse(path).getroot()
    date = root.find('.//wetsluiting//dagtekening/datum')
    return date.get('isodatum') if date is not None else None


class NetherlandsSource(Source):
    code = 'NL'
    name = 'Netherlands'
    source_name = 'Basiswettenbestand (wetten.overheid.nl) and Staatsblad (KOOP)'
    versions = (ORIGINAL, CONSOLIDATED)
    languages = ('nld',)
    identifier_help = ("a BWB identifier for consolidated law (e.g. 'BWBR0001854' for the Wetboek van "
                       "Strafrecht) or a Staatsblad identifier for the act as adopted (e.g. 'stb-2018-144')")
    # wetten.overheid.nl has no ELI; its permanent URLs are matched instead
    eli_patterns = (
        re.compile(r'^https?://wetten\.overheid\.nl/(?P<id>BWB[RV]\d{7})(/.*)?$'),
        re.compile(r'^https?://zoek\.officielebekendmakingen\.nl/(?P<id>stb-\d{4}-\d+)(\.html|/.*)?$'),
    )
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
        client = BWBClient(download_dir=download_dir)
        publication = staatsblad_id(identifier)
        bwb_id = identifier.strip()
        if publication is None and not BWB_ID.match(bwb_id):
            raise ValueError(f"'{identifier}' is not a BWB or Staatsblad identifier; use {self.identifier_help}")
        version = version or (ORIGINAL if publication else CONSOLIDATED)

        if version == CONSOLIDATED:
            if publication:
                raise ValueError("Consolidated law is addressed by its BWB identifier (e.g. 'BWBR0040940'), "
                                 "not by a Staatsblad identifier")
            return self._consolidated(client, bwb_id, date, version)

        if date:
            raise ValueError("A date selects a consolidated version; the original version has none")
        if publication is None:
            publication = client.original_publication(bwb_id)
            if publication is None:
                raise FileLoadError(f"The BWB names no Staatsblad publication for {bwb_id}")
        path = client.download_publication(publication)
        signed = _publication_date(path)
        return Retrieval(
            path=path,
            parser='bwb',
            version=version,
            language='nld',
            version_date=signed,
            meta={
                'eli': f'{OFFICIAL_PUBLICATIONS}/{publication}',
                'date_document': signed,
                'source': f'{OFFICIAL_PUBLICATIONS}/{publication}.html',
            },
        )

    def _consolidated(self, client: BWBClient, bwb_id: str, date: Optional[str], version: str) -> Retrieval:
        date = date or datetime.date.today().isoformat()
        path, record = client.download(bwb_id, date)
        meta = {
            'in_force': True,
            'source': record.get('toestand') or record.get('locatie_toestand'),
        }
        return Retrieval(
            path=path,
            parser='bwb',
            version=version,
            language='nld',
            version_date=record.get('geldigheidsperiode_startdatum') or date,
            meta=meta,
        )
