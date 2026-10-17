"""
Germany: Rechtsinformationen des Bundes (federal legal information portal, test phase).
"""
import re
from typing import Any, Optional

from tulit.client.state.germany import GermanyClient
from tulit.parser.exceptions import FileLoadError
from tulit.sources.base import CONSOLIDATED, Retrieval, Source

PORTAL = 'https://testphase.rechtsinformationen.bund.de'
_WORK = re.compile(r'(eli/bund/[\w-]+/\d{4}/[\w-]+)')


def work_eli(identifier: str) -> str:
    """'eli/bund/bgbl-1/2009/s2704', a portal URL or an expression ELI -> 'eli/bund/bgbl-1/2009/s2704'."""
    match = _WORK.search(identifier)
    if not match:
        raise ValueError(
            f"'{identifier}' is not a German federal ELI; use e.g. 'eli/bund/bgbl-1/2009/s2704'")
    return match.group(1)


class GermanySource(Source):
    code = 'DE'
    name = 'Germany'
    source_name = 'Rechtsinformationen des Bundes (test phase)'
    versions = (CONSOLIDATED,)
    languages = ('deu',)
    identifier_help = "the ELI of a federal act (e.g. 'eli/bund/bgbl-1/2009/s2704')"
    eli_patterns = (re.compile(
        r'^(?P<id>https?://(testphase\.rechtsinformationen\.bund\.de(/v1/legislation)?|www\.recht\.bund\.de)'
        r'/eli/bund/[\w-]+/\d{4}/[\w-]+)(/.*)?$'),)

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
            raise ValueError("The federal portal currently publishes only the version in force; "
                             "a date cannot be selected")
        work = work_eli(identifier)
        client = GermanyClient(download_dir=download_dir)
        expression = client.current_expression(work)
        if expression is None:
            raise FileLoadError(f"{work} is not available on the federal legal information portal")
        path = client.download_expression_xml(expression)
        version_date = re.search(r'/(\d{4}-\d{2}-\d{2})/\d+/deu', expression.get('legislationIdentifier', ''))
        return Retrieval(
            path=path,
            parser='akn',
            parser_options={'file_path': path},
            version=version,
            language='deu',
            version_date=version_date.group(1) if version_date else None,
            meta={
                'eli': f'{PORTAL}/{work}',
                'date_document': expression.get('exampleOfWork', {}).get('legislationDate'),
                'in_force': expression.get('legislationLegalForce') == 'InForce',
                'source': f"{PORTAL}/v1/legislation/{expression.get('legislationIdentifier')}",
            },
        )
