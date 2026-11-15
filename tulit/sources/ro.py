"""
Romania: Portal Legislativ (Ministry of Justice).

The Ministry of Justice's legislation database gives each act as published
in Monitorul Oficial, Part I (its basic form); its web service, which tulit
uses, does not give the consolidated forms, so only the original version is
available.
"""
import re
from typing import Any, Optional

from tulit.client.state.romania import PortalLegislativClient
from tulit.sources.base import ORIGINAL, Retrieval, Source

# Citation forms of each type of act, as the database names the type
KINDS = (
    (r'(?:Ordonan[țţ]a de urgen[țţ][ăa](?: a Guvernului)?|O\.?U\.?G\.?)', 'ORDONANȚĂ DE URGENȚĂ'),
    (r'(?:Ordonan[țţ]a(?: Guvernului)?|O\.?G\.?)', 'ORDONANȚĂ'),
    (r'(?:Hot[ăa]r[âa]rea(?: Guvernului)?|H\.?G\.?)', 'HOTĂRÂRE'),
    (r'(?:Legea|Lege)', 'LEGE'),
    (r'(?:Decretul|Decret)', 'DECRET'),
    (r'(?:Ordinul|Ordin)', 'ORDIN'),
    (r'(?:Decizia|Decizie)', 'DECIZIE'),
)
_CITATION = re.compile(r'^(?P<kind>.+?)\s+(?:nr\.?\s*)?(?P<number>\d+)\s*'
                       r'(?:/\s*(?P<year>\d{4})|\s+din\s+.*?(?P<year2>\d{4}))'
                       r'\s*$', re.IGNORECASE)


_CONSTITUTION = re.compile(r'^Constitu[țţt]ia(?: Rom[âa]niei)?(?: din (?:\d{1,2} \w+ )?(?P<year>\d{4}))?$',
                           re.IGNORECASE)


def act_reference(identifier: str) -> tuple[str, str, str]:
    """
    'Legea nr. 190/2018', 'OUG 57/2019', 'HG nr. 677 din 21 septembrie 2017' -> ('LEGE', '190', '2018');
    'Constituția' (of 1991, or 'Constituția din 1923') -> ('CONSTITUȚIE', '0', '1991').
    """
    constitution = _CONSTITUTION.match(' '.join(identifier.split()))
    if constitution:
        return 'CONSTITUȚIE', '0', constitution.group('year') or '1991'
    match = _CITATION.match(' '.join(identifier.split()))
    if match:
        for pattern, kind in KINDS:
            if re.fullmatch(pattern, match.group('kind'), re.IGNORECASE):
                return kind, match.group('number'), match.group('year') or match.group('year2')
    raise ValueError(f"'{identifier}' is not a citation of a Romanian act; use {RomaniaSource.identifier_help}")


class RomaniaSource(Source):
    code = 'RO'
    name = 'Romania'
    source_name = 'Portal Legislativ (Ministry of Justice)'
    versions = (ORIGINAL,)
    languages = ('ron',)
    identifier_help = ("the citation of an act: its type, number and year, e.g. 'Legea nr. 190/2018', "
                       "'OUG nr. 57/2019', 'Ordonanța nr. 1/2016', 'HG nr. 677/2017', or 'Constituția'")

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
            raise ValueError("The Portal Legislativ web service gives acts as published; a date cannot be selected")
        kind, number, year = act_reference(identifier)
        client = PortalLegislativClient(download_dir=download_dir)
        path = client.download(kind, number, year, title='Constitutia' if kind == 'CONSTITUȚIE' else '')
        found = client.metadata(path)
        return Retrieval(
            path=path,
            parser='ro-legislatie',
            version=ORIGINAL,
            language='ron',
            version_date=found.get('date_document'),
            meta={key: value for key, value in found.items() if value},
        )
