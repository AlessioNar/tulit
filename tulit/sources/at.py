"""
Austria: Rechtsinformationssystem des Bundes (RIS).
"""
import datetime
import json
import os
from typing import Any, Optional

from tulit.client.state.austria import AustriaRISClient, law_eli
from tulit.sources.base import CONSOLIDATED, Retrieval, Source


class AustriaSource(Source):
    code = 'AT'
    name = 'Austria'
    source_name = 'Rechtsinformationssystem des Bundes (RIS)'
    versions = (CONSOLIDATED,)
    languages = ('deu',)
    identifier_help = "a RIS Gesetzesnummer (e.g. '10001597' for the Datenschutzgesetz)"

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
        client = AustriaRISClient(download_dir=download_dir)
        folder = client.download(identifier, date)

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
