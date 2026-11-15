"""
Romania: Portal Legislativ (Ministry of Justice).

The Ministry of Justice's legislation database gives each act as published
in Monitorul Oficial, Part I (its basic form), through its web service, and
its consolidated forms ("forma consolidată", including the official
republications) on the portal's pages, each with the date it applies from.
The original version comes from the web service; the consolidated version
is the form in force on a date (today by default), from the pages.
"""
import datetime
import re
import unicodedata
from typing import Any, Optional

from tulit.client.state.romania import PORTAL, PortalLegislativClient, act_forms, document_id, shown_form
from tulit.sources.base import CONSOLIDATED, ORIGINAL, Retrieval, Source
from tulit.parser.exceptions import FileLoadError, UnsupportedError

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

# The codes, by name (without diacritics, lower case). The database keeps the text of most codes as a
# document of its own ('CODUL CIVIL din 17 iulie 2009 (Legea nr. 287/2009)'), which its consolidated forms
# follow; the Labour and Administrative Codes are the acts that adopted them.
CODES = {
    'codul civil': ('CODUL CIVIL', '0', '2009'),
    'codul penal': ('CODUL PENAL', '0', '2009'),
    'codul de procedura civila': ('CODUL DE PROCEDURĂ CIVILĂ', '0', '2010'),
    'codul de procedura penala': ('CODUL DE PROCEDURĂ PENALĂ', '0', '2010'),
    'codul fiscal': ('CODUL FISCAL', '0', '2015'),
    'codul de procedura fiscala': ('CODUL DE PROCEDURĂ FISCALĂ', '0', '2015'),
    'codul muncii': ('LEGE', '53', '2003'),
    'codul administrativ': ('ORDONANȚĂ DE URGENȚĂ', '57', '2019'),
}


def _plain(text: str) -> str:
    """Lower case without diacritics: 'Codul de procedură civilă' -> 'codul de procedura civila'."""
    return ' '.join(unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().lower().split())


def act_reference(identifier: str) -> tuple[str, str, str]:
    """
    'Legea nr. 190/2018', 'OUG 57/2019', 'HG nr. 677 din 21 septembrie 2017' -> ('LEGE', '190', '2018');
    'Constituția' (of 1991, or 'Constituția din 1923') -> ('CONSTITUȚIE', '0', '1991');
    'Codul civil' -> ('CODUL CIVIL', '0', '2009').
    """
    constitution = _CONSTITUTION.match(' '.join(identifier.split()))
    if constitution:
        return 'CONSTITUȚIE', '0', constitution.group('year') or '1991'
    code = CODES.get(_plain(identifier))
    if code:
        return code
    match = _CITATION.match(' '.join(identifier.split()))
    if match:
        for pattern, kind in KINDS:
            if re.fullmatch(pattern, match.group('kind'), re.IGNORECASE):
                return kind, match.group('number'), match.group('year') or match.group('year2')
    raise UnsupportedError(f"'{identifier}' is not a citation of a Romanian act; use {RomaniaSource.identifier_help}")


def choose_form(forms: list[dict[str, Any]], date: str) -> Optional[dict[str, Any]]:
    """
    The form in force on a date: the latest one applying from that date or earlier; None before the first.

    A republication and a consolidation of the same day: the consolidation, which adds the changes in force
    that day to the republished text.
    """
    applicable = [form for form in forms if form['date'] <= date]
    return max(applicable, key=lambda form: (form['date'], form['kind'] == 'consolidation')) if applicable else None


class RomaniaSource(Source):
    code = 'RO'
    name = 'Romania'
    source_name = 'Portal Legislativ (Ministry of Justice)'
    versions = (ORIGINAL, CONSOLIDATED)
    languages = ('ron',)
    identifier_help = ("the citation of an act: its type, number and year, e.g. 'Legea nr. 190/2018', "
                       "'OUG nr. 57/2019', 'Ordonanța nr. 1/2016', 'HG nr. 677/2017', 'Constituția', or the "
                       "name of a code ('Codul civil', 'Codul penal', 'Codul de procedură civilă', ...); "
                       "version='consolidated' gives the form in force on a date (default today)")

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
        kind, number, year = act_reference(identifier)
        client = PortalLegislativClient(download_dir=download_dir)
        # An act without a number is searched by words of its title
        title = ('Constitutia' if kind == 'CONSTITUȚIE' else _plain(kind)) if number == '0' else ''
        if version == CONSOLIDATED:
            return self._consolidated(client, identifier, kind, number, year, title, date)
        if date:
            raise UnsupportedError("A date selects a consolidated version; the original version has none")
        path = client.download(kind, number, year, title=title)
        found = client.metadata(path)
        return Retrieval(
            path=path,
            parser='ro-legislatie',
            version=ORIGINAL,
            language='ron',
            version_date=found.get('date_document'),
            meta={key: value for key, value in found.items() if value},
        )

    @staticmethod
    def _consolidated(client: PortalLegislativClient, identifier: str, kind: str, number: str, year: str,
                      title: str, date: Optional[str]) -> Retrieval:
        target = date or datetime.date.today().isoformat()
        try:
            datetime.date.fromisoformat(target)
        except ValueError:
            raise UnsupportedError(f"'{date}' is not an ISO date (YYYY-MM-DD)") from None
        record = client.download(kind, number, year, title=title)
        found = client.metadata(record)
        in_force = found.get('date_in_force')
        if in_force and target < in_force:
            raise FileLoadError(f"{identifier} enters into force on {in_force}, after {target}")

        # The act's page shows its latest form and lists all of them
        base = document_id(record)
        page = client.download_page(f'{PORTAL}/{base}')
        with open(page, encoding='utf-8') as f:
            html = f.read()
        forms = act_forms(html)
        chosen = choose_form(forms, target)
        if chosen is not None:
            reuse = chosen['id'] == shown_form(html) and '?' not in chosen['url']
            path = page if reuse else client.download_page(chosen['url'])
            form, start, source = chosen['kind'], chosen['date'], chosen['url']
        elif forms:
            # Before its first consolidation the act is in force as published
            source = f'{PORTAL}/{base}?isFormaDeBaza=True'
            path, form, start = client.download_page(source), 'base', in_force or found.get('date_publication')
        else:
            # Never consolidated: the page shows the act as published
            path, form, start, source = page, 'base', in_force or found.get('date_publication'), f'{PORTAL}/{base}'
        meta = {key: value for key, value in found.items() if value}
        meta.update(source=source, form=form)
        return Retrieval(
            path=path,
            parser='ro-legislatie-html',
            version=CONSOLIDATED,
            language='ron',
            version_date=start,
            meta=meta,
        )
