"""
Sweden: Svensk författningssamling (SFS), consolidated, through the Riksdag open data.
"""
import datetime
import re
from typing import Any, Optional

from tulit.client.state.sweden import RIKSDAGEN, RiksdagenClient
from tulit.sources.base import CONSOLIDATED, Retrieval, Source

_SFS = re.compile(r'(?:^|SFS\s*|sfs-|/)(?P<year>\d{4})[:-](?P<number>\d+(?:\s?[a-z])?)\b', re.IGNORECASE)


def document_id(identifier: str) -> str:
    """'2018:218', 'SFS 2018:218' or 'sfs-2018-218' -> 'sfs-2018-218'."""
    match = _SFS.search(identifier.strip())
    if not match:
        raise ValueError(f"'{identifier}' is not an SFS number; use e.g. '2018:218'")
    return f"sfs-{match.group('year')}-{match.group('number').replace(' ', '')}"


class SwedenSource(Source):
    code = 'SE'
    name = 'Sweden'
    source_name = 'Svensk författningssamling (Government Offices, via the Riksdag open data)'
    versions = (CONSOLIDATED,)
    languages = ('swe',)
    identifier_help = "the SFS number of a statute (e.g. '2018:218' for the Data Protection Act)"
    eli_patterns = (re.compile(r'^https?://data\.riksdagen\.se/dokument(status)?/(?P<id>sfs-\d{4}-\d+[a-z]?)(\.\w+)?$'),)

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
        today = datetime.date.today().isoformat()
        if date and date < today:
            raise ValueError("The Riksdag publishes only the statute as in force now; a past date cannot be selected")
        doc_id = document_id(identifier)
        client = RiksdagenClient(download_dir=download_dir)
        path = client.download(doc_id)
        document = client.metadata(doc_id) if metadata else {}
        issued = (document.get('datum') or '')[:10] or None
        return Retrieval(
            path=path,
            parser='se-sfs',
            parser_options={'date': date or today},
            version=version,
            language='swe',
            version_date=date or today,
            meta={
                'date_document': issued,
                'source': f'{RIKSDAGEN}/dokument/{doc_id}.html',
            },
        )
