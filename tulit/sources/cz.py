"""
Czechia: e-Sbírka (Collection of Laws).
"""
import re
from typing import Any, Optional

from tulit.client.state.czechia import ESBIRKA, EsbirkaClient
from tulit.sources.base import CONSOLIDATED, ORIGINAL, Retrieval, Source

_CITATION = re.compile(r'^(?:zákon\s+)?(?:č\.\s*)?(?P<number>\d+)\s*/\s*(?P<year>\d{4})(?:\s*Sb\.?)?$', re.IGNORECASE)
_PATH = re.compile(r'(?:^|/)(?:eli/cz/)?sb/(?P<year>\d{4})/(?P<number>\d+)(?:/(?P<date>\d{4}-\d{2}-\d{2}))?')


def act_path(identifier: str) -> tuple[str, Optional[str]]:
    """'110/2019 Sb.', '/sb/2019/110' or an e-Sbírka ELI -> ('/sb/2019/110', date of a named version or None)."""
    text = identifier.strip()
    match = _CITATION.match(text)
    if match:
        return f"/sb/{match.group('year')}/{match.group('number')}", None
    match = _PATH.search(text)
    if match:
        return f"/sb/{match.group('year')}/{match.group('number')}", match.group('date')
    raise ValueError(f"'{identifier}' is not a Collection of Laws reference; use e.g. '110/2019 Sb.'")


class CzechiaSource(Source):
    code = 'CZ'
    name = 'Czechia'
    source_name = 'e-Sbírka (Collection of Laws, Ministry of the Interior)'
    languages = ('ces',)
    identifier_help = "the Collection of Laws number of an act (e.g. '110/2019 Sb.' for the Act on Personal Data Processing)"
    eli_patterns = (re.compile(r'^(?P<id>https?://(www\.)?e-sbirka\.(gov\.)?cz/(eli/cz/)?sb/\d{4}/\d+(/\d{4}-\d{2}-\d{2})?)(/.*)?$'),)
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
        path, named = act_path(identifier)
        client = EsbirkaClient(download_dir=download_dir)
        act = client.metadata(path)
        published = (act.get('datumCasVyhlaseni') or '')[:10] or None
        first = act.get('datumUcinnostiOd')

        if version is None and named and not date:
            # An ELI naming a version: return that version
            version = ORIGINAL if named == first else CONSOLIDATED
            when = named
        else:
            version = version or ORIGINAL
            if version == ORIGINAL:
                if date:
                    raise ValueError("A date selects a consolidated version; the original version has none")
                when = first
            else:
                when = date

        chosen = client.metadata(f'{path}/{when}') if when else act
        version_path = chosen['staleUrl']
        file = client.download(version_path)
        return Retrieval(
            path=file,
            parser='cz-esbirka',
            version=version,
            language='ces',
            version_date=chosen.get('datumUcinnostiZneniOd'),
            meta={
                'eli': f"{ESBIRKA}/eli/cz{path}",
                'date_document': published,
                'in_force': chosen.get('typZneni') == 'AKTUALNI' if version == CONSOLIDATED else None,
                'source': f'{ESBIRKA}{version_path}',
            },
        )
