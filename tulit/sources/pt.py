"""
Portugal: Diário da República (official gazette).

Acts are addressed by their ELI, which includes the publication date, or by
their citation ('Lei n.º 58/2019, de 8 de agosto'). The text is read from
the PDF of the gazette, so Portugal needs the ``pdf`` extra; consolidated
texts are published only as a JavaScript application.
"""
import re
from typing import Any, Optional

from tulit.client.state.portugal import PortugalDREClient
from tulit.parser.exceptions import FileLoadError, UnsupportedError
from tulit.sources.base import ORIGINAL, Retrieval, Source

DRE_ELI = 'https://data.dre.pt/eli'
MONTHS = ('janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro',
          'outubro', 'novembro', 'dezembro')
TYPES = {'lei': 'lei', 'decreto-lei': 'dec-lei', 'lei orgânica': 'leiorg', 'lei constitucional': 'leiconst',
         'portaria': 'port'}
_ELI = re.compile(r'(?:^|eli/)(?P<type>[a-z][a-z\-]*)/(?P<number>[\w\-]+)/(?P<year>\d{4})/(?P<month>\d{2})/'
                  r'(?P<day>\d{2})(?:/(?P<region>[pma]))?(?:/|$)')
_CITATION = re.compile(r'^(?P<type>Lei(?: Orgânica| Constitucional)?|Decreto-Lei|Portaria)\s+n\.[ºo°]\s*'
                       r'(?P<number>[\w\-]+)/(?P<year>\d{4}|\d{2})(?:/\d+)?,?\s+'
                       r'de\s+(?P<day>\d{1,2})\s+de\s+(?P<month>\w+)$', re.IGNORECASE)


def act_reference(identifier: str) -> dict[str, str]:
    """'Lei n.º 58/2019, de 8 de agosto', 'lei/58/2019/08/08' or an ELI -> the parts of its ELI."""
    text = identifier.strip()
    match = _ELI.search(text)
    if match:
        parts = match.groupdict()
        parts['region'] = parts['region'] or 'p'
        return parts
    match = _CITATION.match(text)
    if match and match.group('month').lower() in MONTHS:
        year = match.group('year')
        if len(year) == 2:  # 'Lei n.º 67/98'
            year = f"{'19' if int(year) >= 50 else '20'}{year}"
        return {'type': TYPES[match.group('type').lower()], 'number': match.group('number'),
                'year': year, 'month': f"{MONTHS.index(match.group('month').lower()) + 1:02d}",
                'day': f"{int(match.group('day')):02d}", 'region': 'p'}
    raise UnsupportedError(f"'{identifier}' is not a Portuguese act reference; use its ELI or a citation such as "
                     f"'Lei n.º 58/2019, de 8 de agosto'")


class PortugalSource(Source):
    code = 'PT'
    name = 'Portugal'
    source_name = 'Diário da República (Imprensa Nacional-Casa da Moeda)'
    versions = (ORIGINAL,)
    languages = ('por',)
    identifier_help = ("the citation of an act with its date (e.g. 'Lei n.º 58/2019, de 8 de agosto'; laws, "
                       "organic and constitutional laws, decree-laws and portarias) "
                       "or its ELI (https://data.dre.pt/eli/lei/58/2019/08/08/p/dre/pt/html)")
    eli_patterns = (re.compile(r'^(?P<id>https?://data\.dre\.pt/eli/[a-z\-]+/[\w\-]+/\d{4}/\d{2}/\d{2}/[pma])(/.*)?$'),)

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
        if date:
            raise UnsupportedError("Diário da República acts are retrieved as published; a date cannot be selected")
        parts = act_reference(identifier)
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
