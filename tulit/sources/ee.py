"""
Estonia: Riigi Teataja (State Gazette).
"""
import datetime
import re
from typing import Any, Optional

from lxml import etree

from tulit.client.state.estonia import RIIGI_TEATAJA, RiigiTeatajaClient
from tulit.parser.exceptions import FileLoadError, UnsupportedError
from tulit.sources.base import CONSOLIDATED, ORIGINAL, Retrieval, Source

_GLOBAL_ID = re.compile(r'^(?:https?://www\.riigiteataja\.ee/(?:en/)?akt/)?(\d{5,12})(?:[/?#.].*)?$')
_ABBREVIATION = re.compile(r'^[A-ZÕÄÖÜŠŽ][A-Za-zÕÄÖÜŠŽõäöüšž]{1,15}$')


_ISO_DATE = re.compile(r'^\d{4}-\d{2}-\d{2}')


def _date(value: Optional[str]) -> Optional[str]:
    """'2002-03-27+02:00' -> '2002-03-27'."""
    match = _ISO_DATE.match((value or '').strip())
    return match.group(0) if match else None


def _validity(text: dict[str, Any]) -> tuple[str, Optional[str]]:
    period = text.get('kehtivus') or {}
    return _date(period.get('algus')) or '', _date(period.get('lopp'))


def _act_dates(path: str) -> tuple[Optional[str], Optional[str]]:
    """Adoption date (vastuvoetud/aktikuupaev) and publication date (avaldamineKuupaev) of the act."""
    root = etree.parse(path).getroot()
    adopted = root.find('.//{*}vastuvoetud/{*}aktikuupaev')
    published = root.find('.//{*}avaldamismarge/{*}avaldamineKuupaev')
    return (_date(adopted.text) if adopted is not None else None,
            _date(published.text) if published is not None else None)


class EstoniaSource(Source):
    code = 'EE'
    name = 'Estonia'
    source_name = 'Riigi Teataja (Ministry of Justice and Digital Affairs)'
    languages = ('est',)
    identifier_help = ("an act's abbreviation (e.g. 'IKS' for the Isikuandmete kaitse seadus) or "
                       "the id of one of its texts (e.g. '104012019011')")
    eli_patterns = (re.compile(r'^(?P<id>https?://www\.riigiteataja\.ee/(en/)?akt/\d{5,12})([/?#.].*)?$'),)
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
        client = RiigiTeatajaClient(download_dir=download_dir)
        text_id = _GLOBAL_ID.match(identifier.strip())

        if text_id and version is None and not date:
            # A text id names one text: return it as is
            chosen = client.act(text_id.group(1))
            global_id = chosen['global_id']
            version = ORIGINAL if 'algtekst' in (chosen['text_type'] or '') else CONSOLIDATED
            texts = client.texts(chosen['group_id'], title=chosen['title'], abbreviation=chosen['abbreviation'])
            text = next((t for t in texts if str(t['globaalID']) == global_id), {})
        else:
            if text_id:
                act = client.act(text_id.group(1))
                texts = client.texts(act['group_id'], title=act['title'], abbreviation=act['abbreviation'])
            elif _ABBREVIATION.match(identifier.strip()):
                texts = self._texts_by_abbreviation(client, identifier.strip())
            else:
                raise UnsupportedError(f"'{identifier}' is not a Riigi Teataja text id or act abbreviation; "
                                 f"use {self.identifier_help}")
            version = version or CONSOLIDATED
            text = self._choose(texts, version, date, identifier)
            global_id = str(text['globaalID'])

        path = client.download(global_id)
        start, end = _validity(text)
        today = datetime.date.today().isoformat()
        adopted, published = _act_dates(path)
        return Retrieval(
            path=path,
            parser='riigiteataja',
            version=version,
            language='est',
            # Old texts (the 1992 Constitution) give no adoption date, only the publication date
            version_date=(adopted or published) if version == ORIGINAL else (start or None),
            meta={
                'date_document': adopted,
                'date_publication': published,
                'in_force': bool(start) and start <= today and (end is None or end >= today),
                'source': f'{RIIGI_TEATAJA}/akt/{global_id}',
            },
        )

    @staticmethod
    def _texts_by_abbreviation(client: RiigiTeatajaClient, abbreviation: str) -> list[dict[str, Any]]:
        """Texts of the act an abbreviation names; prefers the act currently in force."""
        found = [t for t in client.search(lyhend=abbreviation)
                 if (t.get('lyhend') or '').lower() == abbreviation.lower()]
        if not found:
            raise FileLoadError(f"Riigi Teataja has no act abbreviated '{abbreviation}'")
        groups: dict[int, list[dict[str, Any]]] = {}
        for text in found:
            groups.setdefault(text['terviktekstID'], []).append(text)
        # The act with an open-ended text (in force), else the one with the latest text
        group = max(groups.values(), key=lambda g: (any(_validity(t)[1] is None for t in g),
                                                    max(_validity(t)[0] for t in g)))
        return sorted(group, key=lambda t: (_validity(t)[0], t['globaalID']))

    @staticmethod
    def _choose(texts: list[dict[str, Any]], version: str, date: Optional[str], identifier: str) -> dict[str, Any]:
        if version == ORIGINAL:
            if date:
                raise UnsupportedError("A date selects a consolidated version; the original version has none")
            original = next((t for t in texts if 'algtekst' in (t.get('tekst') or '')), None)
            if original is None:
                raise FileLoadError(f"Riigi Teataja has no original text of {identifier}")
            return original
        target = date or datetime.date.today().isoformat()
        in_force = [t for t in texts if 'terviktekst' in (t.get('tekst') or '')
                    and _validity(t)[0] and _validity(t)[0] <= target
                    and (_validity(t)[1] is None or _validity(t)[1] >= target)]
        if not in_force:
            raise FileLoadError(f"No consolidated text of {identifier} in force on {target}")
        return in_force[-1]
