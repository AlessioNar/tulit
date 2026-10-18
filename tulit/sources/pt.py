"""
Portugal: Diário da República (official gazette) and its consolidated legislation.

Acts as published are addressed by their ELI, which includes the publication
date, or by their citation ('Lei n.º 58/2019, de 8 de agosto'); the text is
read from the PDF of the gazette, so originals need the ``pdf`` extra.

Consolidated texts come from the Legislação Consolidada of the Diário da
República, which consolidates a selection of acts: the codes, the
Constitution and frequently amended laws. They are addressed by the act's
citation (the date may be left out: 'Lei n.º 7/2009'), its ELI, its
consolidated ELI (``.../lei/7/2009/p/cons/20250327/pt/html``), the address of
its page (``https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2009-34546475``)
or, for the codes listed under 'Legislação por código', their name
('Código Penal'). A date selects the version in force on that date.
"""
import datetime
import json
import re
import unicodedata
from typing import Any, Optional

from tulit.client.state.portugal import PortugalConsolidatedClient, PortugalDREClient, consolidated_page
from tulit.parser.exceptions import FileLoadError, UnsupportedError
from tulit.sources.base import CONSOLIDATED, ORIGINAL, Retrieval, Source

DRE_ELI = 'https://data.dre.pt/eli'
MONTHS = ('janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro',
          'outubro', 'novembro', 'dezembro')
TYPES = {'lei': 'lei', 'decreto-lei': 'dec-lei', 'lei orgânica': 'leiorg', 'lei constitucional': 'leiconst',
         'portaria': 'port'}
REPEALED = 4
_ELI = re.compile(r'(?:^|eli/)(?P<type>[a-z][a-z\-]*)/(?P<number>[\w\-]+)/(?P<year>\d{4})/(?P<month>\d{2})/'
                  r'(?P<day>\d{2})(?:/(?P<region>[pma]))?(?:/|$)')
# A consolidated version: lei/7/2009/p/cons/20250327[/pt/html]
_CONS_ELI = re.compile(r'(?:^|eli/)(?P<type>[a-z][a-z\-]*)/(?P<number>[\w\-]+)/(?P<year>\d{4})/(?P<region>[pma])/'
                       r'cons/(?P<cons>\d{8})(?:/|$)')
_CITATION = re.compile(r'^(?P<type>Lei(?: Orgânica| Constitucional)?|Decreto-Lei|Portaria)\s+n\.[ºo°]\s*'
                       r'(?P<number>[\w\-]+)/(?P<year>\d{4}|\d{2})(?:/\d+)?'
                       r'(?:,?\s+de\s+(?P<day>\d{1,2})\s+de\s+(?P<month>\w+))?$', re.IGNORECASE)


def act_reference(identifier: str) -> dict[str, Optional[str]]:
    """
    'Lei n.º 58/2019, de 8 de agosto', 'lei/58/2019/08/08' or an ELI -> the parts of its ELI.

    A citation without its date ('Lei n.º 7/2009') or a consolidated ELI gives no month and day;
    a consolidated ELI gives its consolidation date as 'cons'.
    """
    text = identifier.strip()
    match = _ELI.search(text)
    if match:
        parts = match.groupdict()
        parts['region'] = parts['region'] or 'p'
        return parts
    match = _CONS_ELI.search(text)
    if match:
        parts = match.groupdict()
        parts.update(month=None, day=None)
        return parts
    match = _CITATION.match(text)
    if match and (match.group('month') is None or match.group('month').lower() in MONTHS):
        year = match.group('year')
        if len(year) == 2:  # 'Lei n.º 67/98'
            year = f"{'19' if int(year) >= 50 else '20'}{year}"
        month = match.group('month')
        return {'type': TYPES[match.group('type').lower()], 'number': match.group('number'), 'year': year,
                'month': f"{MONTHS.index(month.lower()) + 1:02d}" if month else None,
                'day': f"{int(match.group('day')):02d}" if month else None, 'region': 'p'}
    raise UnsupportedError(f"'{identifier}' is not a Portuguese act reference; use its ELI or a citation such as "
                           f"'Lei n.º 58/2019, de 8 de agosto'")


def _folded(text: str) -> str:
    """Case and accents folded: 'Código  Penal' -> 'codigo penal'."""
    decomposed = unicodedata.normalize('NFKD', text.casefold())
    return ' '.join(''.join(c for c in decomposed if not unicodedata.combining(c)).split())


def code_page(name: str, codes: list[dict[str, str]]) -> Optional[str]:
    """
    The consolidated page of a code by its name or acronym, from the 'Legislação por código' list.

    'Código Penal', 'codigo penal' or 'CP' -> '/dr/legislacao-consolidada/decreto-lei/1995-34437675';
    None when no code, or more than one, matches.
    """
    wanted = _folded(name)
    by_name, by_acronym = [], []
    for code in codes:
        designation = code['designation']
        full = _folded(designation)
        title, _, acronym = designation.rpartition(' - ') if ' - ' in designation else (designation, '', '')
        if wanted in (full, _folded(title)):
            by_name.append(code['page'])
        elif acronym and wanted == _folded(acronym):
            by_acronym.append(code['page'])
    for found in (by_name, by_acronym):
        if len(set(found)) == 1:
            return found[0]
    return None


