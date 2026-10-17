"""
Bulgaria: State Gazette (Държавен вестник), published by the National Assembly.

Acts are published in the official section of the State Gazette; Bulgaria
publishes no official consolidated texts, so only the original is available.
The material pages of the Gazette cover the issues since 2003.
"""
import re
from typing import Any, Optional

from tulit.client.state.bulgaria import DV, StateGazetteClient
from tulit.parser.exceptions import FileLoadError
from tulit.sources.base import ORIGINAL, Retrieval, Source

_MATERIAL = re.compile(r'^(?:https?://dv\.parliament\.bg/DVWeb/showMaterialDV\.jsp\?(?:.*&)?idMat=)?(?P<id>\d{1,7})'
                       r'(?:&.*)?$')
_ISSUE = re.compile(r'^(?:ДВ,?\s*)?бр\.?\s*(?P<issue>\d+[а-я]?)\s*(?:от|/)\s*(?P<year>\d{4})\s*(?:г\.?)?'
                    r'\s*[,;:–-]?\s*(?P<title>.*)$', re.IGNORECASE)


def _normal(text: str) -> str:
    return ' '.join(text.lower().replace('„', '').replace('“', '').split())


def _choose(results: list[dict[str, Any]], title: Optional[str], identifier: str) -> dict[str, Any]:
    """The material a request names: the one titled exactly so, else the only one found."""
    if title:
        wanted = _normal(title)
        # The result's title starts with the issuer ('Народно събрание Закон за ...')
        exact = [r for r in results if _normal(r['title']) == wanted or _normal(r['title']).endswith(' ' + wanted)]
        if len(exact) == 1:
            return exact[0]
        if exact:
            results = exact
    if len(results) == 1:
        return results[0]
    if not results:
        raise FileLoadError(f"The State Gazette has no act matching '{identifier}'")
    candidates = '; '.join(f"бр. {r['issue']} ({r['date_publication']}): {r['title']}" for r in results[:5])
    raise FileLoadError(f"'{identifier}' matches several acts in the State Gazette; give the issue and the exact "
                        f"title, or the material number. Candidates: {candidates}")


class BulgariaSource(Source):
    code = 'BG'
    name = 'Bulgaria'
    source_name = 'State Gazette (Държавен вестник, National Assembly)'
    versions = (ORIGINAL,)
    languages = ('bul',)
    identifier_help = ("the issue and title of an act ('ДВ, бр. 38 от 2016 г., Закон за електронната "
                       "идентификация'), its exact title, or its material number on dv.parliament.bg ('103709', "
                       "or the showMaterialDV.jsp link); acts published since 2003")
    eli_patterns = (re.compile(r'^(?P<id>https?://dv\.parliament\.bg/DVWeb/showMaterialDV\.jsp\?(?:.*&)?idMat=\d+)'
                               r'(&.*)?$'),)

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
            raise ValueError("The State Gazette publishes acts as adopted; a date cannot be selected")
        client = StateGazetteClient(download_dir=download_dir)
        text = ' '.join(identifier.split())
        material = _MATERIAL.match(text)
        if material:
            number = material.group('id')
        else:
            issue = _ISSUE.match(text)
            if issue:
                title = issue.group('title').strip() or None
                results = client.search(title=title, issue=issue.group('issue'), year=int(issue.group('year')))
            elif len(text) > 8:
                title = text
                results = client.search(title=title)
            else:
                raise ValueError(f"'{identifier}' is not a State Gazette reference; use {self.identifier_help}")
            number = _choose(results, title, identifier)['material']
        path = client.download(number)
        found = client.metadata(path)
        meta = {
            'source': f'{DV}/showMaterialDV.jsp?idMat={number}',
            'title': found.get('title'),
            'gazette_issue': found.get('issue'),
            'gazette_page': found.get('page'),
            'gazette_section': found.get('section'),
            'date_publication': found.get('date_publication'),
        }
        return Retrieval(
            path=path,
            parser='bg-dv',
            version=ORIGINAL,
            language='bul',
            version_date=found.get('date_publication'),
            meta={key: value for key, value in meta.items() if value},
        )
