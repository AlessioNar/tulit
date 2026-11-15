"""
Italy: Normattiva (Istituto Poligrafico e Zecca dello Stato).

Normattiva exports state legislation as Akoma Ntoso as in force on any
date. The original version is its export for the date of publication in the
Gazzetta Ufficiale, which it labels as the original text; the consolidated
version is the text in force today or on a date.
"""
import datetime
import re
from typing import Any, Optional

from lxml import etree

from tulit.client.state.italy import NORMATTIVA, NormattivaAKNClient
from tulit.parser.exceptions import FileLoadError, UnsupportedError
from tulit.sources.base import CONSOLIDATED, ORIGINAL, Retrieval, Source

MONTHS = ('gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio', 'agosto', 'settembre',
          'ottobre', 'novembre', 'dicembre')
# Kinds of act: their names and abbreviations, and their URN name
KINDS = (
    (r'decreto[ -]legislativo|d\.\s?lgs\.?|dlgs', 'decreto.legislativo'),
    (r'decreto[ -]legge|d\.\s?l\.', 'decreto.legge'),
    (r'decreto del presidente della repubblica|d\.\s?p\.\s?r\.?|dpr', 'decreto.del.presidente.della.repubblica'),
    (r'decreto del presidente del consiglio dei ministri|d\.\s?p\.\s?c\.\s?m\.?|dpcm',
     'decreto.del.presidente.del.consiglio.dei.ministri'),
    (r'legge costituzionale|l\.\s?cost\.', 'legge.costituzionale'),
    (r'regio decreto|r\.\s?d\.', 'regio.decreto'),
    (r'legge|l\.', 'legge'),
)
_KIND = '|'.join(f'(?:{pattern})' for pattern, _ in KINDS)
# 'decreto legislativo 10 agosto 2018, n. 101'
_LONG = re.compile(rf'^(?P<kind>{_KIND})\s+(?P<day>\d{{1,2}})[°º]?\s+(?P<month>[a-z]+)\s+(?P<year>\d{{4}}),?\s*'
                   r'n\.?\s*(?P<number>\d+)$', re.IGNORECASE)
# 'D.Lgs. 101/2018', 'legge n. 160/2019'
_SHORT = re.compile(rf'^(?P<kind>{_KIND})\s*(?:n\.\s*)?(?P<number>\d+)\s*/\s*(?P<year>\d{{4}})$', re.IGNORECASE)
_URN = re.compile(r'(urn:nir:[^\s&#]+)')
_ELI = re.compile(r'^https?://www\.(?:normattiva|gazzettaufficiale)\.it/eli/id/(?P<year>\d{4})/(?P<month>\d{2})/'
                  r'(?P<day>\d{2})/(?P<code>\w+)')
_GU = re.compile(r'^(?P<date>\d{4}-\d{2}-\d{2})/(?P<code>\d{2,3}[A-Z]\d{4,5})$')


def _urn_kind(kind: str) -> str:
    for pattern, name in KINDS:
        if re.fullmatch(pattern, kind.strip(), re.IGNORECASE):
            return name
    raise UnsupportedError(f"'{kind}' is not a kind of act Normattiva knows")


def act_reference(identifier: str) -> dict[str, str]:
    """
    A URN ({'urn': ...}) or Gazzetta Ufficiale date and code ({'date': ..., 'code': ...}) for an act.

    Accepts a URN, a Normattiva or Gazzetta Ufficiale link, a citation ('decreto legislativo 10 agosto 2018,
    n. 101', 'D.Lgs. 101/2018', 'legge 27 dicembre 2019, n. 160'), 'Costituzione', or the date and code of
    publication ('2018-09-04/18G00129').
    """
    text = ' '.join(identifier.strip().split())
    match = _URN.search(text)
    if match:
        return {'urn': match.group(1)}
    match = _ELI.match(text)
    if match:
        return {'date': f"{match.group('year')}-{match.group('month')}-{match.group('day')}",
                'code': match.group('code')}
    match = _GU.match(text)
    if match:
        return {'date': match.group('date'), 'code': match.group('code')}
    if text.lower() in ('costituzione', 'costituzione della repubblica italiana'):
        return {'urn': 'urn:nir:stato:costituzione:1947-12-27'}
    match = _LONG.match(text)
    if match:
        if match.group('month').lower() not in MONTHS:
            raise UnsupportedError(f"'{identifier}': unknown month '{match.group('month')}'")
        date = datetime.date(int(match.group('year')), MONTHS.index(match.group('month').lower()) + 1,
                             int(match.group('day')))
        return {'urn': f"urn:nir:stato:{_urn_kind(match.group('kind'))}:{date.isoformat()};{match.group('number')}"}
    match = _SHORT.match(text)
    if match:
        return {'urn': f"urn:nir:stato:{_urn_kind(match.group('kind'))}:{match.group('year')};{match.group('number')}"}
    raise UnsupportedError(f"'{identifier}' is not an Italian act reference; use {ItalySource.identifier_help}")


