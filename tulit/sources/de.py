"""
Germany: federal law, consolidated from Rechtsinformationen des Bundes (the
federal legal information portal, test phase) and as promulgated in the
Federal Law Gazette (Bundesgesetzblatt, BGBl.).

The consolidated version in force is addressed by its ELI
('eli/bund/bgbl-1/2009/s2704'), the act as promulgated by its Gazette
citation: 'BGBl. 2024 I Nr. 149' since 2023, when the Gazette went
electronic on recht.bund.de (PDF only), and 'BGBl. 2017 I S. 2097' (year,
part and first page) for the printed issues of 1949-2022, from the bgbl.de
archive. Issues of the archive from before about 1998 are scanned images
without text: ``tulit.download`` returns their PDF.
"""
import re
from typing import Any, Optional

from tulit.client.state.germany import GermanyClient
from tulit.client.state.germany_bgbl import (BundesgesetzblattClient, archive_name, archive_url,
                                             promulgation_url)
from tulit.parser.exceptions import FileLoadError, UnsupportedError
from tulit.parser.pdf.layout import has_text
from tulit.sources.base import CONSOLIDATED, ORIGINAL, Retrieval, Source

PORTAL = 'https://testphase.rechtsinformationen.bund.de'
ELECTRONIC = 2023
"""First year of the electronic Gazette, whose promulgations are numbered rather than paged."""

_WORK = re.compile(r'(eli/bund/([\w-]+)/(\d{4})/([\w-]+))', re.IGNORECASE)
_CITATION = re.compile(
    r'^BGBl\.?\s*(?:(?P<year>\d{4})\s+)?(?P<part>I{1,2}|[12])\.?\s*,?\s*(?:(?P<year2>\d{4})\s*,?\s*)?'
    r'(?:Nr\.?\s*(?P<number>\d+[a-z]?)|S(?:\.|eite)?\s*(?P<page>\d+[a-z]?))'
    r'(?:\s*\(\s*(?P<year3>\d{4})\s*\)|\s*,?\s*(?P<year4>\d{4}))?$', re.IGNORECASE)
_GAZETTE_ELI = re.compile(r'eli/bund/bgbl[-_]?(?P<part>[12])/(?P<year>\d{4})/(?P<id>s?\d+[a-z]?)(?:/|$)',
                          re.IGNORECASE)
_PROMULGATION_PAGE = re.compile(r'recht\.bund\.de/bgbl/(?P<part>[12])/(?P<year>\d{4})/(?P<number>\d+[a-z]?)/',
                                re.IGNORECASE)
_ARCHIVE_NAME = re.compile(r'bgbl(?P<part>[12])(?P<year>\d{2})s(?P<page>\d+[a-z]?)\.pdf', re.IGNORECASE)


def work_eli(identifier: str) -> str:
    """'eli/bund/bgbl-1/2009/s2704', a portal URL or an expression ELI -> 'eli/bund/bgbl-1/2009/s2704'."""
    match = _WORK.search(identifier)
    if not match:
        reference = gazette_reference(identifier)
        if reference:
            return reference_eli(reference)
        raise UnsupportedError(
            f"'{identifier}' is not a German federal ELI; use e.g. 'eli/bund/bgbl-1/2009/s2704'")
    # recht.bund.de also writes 'BGBl-1' and, until 2024, 'BGBl_1'
    agent = match.group(2).lower().replace('_', '-')
    return f'eli/bund/{agent}/{match.group(3)}/{match.group(4)}'


def gazette_reference(identifier: str) -> Optional[dict[str, str]]:
    """
    The Federal Law Gazette promulgation an identifier names, or None.

    'BGBl. 2024 I Nr. 149' -> {'part': '1', 'year': '2024', 'number': '149'};
    'BGBl. 2017 I S. 2097', 'BGBl. I 2017 S. 2097', 'eli/bund/bgbl-1/2017/s2097'
    -> {'part': '1', 'year': '2017', 'page': '2097'}; recht.bund.de and
    bgbl.de links work too. A citation without its year is rejected.
    """
    text = ' '.join(identifier.strip().split())
    match = _CITATION.match(text)
    if match:
        part = '2' if match.group('part').upper() in ('II', '2') else '1'
        year = next((match.group(g) for g in ('year', 'year2', 'year3', 'year4') if match.group(g)), None)
        if year is None:
            raise UnsupportedError(f"'{identifier}' gives no year; cite the Federal Law Gazette with it, "
                                   f"e.g. 'BGBl. 2017 I S. 2097' or 'BGBl. 2024 I Nr. 149'")
        if match.group('number'):
            return {'part': part, 'year': year, 'number': match.group('number').lower()}
        return {'part': part, 'year': year, 'page': match.group('page').lower()}
    match = _PROMULGATION_PAGE.search(text)
    if match:
        return {'part': match.group('part'), 'year': match.group('year'), 'number': match.group('number').lower()}
    match = _ARCHIVE_NAME.search(text)
    if match and 'bgbl.de' in text.lower():
        yy = int(match.group('year'))
        year = str(1900 + yy if yy >= 49 else 2000 + yy)
        return {'part': match.group('part'), 'year': year, 'page': match.group('page').lower().lstrip('0')}
    match = _GAZETTE_ELI.search(text)
    if match:
        found = match.group('id').lower()
        if found.startswith('s'):
            return {'part': match.group('part'), 'year': match.group('year'), 'page': found[1:]}
        return {'part': match.group('part'), 'year': match.group('year'), 'number': found}
    return None


