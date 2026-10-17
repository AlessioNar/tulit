"""
Poland: Dziennik Ustaw and Monitor Polski, through the Sejm ELI API.

The consolidated version of an act is its official consolidated text (tekst
jednolity): an announcement published in the Journal of Laws whose annex
holds the act as amended up to then. Amendments published after the latest
consolidated text are not part of it.
"""
import datetime
import logging
import re
from typing import Any, Optional

from tulit.client.state.poland import ELI_API, SejmELIClient
from tulit.parser.exceptions import FileLoadError
from tulit.sources.base import CONSOLIDATED, ORIGINAL, Retrieval, Source

ELI_PL = 'https://eli.gov.pl/eli'
logger = logging.getLogger(__name__)
_ELI = re.compile(r'(?:^|/)(?P<publisher>DU|MP)/(?P<year>\d{4})/(?P<position>\d+)(?:/|$)', re.IGNORECASE)
_CITATION = re.compile(r'^(?P<publisher>Dz\.?\s*U\.?|M\.?\s*P\.?)\s*(?:z\s*)?(?P<year>\d{4})\s*(?:r\.)?\s*'
                       r'(?:Nr\s*\d+\s*,?\s*)?poz\.?\s*(?P<position>\d+)$', re.IGNORECASE)
_ADDRESS = re.compile(r'(?:^|id=)(?P<publisher>W[DM][UP])(?P<year>\d{4})(?P<position>\d{7})', re.IGNORECASE)


def act_eli(identifier: str) -> str:
    """'DU/2018/1000', 'Dz.U. 2018 poz. 1000', 'WDU20180001000' or an ELI URI -> 'DU/2018/1000'."""
    text = identifier.strip()
    match = _CITATION.match(text)
    if match:
        publisher = 'DU' if match.group('publisher').upper().startswith('D') else 'MP'
        return f"{publisher}/{match.group('year')}/{int(match.group('position'))}"
    match = _ADDRESS.search(text)
    if match:
        publisher = 'DU' if match.group('publisher').upper() == 'WDU' else 'MP'
        return f"{publisher}/{match.group('year')}/{int(match.group('position'))}"
    match = _ELI.search(text)
    if match:
        return f"{match.group('publisher').upper()}/{match.group('year')}/{int(match.group('position'))}"
    raise ValueError(f"'{identifier}' is not a Polish act reference; use e.g. 'DU/2018/1000' "
                     f"or 'Dz.U. 2018 poz. 1000'")


def _references(act: dict[str, Any], kind: str) -> list[str]:
    return [reference['id'] for reference in (act.get('references') or {}).get(kind, [])]


def _published(act: dict[str, Any]) -> str:
    return act.get('promulgation') or act.get('announcementDate') or ''


class PolandSource(Source):
    code = 'PL'
    name = 'Poland'
    source_name = 'Dziennik Ustaw and Monitor Polski (Sejm ELI API)'
    languages = ('pol',)
    identifier_help = "the Journal of Laws reference of an act (e.g. 'DU/2018/1000' or 'Dz.U. 2018 poz. 1000')"
    eli_patterns = (
        re.compile(r'^(?P<id>https?://eli\.gov\.pl/eli/(DU|MP)/\d{4}/\d+)(/.*)?$'),
        re.compile(r'^(?P<id>https?://api\.sejm\.gov\.pl/eli/acts/(DU|MP)/\d{4}/\d+)(/.*)?$'),
        re.compile(r'^(?P<id>https?://isap\.sejm\.gov\.pl/isap\.nsf/DocDetails\.xsp\?id=W(DU|MP)\d{11})$'),
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
        client = SejmELIClient(download_dir=download_dir)
        eli = act_eli(identifier)
        act = client.act(eli)
        consolidates = _references(act, 'Tekst jednolity dla aktu')

        base = client.act(consolidates[0]) if consolidates else act
        if version is None:
            # A consolidated text names itself; any other act is returned as published
            version = CONSOLIDATED if consolidates else ORIGINAL
            chosen = act
        elif version == ORIGINAL:
            if date:
                raise ValueError("A date selects a consolidated version; the original version has none")
            chosen = base
        else:
            chosen = self._consolidated_text(client, base, date)

        chosen_eli = chosen.get('ELI') or eli
        if not chosen.get('textHTML'):
            raise FileLoadError(f"{chosen.get('displayAddress') or chosen_eli} is published only as PDF; "
                                f"the Sejm ELI API has no HTML text for it")
        path = client.download_text(chosen_eli)
        return Retrieval(
            path=path,
            parser='pl-eli',
            version=version,
            language='pol',
            version_date=chosen.get('announcementDate') or _published(chosen) or None,
            meta={
                'eli': f"{ELI_PL}/{base.get('ELI') or eli}/ogl",
                'date_document': base.get('announcementDate'),
                'in_force': base.get('inForce') == 'IN_FORCE',
                'source': f'{ELI_API}/{chosen_eli}/text.html',
            },
        )

    @staticmethod
    def _consolidated_text(client: SejmELIClient, act: dict[str, Any], date: Optional[str]) -> dict[str, Any]:
        """The latest official consolidated text published on or before ``date``."""
        target = date or datetime.date.today().isoformat()
        texts = [client.act(eli) for eli in _references(act, 'Inf. o tekście jednolitym')]
        texts = sorted((t for t in texts if _published(t) and _published(t) <= target), key=_published)
        with_html = [t for t in texts if t.get('textHTML')]
        if with_html:
            if with_html[-1] is not texts[-1]:
                logger.warning("The latest consolidated text %s has no HTML yet; using %s",
                               texts[-1].get('displayAddress'), with_html[-1].get('displayAddress'))
            return with_html[-1]
        if texts:
            return texts[-1]
        if not _references(act, 'Akty zmieniające') and _published(act) <= target:
            # Never amended: the act as published is its consolidated text
            return act
        raise FileLoadError(f"No official consolidated text of {act.get('displayAddress') or act.get('ELI')} "
                            f"was published on or before {target}")
