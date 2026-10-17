"""
Malta: Legislation Malta (legislation.mt).

Consolidated laws are the Chapters of the Laws of Malta ('Cap. 586'); laws
as passed are the Acts ('Act XII of 2018') and Legal Notices. Both are
published as PDF, so Malta needs the ``pdf`` extra.
"""
import re
from typing import Any, Optional

from tulit.client.state.malta import MaltaLegislationClient
from tulit.parser.exceptions import FileLoadError
from tulit.sources.base import CONSOLIDATED, ORIGINAL, Retrieval, Source

LEGISLATION_MT = 'https://legislation.mt/eli'
_CHAPTER = re.compile(r'^(?:(?:Cap\.?|Chapter|Kap\.?|Kapitolu)\s*)?(?P<cap>\d+)$', re.IGNORECASE)
_ACT = re.compile(r'^Act\s+(?:No\.?\s*)?(?P<num>[IVXLCDM]+|\d+)\s+of\s+(?P<year>\d{4})$', re.IGNORECASE)
_LEGAL_NOTICE = re.compile(r'^(?:L\.\s?N\.|Legal Notice)\s*(?P<num>\d+)\s+of\s+(?P<year>\d{4})$', re.IGNORECASE)
_ELI = re.compile(r'(?:^|eli/)(?P<path>cap/\d+|act/\d{4}/\d+|ln/\d{4}/\d+)(?:/|$)')
_ROMAN = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
_LANGUAGES = {'eng': 'eng', 'mlt': 'mlt'}


def roman(number: str) -> int:
    """'XII' -> 12."""
    values = [_ROMAN[c] for c in number.upper()]
    return sum(-v if i + 1 < len(values) and v < values[i + 1] else v for i, v in enumerate(values))


def eli_path(identifier: str) -> str:
    """'Cap. 586', 'Act XII of 2018', 'L.N. 212 of 2023' or an ELI -> 'cap/586', 'act/2018/12', 'ln/2023/212'."""
    text = identifier.strip()
    match = _ELI.search(text)
    if match:
        return match.group('path')
    match = _CHAPTER.match(text)
    if match:
        return f"cap/{match.group('cap')}"
    match = _ACT.match(text)
    if match:
        number = match.group('num')
        return f"act/{match.group('year')}/{int(number) if number.isdigit() else roman(number)}"
    match = _LEGAL_NOTICE.match(text)
    if match:
        return f"ln/{match.group('year')}/{match.group('num')}"
    raise ValueError(f"'{identifier}' is not a Maltese law reference; use e.g. 'Cap. 586' or 'Act XII of 2018'")


def _enacting_act(path: str) -> Optional[str]:
    """The Act that enacted a Chapter, from its cover page ('ACT XX of 2018, as amended by ...')."""
    from tulit.parser.pdf.layout import read_lines
    lines, _, _ = read_lines(path)
    for line in lines[:40]:
        match = re.match(r'^(?:ACT|ATT)\s+([IVXLCDM]+)\s+(?:of|tal-)\s*(\d{4})', line.text)
        if match:
            return f'act/{match.group(2)}/{roman(match.group(1))}'
    return None


class MaltaSource(Source):
    code = 'MT'
    name = 'Malta'
    source_name = 'Legislation Malta (Office of the State Advocate)'
    languages = ('eng', 'mlt')
    identifier_help = ("a Chapter for consolidated law (e.g. 'Cap. 586' for the Data Protection Act) or an Act "
                       "or Legal Notice as passed (e.g. 'Act XII of 2018', 'L.N. 212 of 2023')")
    eli_patterns = (re.compile(r'^(?P<id>https?://legislation\.mt/eli/(cap/\d+|act/\d{4}/\d+|ln/\d{4}/\d+))(/.*)?$'),)
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
        if date:
            raise ValueError("Legislation Malta publishes Chapters as in force now; a date cannot be selected")
        path = eli_path(identifier)
        language = _LANGUAGES.get((language or 'eng').lower(), 'eng')
        client = MaltaLegislationClient(download_dir=download_dir)
        chapter = path.startswith('cap/')
        version = version or (CONSOLIDATED if chapter else ORIGINAL)

        if language == 'mlt' and not chapter:
            raise ValueError("Acts and Legal Notices are printed in Maltese and English side by side; "
                             "use language='eng'")
        if version == CONSOLIDATED and not chapter:
            raise ValueError("Consolidated law is addressed by its Chapter (e.g. 'Cap. 586'), "
                             "not by the Act or Legal Notice that made it")
        file = self._download(client, path, language)
        if version == ORIGINAL and chapter:
            act = _enacting_act(file)
            if act is None:
                raise FileLoadError(f"The cover of {path} names no enacting Act")
            path = act
            file = self._download(client, path, language)
        return Retrieval(
            path=file,
            parser='mt-pdf',
            version=version,
            language=language,
            version_date=None,
            meta={
                'eli': f'{LEGISLATION_MT}/{path}',
                'source': f'{LEGISLATION_MT}/{path}/{language}/pdf',
            },
        )

    @staticmethod
    def _download(client: MaltaLegislationClient, path: str, language: str) -> str:
        file = client.download(path, lang=language, fmt='pdf')
        if file is None:
            raise FileLoadError(f"Legislation Malta has no PDF for {path} ({language})")
        return file
