"""
Greece: Government Gazette (Εφημερίδα της Κυβερνήσεως, National Printing House).

Laws, presidential decrees and acts of legislative content are published in
Part A (Τεύχος Α΄) of the Government Gazette; that publication is the
official text. Greece publishes no official consolidated texts, so only the
original is available.
"""
import re
from typing import Any, Optional

from tulit.client.state.greece import STORAGE, GovernmentGazetteClient, pdf_url
from tulit.sources.base import ORIGINAL, Retrieval, Source

_LETTERS = {'A': 'Α', 'B': 'Β', 'Γ': 'Γ', 'Δ': 'Δ', 'Α': 'Α', 'Β': 'Β'}
_ACT = re.compile(r'^(?:(?P<kind>ν\.?|n\.?|νόμος|νομος|law|π\.?\s?δ\.?|p\.?d\.?|προεδρικό διάταγμα)\s*)?'
                  r'(?P<number>\d{1,5})\s*/\s*(?P<year>\d{4})$', re.IGNORECASE)
_ISSUE = re.compile(r'^(?:ΦΕΚ\s*)?(?P<part>[ΑAΒBΓΔ])[΄\'’]?\s*(?:\s|-)?\s*(?P<number>\d{1,5})\s*/\s*'
                    r'(?:\d{1,2}[.\-/]\d{1,2}[.\-/])?(?P<year>\d{4})$', re.IGNORECASE)
_PDF = re.compile(r'/fek/(?P<group>\d{2})/(?P<year>\d{4})/\d{4}\d{2}(?P<number>\d{5})\.pdf$')
PART_GROUPS = {'Α': '1', 'Β': '2', 'Γ': '3', 'Δ': '4'}


def reference(identifier: str) -> tuple[str, str, str]:
    """
    What an identifier names: ('law' or 'decree', number, year) for an act, ('issue', 'group/number', year) for an
    issue of the Gazette.

    'ν. 4624/2019', '4624/2019' -> ('law', '4624', '2019'); 'π.δ. 70/2015' -> ('decree', '70', '2015');
    'ΦΕΚ Α 137/29.08.2019', "Α' 137/2019" -> ('issue', '1/137', '2019').
    """
    text = ' '.join(identifier.strip().split())
    match = _PDF.search(text)
    if match:
        return 'issue', f"{int(match.group('group'))}/{int(match.group('number'))}", match.group('year')
    match = _ISSUE.match(text)
    if match:
        part = _LETTERS.get(match.group('part').upper(), match.group('part').upper())
        return 'issue', f"{PART_GROUPS[part]}/{match.group('number')}", match.group('year')
    match = _ACT.match(text)
    if match:
        kind = (match.group('kind') or 'ν').lower().replace(' ', '')
        decree = kind.startswith(('π', 'p'))
        return ('decree' if decree else 'law'), match.group('number'), match.group('year')
    raise ValueError(f"'{identifier}' is not a Greek act or Gazette reference; use {GreeceSource.identifier_help}")


class GreeceSource(Source):
    code = 'GR'
    name = 'Greece'
    source_name = 'Government Gazette (Εφημερίδα της Κυβερνήσεως, National Printing House)'
    versions = (ORIGINAL,)
    languages = ('ell',)
    options = ('number',)
    identifier_help = ("a law or presidential decree as 'ν. 4624/2019' or 'π.δ. 70/2015', or an issue of Part A "
                       "of the Government Gazette as 'ΦΕΚ Α 137/29.08.2019' (the PDF link of an issue works too)")
    eli_patterns = (re.compile(r'^(?P<id>' + re.escape(STORAGE) + r'/\d{2}/\d{4}/\d{11}\.pdf)$'),)

    def retrieve(
        self,
        identifier: str,
        version: str,
        date: Optional[str],
        language: Optional[str],
        download_dir: str,
        metadata: bool = True,
        number: Optional[str] = None,
        **options: Any,
    ) -> Retrieval:
        if date:
            raise ValueError("The Government Gazette publishes acts as adopted; a date cannot be selected")
        kind, act, year = reference(identifier)
        client = GovernmentGazetteClient(download_dir=download_dir)
        if kind == 'issue':
            part, issue_number = act.split('/')
            if metadata:
                issue = client.find_issue(part, issue_number, year)
            else:
                issue = {'part': part, 'issue': issue_number}
        else:
            issue = client.find_act(kind, act, year)
            # A decree shares its issue with others: the parser picks it by its number
            number = number or act
        path = client.download(issue, year)
        meta = {
            'source': pdf_url(issue['part'], issue['issue'], year),
            'gazette_issue': issue.get('label') or f"{issue['issue']}/{year}",
            'date_document': issue.get('date_document'),
            'date_publication': issue.get('date_publication'),
            'title': issue.get('title'),
        }
        return Retrieval(
            path=path,
            parser='gr-fek-pdf',
            parser_options={'number': str(number)} if number else {},
            version=ORIGINAL,
            language='ell',
            version_date=issue.get('date_publication'),
            meta={key: value for key, value in meta.items() if value},
        )
