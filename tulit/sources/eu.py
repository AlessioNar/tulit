"""
European Union: Cellar, the repository of the Publications Office of the EU.
"""
import datetime
import os
import re
from typing import Any, Optional

from tulit.client.eu.cellar import CellarClient
from tulit.parser.exceptions import FileLoadError
from tulit.sources.base import CONSOLIDATED, ORIGINAL, Retrieval, Source

CELLAR_RESOURCE = 'http://publications.europa.eu/resource/cellar/'

# Cellar download format -> registry format id of the parser that reads it
CELLAR_FORMATS = {
    'fmx4': 'formex',
    'xhtml': 'cellar-xhtml',
    'html': 'cellar-html',
}

# The 24 official languages, as ISO 639-3 codes (Cellar uses them in upper case)
EU_LANGUAGES = (
    'eng', 'bul', 'ces', 'dan', 'deu', 'ell', 'est', 'fin', 'fra', 'gle', 'hrv', 'hun',
    'ita', 'lav', 'lit', 'mlt', 'nld', 'pol', 'por', 'ron', 'slk', 'slv', 'spa', 'swe',
)


class EUSource(Source):
    code = 'EU'
    name = 'European Union'
    source_name = 'Cellar (Publications Office of the EU)'
    languages = EU_LANGUAGES
    identifier_help = "a CELEX number (e.g. '32024R0903') or an EU ELI (http://data.europa.eu/eli/...)"
    eli_patterns = (re.compile(r'^(?P<id>https?://data\.europa\.eu/eli/.+?)/?$'),)
    options = ('format',)

    def retrieve(
        self,
        identifier: str,
        version: str,
        date: Optional[str],
        language: Optional[str],
        download_dir: str,
        metadata: bool = True,
        format: str = 'fmx4',
        **options: Any,
    ) -> Retrieval:
        if format not in CELLAR_FORMATS:
            raise ValueError(
                f"Unsupported format '{format}'. Choose one of: {', '.join(CELLAR_FORMATS)}"
            )
        language = (language or self.default_language).lower()
        client = CellarClient(download_dir=download_dir)

        celex = identifier
        if identifier.startswith(('http://', 'https://')):
            celex = client.celex_from_eli(identifier)
            if celex is None:
                raise FileLoadError(f"No act found in Cellar for ELI {identifier}")

        document_celex, version_date = celex, None
        if version == CONSOLIDATED:
            target = date or datetime.date.today().isoformat()
            found = client.get_consolidated_celex(celex, target)
            if found is None:
                raise FileLoadError(f"No consolidated version of {celex} on or before {target}")
            document_celex, version_date = found

        paths = [p for p in (client.download(document_celex, format=format, language=language) or []) if p]
        if not paths:
            raise FileLoadError(
                f"No {format} document found in Cellar for {document_celex} in language {language.upper()}"
            )

        meta = client.get_metadata(celex) if metadata else {}
        meta['source'] = _source_uri(paths, download_dir)
        if version == ORIGINAL:
            version_date = meta.get('date_document')

        # A Formex act may be split over several items (DOC_1.xml, DOC_2.xml, ...);
        # the Formex parser reads the whole folder and finds the act and its annexes
        path = paths[0] if len(paths) == 1 else os.path.commonpath(paths)
        return Retrieval(
            path=path,
            parser=CELLAR_FORMATS[format],
            version=version,
            language=language,
            version_date=version_date,
            meta=meta,
        )


def _source_uri(paths, download_dir):
    """Cellar URI of the downloaded item, or of the manifestation holding several items."""
    ids = [os.path.relpath(p, download_dir).replace(os.sep, '/') for p in paths]
    ids = [os.path.splitext(i)[0] if '/' in i else i for i in ids]
    if len(ids) == 1:
        return CELLAR_RESOURCE + ids[0]
    return CELLAR_RESOURCE + os.path.commonprefix(ids).rstrip('/').rsplit('/', 1)[0]