def _fragment_date(fragment: dict[str, Any], key: str) -> Optional[str]:
    """A date of a fragment's version ('DataEntradaVigor', 'DataVersao'); None when unknown (1900-01-01)."""
    value = ((fragment.get('FragmentoVersao') or {}).get(key) or '')[:10]
    return value if re.match(r'^\d{4}-\d{2}-\d{2}$', value) and not value.startswith('1900') else None


def not_in_force(fragments: list[dict[str, Any]], date: str) -> list[dict[str, Any]]:
    """The fragments whose version enters into force after ``date``."""
    return [f for f in fragments if (_fragment_date(f, 'DataEntradaVigor') or '') > date]


def version_date(fragments: list[dict[str, Any]], date: str, published: Optional[str]) -> Optional[str]:
    """
    The date the version in force on ``date`` applies from: the latest entry into force of its fragments
    (or, when a fragment's entry into force is not recorded, the date of its version).
    """
    applied = []
    for fragment in fragments:
        value = _fragment_date(fragment, 'DataEntradaVigor') or _fragment_date(fragment, 'DataVersao')
        if value and value <= date:
            applied.append(value)
    return max(applied) if applied else published


class PortugalSource(Source):
    code = 'PT'
    name = 'Portugal'
    source_name = 'Diário da República (Imprensa Nacional-Casa da Moeda)'
    versions = (ORIGINAL, CONSOLIDATED)
    languages = ('por',)
    identifier_help = ("the citation of an act (e.g. 'Lei n.º 58/2019, de 8 de agosto'; laws, organic and "
                       "constitutional laws, decree-laws and portarias) or its ELI "
                       "(https://data.dre.pt/eli/lei/58/2019/08/08/p/dre/pt/html) for the act as published; "
                       "for the consolidated version (Legislação Consolidada), also a citation without its date "
                       "('Lei n.º 7/2009'), a consolidated ELI (https://data.dre.pt/eli/lei/7/2009/p/cons/"
                       "20250327/pt/html), the address of its page on diariodarepublica.pt or the name of a code "
                       "('Código Penal', 'Código do Trabalho')")
    eli_patterns = (
        re.compile(r'^(?P<id>https?://data\.dre\.pt/eli/[a-z\-]+/[\w\-]+/\d{4}/\d{2}/\d{2}/[pma])(/.*)?$'),
        re.compile(r'^(?P<id>https?://data\.dre\.pt/eli/[a-z\-]+/[\w\-]+/\d{4}/[pma]/cons/\d{8})(/.*)?$'),
        # Not an ELI: the page of a consolidated act
        re.compile(r'^(?P<id>https?://diariodarepublica\.pt/dr/legislacao-consolidada/[a-z\-]+/\d{4}-\d+)'
                   r'(-\d+)?/?$'),
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
        text = identifier.strip()
        page = consolidated_page(text) if 'legislacao-consolidada' in text else None
        parts = None
        if page is None:
            try:
                parts = act_reference(text)
            except UnsupportedError:
                parts = None
        consolidated_client = PortugalConsolidatedClient(download_dir=download_dir)
        if page is None and parts is None:
            # The name of a code ('Código Penal')
            found = code_page(text, consolidated_client.codes())
            if found is None:
                raise UnsupportedError(f"'{identifier}' is not a Portuguese act reference or the name of a code "
                                       f"listed in the Diário da República; use {self.identifier_help}")
            page = consolidated_page(found)
        if version is None:
            # Acts are retrieved as published unless the identifier names a consolidated text or a date is given
            version = CONSOLIDATED if page or date or (parts and parts.get('cons')) else ORIGINAL

        if version == CONSOLIDATED:
            return self._consolidated(consolidated_client, identifier, page, parts, date)

        if date:
            raise UnsupportedError("Diário da República acts are retrieved as published; a date selects "
                                   "a consolidated version (version='consolidated')")
        if parts is None or not parts.get('month'):
            parts = self._published_parts(consolidated_client, identifier, page, parts)
        return self._original(identifier, parts, download_dir, version)

    @staticmethod
    def _original(identifier: str, parts: dict[str, Any], download_dir: str, version: str) -> Retrieval:
        client = PortugalDREClient(download_dir=download_dir)
        path = client.download('legal_act', act_type=parts['type'], number=parts['number'], year=parts['year'],
                               month=parts['month'], day=parts['day'], region=parts['region'], fmt='pdf')
        if path is None:
            raise FileLoadError(f"Diário da República has no PDF for {identifier} (its ELI register starts "
                                f"in the 1990s; older acts are not reachable)")
        eli = (f"{DRE_ELI}/{parts['type']}/{parts['number']}/{parts['year']}/{parts['month']}/{parts['day']}/"
               f"{parts['region']}")
        published = f"{parts['year']}-{parts['month']}-{parts['day']}"
        return Retrieval(
            path=path,
            parser='pt-dre-pdf',
            parser_options={'number': f"{parts['number']}/{parts['year']}"},
            version=version,
            language='por',
            version_date=published,
            meta={
                'eli': eli,
                'date_document': published,
                'source': f'{eli}/dre/pt/pdf',
            },
        )

    @staticmethod
    def _published_parts(client: PortugalConsolidatedClient, identifier: str,
                         page: Optional[tuple[str, str, str]], parts: Optional[dict[str, Any]]) -> dict[str, Any]:
        """The ELI parts of the act as published, for a reference without its date, from its consolidated text."""
        if page is None and parts is not None:
            page = client.resolve_eli(parts['type'], parts['number'], parts['year'], parts['region'])
        if page is None:
            raise UnsupportedError(f"The act as published is addressed by its citation with the date "
                                   f"('Lei n.º 58/2019, de 8 de agosto') or its ELI; '{identifier}' has no date")
        detail = client.diploma(*page)
        legis = detail.get('DiplomaLegis') or {}
        acronym = (detail.get('TipoDiploma') or {}).get('Acronimo') or ''
        number = (legis.get('Numero') or '').split('/')[0].strip()
        published = (legis.get('DataPublicacao') or '')[:10]
        if not (acronym and number and re.match(r'^\d{4}-\d{2}-\d{2}$', published)):
            raise FileLoadError(f"Diário da República gives no publication details for {identifier}")
        year, month, day = published.split('-')
        return {'type': acronym, 'number': number, 'year': year, 'month': month, 'day': day, 'region': 'p'}

    @staticmethod
    def _in_force(client: PortugalConsolidatedClient, page: tuple[str, str, str], date: str,
                  named: bool) -> tuple[str, dict[str, Any]]:
        """
        Download the consolidation in force on ``date``.

        The Diário da República selects a consolidation by the date its amending act was published, so the
        consolidation of a date can hold changes that enter into force later; the one before it is then asked
        for, until every fragment is in force on the date.
        """
        selected = date
        for _ in range(10):
            path = client.download(*page, date=selected)
            with open(path, encoding='utf-8') as f:
                document = json.load(f)
            later = [] if named else not_in_force(document['fragments'], date)
            published = [_fragment_date(f, 'DataVersao') for f in later]
            if not later or None in published:
                break
            earlier = (datetime.date.fromisoformat(min(published)) - datetime.timedelta(days=1)).isoformat()
            if earlier >= selected:
                break
            selected = earlier
        return path, document

    @staticmethod
    def _consolidated(client: PortugalConsolidatedClient, identifier: str, page: Optional[tuple[str, str, str]],
                      parts: Optional[dict[str, Any]], date: Optional[str]) -> Retrieval:
        # A consolidated ELI names one consolidation: it is returned as it is
        named = date is None and bool(parts and parts.get('cons'))
        if named:
            cons = parts['cons']
            date = f'{cons[:4]}-{cons[4:6]}-{cons[6:]}'
        date = date or datetime.date.today().isoformat()
        try:
            datetime.date.fromisoformat(date)
        except ValueError as e:
            raise UnsupportedError(f"'{date}' is not an ISO date (YYYY-MM-DD)") from e
        if page is None and parts is not None:
            page = client.resolve_eli(parts['type'], parts['number'], parts['year'], parts['region'])
            if page is None:
                raise FileLoadError(f"The Diário da República publishes no consolidated version of {identifier} "
                                    f"(it consolidates the codes and a selection of laws); "
                                    f"version='original' gives the act as published")
        path, document = PortugalSource._in_force(client, page, date, named)
        detail = document.get('diploma') or {}
        legis = detail.get('DiplomaLegis') or {}
        published = (legis.get('DataPublicacao') or '')[:10] or None
        if published and date < published:
            raise FileLoadError(f"{identifier} was published on {published}; it has no version in force on {date}")
        applies = version_date(document['fragments'], '9999-12-31' if named else date, published)
        consolidation = document.get('consolidation') or {}
        eli = re.sub(r'/pt/html$', '', (detail.get('DiplomaFrag') or {}).get('ELI') or '')
        if not _CONS_ELI.search(eli):
            eli = None
        elif consolidation.get('CurrentConsolidacaoId') != consolidation.get('LastConsolidacaoId') and applies:
            # An earlier version: the consolidated ELI of the date it applies from
            eli = re.sub(r'/cons/\d{8}$', f"/cons/{applies.replace('-', '')}", eli)
        root = document['fragments'][0].get('FragmentoVersao') or {}
        return Retrieval(
            path=path,
            parser='pt-dre-consolidated',
            version=CONSOLIDATED,
            language='por',
            version_date=applies,
            meta={
                'eli': eli,
                'date_document': published,
                'in_force': root.get('VersaoEstadoId') != REPEALED,
                'source': document.get('page'),
            },
        )
