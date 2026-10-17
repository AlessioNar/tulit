"""
Finland: Finlex (Ministry of Justice).
"""
import re
from typing import Any, Optional

from tulit.client.state.finlex import FinlexClient
from tulit.parser.exceptions import FileLoadError
from tulit.sources.base import CONSOLIDATED, Retrieval, Source

FINLEX_ELI = 'http://data.finlex.fi/eli/sd'
_CITATION = re.compile(r'^(\d+)\s*/\s*(\d{4})$')


def statute_number(identifier: str) -> tuple[str, str]:
    """'1050/2018' (number/year) -> ('2018', '1050'); 'sd/2018/1050' or a Finlex ELI -> ('2018', '1050')."""
    text = identifier.strip().rstrip('/')
    match = _CITATION.match(text)
    if match:
        return match.group(2), match.group(1)
    match = re.search(r'(?:^|/)sd/(\d{4})/(\d+)(?:/\w+)?$', text)
    if match:
        return match.group(1), match.group(2)
    raise ValueError(f"'{identifier}' is not a Finnish statute number; use number/year, e.g. '1050/2018'")


class FinlandSource(Source):
    code = 'FI'
    name = 'Finland'
    source_name = 'Finlex (Ministry of Justice)'
    languages = ('fin', 'swe')
    identifier_help = "the statute number/year (e.g. '1050/2018' for the Data Protection Act)"
    eli_patterns = (re.compile(r'^https?://data\.finlex\.fi/eli/(?P<id>sd/\d{4}/\d+)(/\w+)?/?$'),)

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
            raise ValueError("Finlex publishes the consolidated text currently in force; a date cannot be selected")
        year, number = statute_number(identifier)
        language = (language or self.default_language).lower()
        consolidated = version == CONSOLIDATED
        path = FinlexClient(download_dir=download_dir).download(
            year, number, consolidated=consolidated, language=language)
        if path is None:
            raise FileLoadError(
                f"Finlex has no {'consolidated ' if consolidated else ''}text of {number}/{year} in {language}")
        return Retrieval(
            path=path,
            parser='akn',
            parser_options={'file_path': path},
            version=version,
            language=language,
            meta={
                'eli': f'{FINLEX_ELI}/{year}/{number}',
                'source': f'{FinlexClient.BASE_URL}/akn/fi/act/'
                          f"{'statute-consolidated' if consolidated else 'statute'}/{year}/{number}/{language}@",
            },
        )
