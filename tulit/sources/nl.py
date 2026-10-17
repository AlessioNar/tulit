"""
Netherlands: Basiswettenbestand (wetten.overheid.nl).
"""
import datetime
import re
from typing import Any, Optional

from tulit.client.state.netherlands import BWBClient
from tulit.sources.base import CONSOLIDATED, Retrieval, Source


class NetherlandsSource(Source):
    code = 'NL'
    name = 'Netherlands'
    source_name = 'Basiswettenbestand (wetten.overheid.nl, KOOP)'
    versions = (CONSOLIDATED,)
    languages = ('nld',)
    identifier_help = "a BWB identifier (e.g. 'BWBR0001854' for the Wetboek van Strafrecht)"
    # wetten.overheid.nl has no ELI; its permanent URLs are matched instead
    eli_patterns = (re.compile(r'^https?://wetten\.overheid\.nl/(?P<id>BWB[RV]\d{7})(/.*)?$'),)

    def retrieve(
        self,
        identifier: str,
        version: str,
        date: Optional[str],
        language: Optional[str],
        download_dir: str,
        metadata: bool = True,
        **options: Any,
    ) -> Retrieval:
        date = date or datetime.date.today().isoformat()
        client = BWBClient(download_dir=download_dir)
        path, record = client.download(identifier.strip(), date)
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