def citation(reference: dict[str, str]) -> str:
    """{'part': '1', 'year': '2024', 'number': '149'} -> 'BGBl. 2024 I Nr. 149'."""
    part = 'I' * int(reference['part'])
    if 'number' in reference:
        return f"BGBl. {reference['year']} {part} Nr. {reference['number']}"
    return f"BGBl. {reference['year']} {part} S. {reference['page']}"


def reference_eli(reference: dict[str, str]) -> str:
    """The work ELI of a promulgation: 'eli/bund/bgbl-1/2024/149', 'eli/bund/bgbl-1/2017/s2097'."""
    natural = reference['number'] if 'number' in reference else f"s{reference['page']}"
    return f"eli/bund/bgbl-{reference['part']}/{reference['year']}/{natural}"


def _is_citation(identifier: str) -> bool:
    """Whether an identifier names the act as promulgated (a Gazette citation or link), not an ELI."""
    text = identifier.strip()
    return bool(_CITATION.match(' '.join(text.split())) or _PROMULGATION_PAGE.search(text)
                or ('bgbl.de' in text.lower() and _ARCHIVE_NAME.search(text)))


class GermanySource(Source):
    code = 'DE'
    name = 'Germany'
    source_name = ('Rechtsinformationen des Bundes (test phase) for consolidated law; '
                   'Bundesgesetzblatt (recht.bund.de, bgbl.de archive) for acts as promulgated')
    versions = (ORIGINAL, CONSOLIDATED)
    languages = ('deu',)
    identifier_help = ("the ELI of a federal act for the consolidated version in force "
                       "(e.g. 'eli/bund/bgbl-1/2009/s2704'), or its Federal Law Gazette citation for the act as "
                       "promulgated: 'BGBl. 2024 I Nr. 149' since 2023, 'BGBl. 2017 I S. 2097' (year, part and "
                       "first page) for 1949-2022; recht.bund.de and bgbl.de links work too, and an ELI with "
                       "version='original'")
    eli_patterns = (
        re.compile(r'^(?P<id>https?://(testphase\.rechtsinformationen\.bund\.de(/v1/legislation)?|www\.recht\.bund\.de)'
                   r'/eli/bund/[\w-]+/\d{4}/[\w-]+)(/.*)?$', re.IGNORECASE),
        re.compile(r'^(?P<id>https?://www\.recht\.bund\.de/bgbl/[12]/\d{4}/\w+/.*)$', re.IGNORECASE),
        re.compile(r'^(?P<id>https?://www\.bgbl\.de/xaver/bgbl/start\.xav\?.*bgbl[12]\d{2}s\d+[a-z]?\.pdf.*)$',
                   re.IGNORECASE),
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
        # An ELI names the act in force, a Gazette citation the act as promulgated
        version = version or (ORIGINAL if _is_citation(identifier) else CONSOLIDATED)
        if version == ORIGINAL:
            if date:
                raise UnsupportedError("A date selects a consolidated version; the original version has none")
            return self._original(identifier, download_dir)
        return self._consolidated(identifier, date, download_dir)

    def _consolidated(self, identifier: str, date: Optional[str], download_dir: str) -> Retrieval:
        if date:
            raise UnsupportedError("The federal portal currently publishes only the version in force; "
                                   "a date cannot be selected")
        work = work_eli(identifier)
        client = GermanyClient(download_dir=download_dir)
        expression = client.current_expression(work)
        if expression is None:
            raise FileLoadError(f"{work} is not available on the federal legal information portal")
        path = client.download_expression_xml(expression)
        client.download_attachments(path)
        version_date = re.search(r'/(\d{4}-\d{2}-\d{2})/\d+/deu', expression.get('legislationIdentifier', ''))
        return Retrieval(
            path=path,
            parser='akn',
            parser_options={'file_path': path},
            version=CONSOLIDATED,
            language='deu',
            version_date=version_date.group(1) if version_date else None,
            meta={
                'eli': f'{PORTAL}/{work}',
                'date_document': expression.get('exampleOfWork', {}).get('legislationDate'),
                'in_force': expression.get('legislationLegalForce') == 'InForce',
                'source': f"{PORTAL}/v1/legislation/{expression.get('legislationIdentifier')}",
            },
        )

    def _original(self, identifier: str, download_dir: str) -> Retrieval:
        reference = gazette_reference(identifier)
        if reference is None:
            if _WORK.search(identifier):
                raise UnsupportedError(f"'{identifier}' was not promulgated in the Federal Law Gazette; the original "
                                       f"version is available for Bundesgesetzblatt acts only")
            raise UnsupportedError(f"'{identifier}' is not a Federal Law Gazette citation; use {self.identifier_help}")
        year = int(reference['year'])
        client = BundesgesetzblattClient(download_dir=download_dir)
        if year >= ELECTRONIC:
            if 'number' not in reference:
                raise UnsupportedError(f"Since 2023 the Federal Law Gazette numbers its promulgations: cite "
                                       f"'BGBl. {year} {'I' * int(reference['part'])} Nr. ...', not a page")
            return self._promulgation(client, reference)
        if 'page' not in reference:
            raise UnsupportedError(f"The Federal Law Gazette of {year} is cited by page: "
                                   f"'BGBl. {year} {'I' * int(reference['part'])} S. ...'")
        return self._archive(client, reference)

    def _promulgation(self, client: BundesgesetzblattClient, reference: dict[str, str]) -> Retrieval:
        part, year, number = reference['part'], reference['year'], reference['number']
        promulgation = client.promulgation(part, year, number)
        paths = client.download_promulgation(promulgation, part, year, number)
        meta = {
            'eli': promulgation_url(part, year, number),
            'source': promulgation['pdf_urls'][0],
            'gazette': promulgation.get('citation') or citation(reference),
            'date_document': promulgation.get('date_document'),
            'date_publication': promulgation.get('date_publication'),
            'title': promulgation.get('title'),
            'type': promulgation.get('type'),
        }
        return Retrieval(
            path=paths[0],
            parser='de-bgbl-pdf',
            parser_options={'annexes': paths[1:]} if len(paths) > 1 else {},
            version=ORIGINAL,
            language='deu',
            version_date=promulgation.get('date_publication'),
            meta={key: value for key, value in meta.items() if value},
        )

    def _archive(self, client: BundesgesetzblattClient, reference: dict[str, str]) -> Retrieval:
        part, year, page = reference['part'], reference['year'], reference['page']
        # Pages are written with four digits in some years ('bgbl251s0145.pdf')
        digits, letter = re.match(r'(\d+)([a-z]?)', page).groups()
        names = list(dict.fromkeys(archive_name(part, year, f'{number}{letter}')
                                   for number in (digits.lstrip('0') or '0', digits.zfill(4))))
        found = next(((name, document) for name in names
                      for document in [client.archive_document(name)] if document), None)
        if found is None:
            if not letter and any(client.archive_document(name.replace('.pdf', 'a.pdf')) for name in names):
                raise UnsupportedError(f"Several acts begin on {citation(reference)}; add the letter of the one "
                                       f"meant, e.g. '{citation(reference)}a'")
            raise FileLoadError(f"The bgbl.de archive has no act beginning on {citation(reference)}: "
                                f"cite the first page of the act")
        name, document = found
        path = client.download_archive(document)
        meta = {
            'eli': f'{PORTAL}/{reference_eli(reference)}',
            'source': archive_url(name),
            'gazette': citation(reference),
            'gazette_issue': document.get('issue'),
            'date_publication': document.get('date_publication'),
            'title': document.get('title'),
        }
        # Issues before about 1998 are scanned images without text
        readable = has_text(path)
        if not readable:
            meta['scanned'] = True
        return Retrieval(
            path=path,
            parser='de-bgbl-pdf' if readable else None,
            parser_options={'title': document.get('title')} if readable else {},
            version=ORIGINAL,
            language='deu',
            version_date=document.get('date_publication'),
            meta={key: value for key, value in meta.items() if value},
        )
