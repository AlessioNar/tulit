"""
Cyprus: Official Gazette of the Republic (Government Printing Office).

Laws are published in the Official Gazette, Annex One, under Article 52 of
the Constitution; that publication is the official text. The Republic
publishes no official consolidated texts, so only the original is available.

A law is found by its number through the Gazette's search, which covers the
issues from about 2015. Older issues are scanned images: they are found by
their issue number in the archive, and ``tulit.download`` returns their PDF.
"""
import re
from typing import Any, Optional

from tulit.client.state.cyprus import GAZETTE, CyprusGazetteClient
from tulit.parser.exceptions import FileLoadError, UnsupportedError
from tulit.parser.pdf.cyprus import normalise_number
from tulit.parser.pdf.layout import has_text as _has_text
from tulit.sources.base import ORIGINAL, Retrieval, Source

_ISSUE = re.compile(r'^(?:Αρ\.?\s*|Ε\.Ε\..*?Αρ\.\s*|issue\s+)?(?P<issue>\d{3,5})\s*(?:/|,)\s*'
                    r'(?:(?P<day>\d{1,2})[./](?P<month>\d{1,2})[./])?(?P<year>\d{4})$', re.IGNORECASE)
_LINK = re.compile(r'^https?://www\.mof\.gov\.cy/mof/gpo/gazette\.nsf/All/[0-9A-F]{32}')


class CyprusSource(Source):
    code = 'CY'
    name = 'Cyprus'
    source_name = 'Official Gazette of the Republic of Cyprus (Government Printing Office)'
    versions = (ORIGINAL,)
    languages = ('ell',)
    options = ('number',)
    identifier_help = ("the number of a law, e.g. '125(I)/2018' (Ν. 125(Ι)/2018, the data protection law) "
                       "or '125(Ι) του 2018'; for laws before about 2015, the Annex One issue that published "
                       "them, e.g. '4252/2010' or '4252, 23.7.2010', or the link of the issue")
    eli_patterns = (re.compile(r'^(?P<id>https?://www\.mof\.gov\.cy/mof/gpo/gazette\.nsf/All/[0-9A-F]{32})'
                               r'(\?.*|/.*)?$'),)

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
            raise UnsupportedError("The Official Gazette publishes laws as adopted; a date cannot be selected")
        client = CyprusGazetteClient(download_dir=download_dir)
        text = identifier.strip()
        issue = _ISSUE.match(text)
        if _LINK.match(text) or issue:
            # An issue of the Gazette: its first law, or the law ``number`` it holds
            if issue:
                month = int(issue.group('month')) if issue.group('month') else None
                link = client.find_issue(issue.group('issue'), int(issue.group('year')), month)
            else:
                link = text if '?' in text else f'{text}?OpenDocument'
            path, details = client.download_issue(link)
            number = normalise_number(number) if number else None
        else:
            try:
                number = normalise_number(text)
            except ValueError:
                raise UnsupportedError(f"'{identifier}' is neither a Cypriot law number nor a Gazette issue; "
                                       f"use {self.identifier_help}") from None
            law, part, year = re.match(r'^(\w+)\((I+)\)/(\d{4})$', number).groups()
            try:
                path, details = client.download(law, part, year)
            except FileLoadError as e:
                raise FileLoadError(f"{e}. For an older law, give the Annex One issue that published it, "
                                    f"e.g. '4252/2010'") from None
        meta = {
            'source': details.get('pdf') or GAZETTE,
            'gazette_issue': details.get('issue'),
            'gazette_pages': details.get('pages'),
            'date_publication': details.get('date_publication'),
            'number': number,
        }
        readable = _has_text(path)
        if not readable:
            meta['scanned'] = True
        return Retrieval(
            path=path,
            parser='cy-gazette-pdf' if readable else None,
            parser_options={'number': number} if number and readable else {},
            version=ORIGINAL,
            language='ell',
            version_date=details.get('date_publication'),
            meta={key: value for key, value in meta.items() if value},
        )
