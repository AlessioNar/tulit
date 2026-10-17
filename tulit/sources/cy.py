"""
Cyprus: Official Gazette of the Republic (Government Printing Office).

Laws are published in the Official Gazette, Annex One, under Article 52 of
the Constitution; that publication is the official text. The Republic
publishes no official consolidated texts, so only the original is available.
"""
import re
from typing import Any, Optional

from tulit.client.state.cyprus import CyprusGazetteClient
from tulit.parser.pdf.cyprus import normalise_number
from tulit.sources.base import ORIGINAL, Retrieval, Source


class CyprusSource(Source):
    code = 'CY'
    name = 'Cyprus'
    source_name = 'Official Gazette of the Republic of Cyprus (Government Printing Office)'
    versions = (ORIGINAL,)
    languages = ('ell',)
    identifier_help = ("the number of a law, e.g. '125(I)/2018' (Ν. 125(Ι)/2018, the data protection law) "
                       "or '125(Ι) του 2018'")

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
            raise ValueError("The Official Gazette publishes laws as adopted; a date cannot be selected")
        try:
            number = normalise_number(identifier)
        except ValueError:
            raise ValueError(f"'{identifier}' is not a Cypriot law number; use {self.identifier_help}") from None
        law, part, year = re.match(r'^(\w+)\((I+)\)/(\d{4})$', number).groups()
        client = CyprusGazetteClient(download_dir=download_dir)
        path, details = client.download(law, part, year)
        meta = {
            'source': details.get('pdf'),
            'gazette_issue': details.get('issue'),
            'gazette_pages': details.get('pages'),
            'date_publication': details.get('date_publication'),
            'number': number,
        }
        return Retrieval(
            path=path,
            parser='cy-gazette-pdf',
            parser_options={'number': number},
            version=ORIGINAL,
            language='ell',
            version_date=details.get('date_publication'),
            meta={key: value for key, value in meta.items() if value},
        )
