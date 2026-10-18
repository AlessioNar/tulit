"""
Hungary: Nemzeti Jogszabálytár (National Legislation Database).

The original version is the act as promulgated in the Magyar Közlöny
(közlönyállapot); the consolidated version is the time state in force today
or on a date. Both come from the Nemzeti Jogszabálytár.
"""
import re
from typing import Any, Optional

from tulit.client.state.hungary import NJT, NJTClient
from tulit.parser.exceptions import FileLoadError, UnsupportedError
from tulit.parser.html.njt import _ADOPTED, _PROMULGATED, _hungarian_date, roman
from tulit.sources.base import CONSOLIDATED, ORIGINAL, Retrieval, Source

_LAW = re.compile(r'^(?P<year>\d{4})\.\s*évi\s+(?P<number>[IVXLCDM]+)\.\s*törvény\b', re.IGNORECASE)
_DECREE_LAW = re.compile(r'^(?P<year>\d{4})\.\s*évi\s+(?P<number>\d+)\.\s*törvényerejű rendelet\b', re.IGNORECASE)
_DECREE = re.compile(r'^(?P<number>\d+)/(?P<year>\d{4})\.\s*\([IVXLC]+\.\s*\d{1,2}\.\)\s*(?P<issuer>[\w.\s-]+?)\s*'
                     r'rendelet\b', re.IGNORECASE)
_ID = re.compile(r'^(?:https?://njt\.jog\.gov\.hu/jogszabaly/)?(?P<id>\d{4}-\d+-\d{2}-\d{2})(?:\.\d+)?$')
_ELI = re.compile(r'^(?:https?://njt\.jog\.gov\.hu/eli/)(?P<path>[A-Za-z_]+(?:/[\w]+)*)$')


_CITATION_DATE = re.compile(r'mainTitle">\s*\d+/(?P<year>\d{4})\.\s*\((?P<month>[IVXLC]+)\.\s*(?P<day>\d{1,2})\.\)')


def _citation_date(page: str) -> Optional[str]:
    """The promulgation date in a decree's citation ('21/2016. (X. 11.) IM rendelet' -> '2016-10-11')."""
    match = _CITATION_DATE.search(page)
    if not match:
        return None
    return f"{match.group('year')}-{roman(match.group('month')):02d}-{int(match.group('day')):02d}"


def eli_path(identifier: str) -> Optional[str]:
    """
    The ELI path of a Hungarian citation.

    '2011. évi CXII. törvény' -> 'TV/2011/112'; '335/2005. (XII. 29.) Korm. rendelet' -> 'R/2005/Korm/335';
    '1979. évi 13. törvényerejű rendelet' -> 'TVR/1979/13'; 'Alaptörvény' -> 'Alaptv'.
    """
    text = ' '.join(identifier.split())
    if text.lower() in ('alaptörvény', "magyarország alaptörvénye"):
        return 'Alaptv'
    match = _DECREE_LAW.match(text)
    if match:
        return f"TVR/{match.group('year')}/{match.group('number')}"
    match = _LAW.match(text)
    if match:
        return f"TV/{match.group('year')}/{roman(match.group('number').upper())}"
    match = _DECREE.match(text)
    if match:
        issuer = match.group('issuer').strip().rstrip('.').replace(' ', '_')
        return f"R/{match.group('year')}/{issuer}/{match.group('number')}"
    return None


class HungarySource(Source):
    code = 'HU'
    name = 'Hungary'
    source_name = 'Nemzeti Jogszabálytár (Ministry of Justice)'
    versions = (ORIGINAL, CONSOLIDATED)
    languages = ('hun',)
    identifier_help = ("a citation ('2011. évi CXII. törvény', '335/2005. (XII. 29.) Korm. rendelet'), an NJT id "
                       "('2011-112-00-00') or link, or an ELI ('https://njt.jog.gov.hu/eli/TV/2011/112')")
    eli_patterns = (
        re.compile(r'^(?P<id>https?://njt\.jog\.gov\.hu/eli/[A-Za-z_]+(?:/[\w]+)*)$'),
        re.compile(r'^(?P<id>https?://njt\.jog\.gov\.hu/jogszabaly/\d{4}-\d+-\d{2}-\d{2})(\.\d+)?$'),
    )

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
        client = NJTClient(download_dir=download_dir)
        text = identifier.strip()
        found = _ID.match(text)
        if found:
            document_id = found.group('id')
        else:
            eli = _ELI.match(text)
            path = eli.group('path') if eli else eli_path(text)
            if path is None:
                raise UnsupportedError(f"'{identifier}' is not a Hungarian act reference; use {self.identifier_help}")
            # A date or 'kozlony' at the end of an ELI selects a version; the request decides here
            path = re.sub(r'/(kozlony|\d{4}-\d{2}-\d{2})$', '', path)
            document_id, _ = client.resolve(path)

        if version == ORIGINAL:
            if date:
                raise UnsupportedError("A date selects a consolidated version; the original version has none")
            path = client.download(document_id, 0)
            version_date = None
        else:
            versions = client.versions(document_id)
            chosen = client.in_force(versions, date)
            if chosen is None:
                first = next((v['from'] for v in versions if v['from']), None)
                raise FileLoadError(f"No time state of {identifier} is in force on {date or 'today'}"
                                    + (f"; the first came into force on {first}" if first else ''))
            path = client.download(document_id, chosen['version'])
            version_date = chosen['from']
        with open(path, encoding='utf-8', errors='replace') as f:
            page = f.read()
        promulgated = _hungarian_date(_PROMULGATED.search(page)) or _citation_date(page)
        version_date = version_date or promulgated
        meta = {'eli': client.eli(path), 'source': f'{NJT}/jogszabaly/{document_id}', 'njt_id': document_id,
                'date_document': _hungarian_date(_ADOPTED.search(page)), 'date_publication': promulgated}
        return Retrieval(path=path, parser='hu-njt', version=version, language='hun', version_date=version_date,
                         meta={key: value for key, value in meta.items() if value})
