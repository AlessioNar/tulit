"""
Sweden: Svensk författningssamling (SFS).

- original: the act as adopted, from the official electronic SFS published by
  the Government Offices (svenskforfattningssamling.se, PDF), which exists
  from 1 April 2018 (SFS 2018:160); earlier acts appeared only in print;
- consolidated: the statute as in force now, the Government Offices' text
  republished by the Riksdag open data (data.riksdagen.se, HTML).

An SFS number ('2018:218', 'SFS 2018:218') names the act as adopted; a
Riksdag document id ('sfs-2018-218') or URL the consolidated statute.
"""
import datetime
import re
from typing import Any, Optional

from tulit.client.state.sweden import FIRST_ELECTRONIC, RIKSDAGEN, RiksdagenClient, SFSClient
from tulit.parser.exceptions import FileLoadError, NetworkError, UnsupportedError
from tulit.parser.pdf.sweden import masthead
from tulit.sources.base import CONSOLIDATED, ORIGINAL, Retrieval, Source

_SFS = re.compile(r'(?:^|SFS\s*|sfs-|/)(?P<year>\d{4})[:-](?P<number>\d+(?:\s?[a-z])?)\b', re.IGNORECASE)
_RIKSDAGEN_ID = re.compile(r'(?:^|/)sfs-\d{4}-\d+', re.IGNORECASE)


def sfs_number(identifier: str) -> tuple[str, str]:
    """'2018:218', 'SFS 2018:218' or 'sfs-2018-218' -> ('2018', '218')."""
    match = _SFS.search(identifier.strip())
    if not match:
        raise UnsupportedError(f"'{identifier}' is not an SFS number; use e.g. '2018:218'")
    return match.group('year'), match.group('number').replace(' ', '')


def document_id(identifier: str) -> str:
    """'2018:218', 'SFS 2018:218' or 'sfs-2018-218' -> 'sfs-2018-218' (the Riksdag document id)."""
    year, number = sfs_number(identifier)
    return f'sfs-{year}-{number}'


class SwedenSource(Source):
    code = 'SE'
    name = 'Sweden'
    source_name = ('Svensk författningssamling (Government Offices: svenskforfattningssamling.se as adopted, '
                   'the Riksdag open data consolidated)')
    versions = (ORIGINAL, CONSOLIDATED)
    languages = ('swe',)
    identifier_help = ("the SFS number of an act (e.g. '2018:218' or 'SFS 2018:218' for the Data Protection Act): "
                       "the act as published in Svensk författningssamling, from SFS 2018:160 (1 April 2018) on, "
                       "or with version='consolidated' the statute as in force now; a Riksdag document id or URL "
                       "('sfs-2018-218') names the consolidated statute")
    eli_patterns = (
        re.compile(r'^https?://data\.riksdagen\.se/dokument(status)?/(?P<id>sfs-\d{4}-\d+[a-z]?)(\.\w+)?$'),)
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
        year, number = sfs_number(identifier)
        if version is None:
            # The act as adopted where the electronic SFS has it; before it (April 2018), or for a Riksdag
            # document, or with a date, the consolidated text as before 1.0
            digits = re.match(r'\d+', number)
            electronic = number.isdigit() and (int(year), int(digits.group(0))) >= FIRST_ELECTRONIC
            version = ORIGINAL if electronic and not date and not _RIKSDAGEN_ID.search(identifier.strip()) \
                else CONSOLIDATED
        if version == CONSOLIDATED:
            return self._consolidated(f'sfs-{year}-{number}', date, download_dir, metadata)
        return self._original(int(year), number, date, download_dir, metadata)

    def _original(self, year: int, number: str, date: Optional[str], download_dir: str,
                  metadata: bool) -> Retrieval:
        if date:
            raise UnsupportedError("A date selects a consolidated version; the act as adopted has none")
        digits = re.match(r'\d+', number)
        if not number.isdigit() or (year, int(digits.group(0))) < FIRST_ELECTRONIC:
            raise UnsupportedError(
                f"SFS {year}:{number} was published only in the printed Svensk författningssamling: the official "
                f"electronic SFS starts with SFS {FIRST_ELECTRONIC[0]}:{FIRST_ELECTRONIC[1]} (1 April 2018) and "
                f"no official source publishes earlier acts as adopted in a machine-readable form. "
                f"Use version='consolidated' for the statute as in force now")
        # The Riksdag knows when a statute in force was issued, which finds its PDF in one request
        issued = None
        if metadata:
            try:
                issued = (RiksdagenClient(download_dir=download_dir).metadata(f'sfs-{year}-{number}').get('datum')
                          or '')[:10] or None
            except (FileLoadError, NetworkError):
                pass  # an amending act, or a repealed one: the Riksdag has no document for it
        path, url = SFSClient(download_dir=download_dir).download(year, number, issued)
        found = masthead(path)
        return Retrieval(
            path=path,
            parser='se-sfs-pdf',
            version=ORIGINAL,
            language='swe',
            version_date=found['published'],
            meta={key: value for key, value in {
                'date_document': found['issued'],
                'date_publication': found['published'],
                'source': url,
            }.items() if value},
        )

    def _consolidated(self, doc_id: str, date: Optional[str], download_dir: str, metadata: bool) -> Retrieval:
        today = datetime.date.today().isoformat()
        if date and date < today:
            raise UnsupportedError("The Riksdag publishes only the statute as in force now; "
                                   "a past date cannot be selected")
        client = RiksdagenClient(download_dir=download_dir)
        path = client.download(doc_id)
        document = client.metadata(doc_id) if metadata else {}
        issued = (document.get('datum') or '')[:10] or None
        return Retrieval(
            path=path,
            parser='se-sfs',
            parser_options={'date': date or today},
            version=CONSOLIDATED,
            language='swe',
            version_date=date or today,
            meta={
                'date_document': issued,
                'source': f'{RIKSDAGEN}/dokument/{doc_id}.html',
            },
        )