def _expression_date(path: str) -> Optional[str]:
    """
    The date the exported text is in force from: the date of its ELI alias ('.../CONSOLIDATED/20260812'),
    else the FRBRExpression date (which, for a code annexed to its decree, stays the decree's).
    """
    root = etree.parse(path).getroot()
    for alias in root.xpath('//*[local-name()="FRBRWork"]/*[local-name()="FRBRalias"][@name="eli"]/@value'):
        match = re.search(r'/CONSOLIDATED/(\d{4})(\d{2})(\d{2})$', alias)
        if match:
            return '-'.join(match.groups())
    found = root.xpath('//*[local-name()="FRBRExpression"]/*[local-name()="FRBRdate"]/@date')
    return found[0] if found else None


def _check_kind(urn: str, title: Optional[str]) -> None:
    """Normattiva answers a URN naming no act with another act of that year and number: refuse it."""
    kind = urn.split(':')[3] if urn.count(':') >= 4 else ''
    if not title or kind in ('', 'costituzione'):
        return
    expected = kind.replace('.', ' ')
    if not ' '.join(title.lower().replace('-', ' ').split()).startswith(expected):
        raise FileLoadError(f"Normattiva has no act {urn} (it answered with '{title}')")


class ItalySource(Source):
    code = 'IT'
    name = 'Italy'
    source_name = 'Normattiva (Istituto Poligrafico e Zecca dello Stato)'
    versions = (ORIGINAL, CONSOLIDATED)
    languages = ('ita',)
    identifier_help = ("a citation ('decreto legislativo 10 agosto 2018, n. 101', 'D.Lgs. 101/2018', "
                       "'L. 160/2019'), a URN ('urn:nir:stato:decreto.legislativo:2018-08-10;101'), a Normattiva "
                       "or Gazzetta Ufficiale link, or the Gazzetta Ufficiale date and code ('2018-09-04/18G00129')")
    eli_patterns = (
        re.compile(r'^(?P<id>https?://www\.(?:normattiva|gazzettaufficiale)\.it/eli/id/\d{4}/\d{2}/\d{2}/\w+)(/.*)?$'),
        re.compile(r'^(?P<id>https?://www\.normattiva\.it/uri-res/N2Ls\?urn:nir:.+)$'),
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
        reference = act_reference(identifier)
        client = NormattivaAKNClient(download_dir=download_dir)
        if 'urn' in reference:
            found = client.resolve(reference['urn'])
            _check_kind(reference['urn'], found.get('title'))
            published, code = found['date'], found['code']
        else:
            published, code = reference['date'], reference['code']
            client.open_act(published, code)
        meta: dict[str, Any] = {'eli': client.gazzetta_eli(published, code), 'date_publication': published,
                                'gazzetta_code': code}
        if 'urn' in reference:
            meta['urn'] = reference['urn']

        if version == ORIGINAL:
            if date:
                raise UnsupportedError("A date selects a consolidated version; the original version has none")
            path = client.download(published, code, published)
            meta['source'] = f"{NORMATTIVA}/eli/id/{published.replace('-', '/')}/{code}/ORIGINAL"
            return Retrieval(path=path, parser='it-normattiva', version=ORIGINAL, language='ita',
                             version_date=published, meta=meta)

        target = date or datetime.date.today().isoformat()
        datetime.date.fromisoformat(target)
        if target < published:
            raise FileLoadError(f"{identifier} was published on {published}, after {target}")
        path = client.download(published, code, target)
        meta['source'] = f"{NORMATTIVA}/eli/id/{published.replace('-', '/')}/{code}/CONSOLIDATED"
        return Retrieval(path=path, parser='it-normattiva', version=CONSOLIDATED, language='ita',
                         version_date=_expression_date(path), meta=meta)
