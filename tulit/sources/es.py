"""
Spain: Boletín Oficial del Estado (BOE).
"""
import datetime
import os
from typing import Any, Optional

from lxml import etree

from tulit.client.state.boe import BOEClient
from tulit.parser.exceptions import FileLoadError
from tulit.sources.base import CONSOLIDATED, ORIGINAL, Retrieval, Source


def _iso(stamp: Optional[str]) -> Optional[str]:
    """'20181207' -> '2018-12-07'."""
    if stamp and len(stamp) >= 8 and stamp[:8].isdigit():
        return f'{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}'
    return None


class SpainSource(Source):
    code = 'ES'
    name = 'Spain'
    source_name = 'Boletín Oficial del Estado (BOE)'
    languages = ('spa',)
    identifier_help = "a BOE identifier (e.g. 'BOE-A-2018-16673' for Ley Orgánica 3/2018)"

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
        client = BOEClient(download_dir=download_dir)
        boe_id = identifier.strip()
        try:
            folder = client.download_consolidated(boe_id)
        except FileLoadError:
            if version == CONSOLIDATED:
                raise
            # Acts outside the consolidated database: the gazette text as published
            return Retrieval(
                path=client.download_gazette(boe_id),
                parser='boe',
                version=ORIGINAL,
                language='spa',
                meta={'source': f'https://www.boe.es/diario_boe/txt.php?id={boe_id}'},
            )

        meta_root = etree.parse(os.path.join(folder, 'metadatos.xml')).getroot().find('.//metadatos')
        fields = {c.tag: (c.text or '').strip() for c in meta_root} if meta_root is not None else {}
        target = (date or datetime.date.today().isoformat()).replace('-', '')
        text = etree.parse(os.path.join(folder, 'texto.xml')).getroot()
        if version == CONSOLIDATED:
            applied = [v.get('fecha_vigencia') for v in text.iter('version')
                       if (v.get('fecha_vigencia') or '') <= target]
            version_date = _iso(max(applied)) if applied else None
            if version_date is None:
                raise FileLoadError(f"{boe_id} was not in force on {date}")
        else:
            version_date = _iso(fields.get('fecha_publicacion'))

        return Retrieval(
            path=folder,
            parser='boe-consolidated',
            parser_options={'version': version, 'date': date},
            version=version,
            language='spa',
            version_date=version_date,
            meta={
                'eli': fields.get('url_eli') or None,
                'date_document': _iso(fields.get('fecha_disposicion')),
                'in_force': fields.get('estatus_derogacion') == 'N' if fields.get('estatus_derogacion') else None,
                'source': fields.get('url_html_consolidada') or f'https://www.boe.es/buscar/act.php?id={boe_id}',
            },
        )
