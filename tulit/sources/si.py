"""
Slovenia: PISRS (Pravno-informacijski sistem Republike Slovenije).

The original version is the act's text as published in the Official Gazette
(Uradni list RS), as PISRS gives it; the consolidated version is PISRS's
unofficial consolidated text (neuradno prečiščeno besedilo) that applies on
a date, today by default.
"""
import datetime
import re
from typing import Any, Optional

from tulit.client.state.slovenia import PISRS, PisrsClient
from tulit.parser.exceptions import FileLoadError
from tulit.sources.base import CONSOLIDATED, ORIGINAL, Retrieval, Source

_ID = re.compile(r'^(?:https?://(?:www\.)?pisrs\.si/\S*?[?&/]id=)?(?P<id>[A-Z]{4}\d{1,6})(?:[&#].*)?$')
_CITATION = re.compile(r'^(?:Uradni list RS|Ur\. ?l\. RS|UL RS),?\s*(?:št\.\s*)?(?P<number>\d{1,4})/(?P<year>\d{2,4})$',
                       re.IGNORECASE)
_SOP = re.compile(r'^(?:https?://\S*?(?:vsebina/|sop=))?(?P<sop>\d{4}-\d{2}-\d{4})(?:[&#?].*)?$')
_ABBREVIATION = re.compile(r'^[A-ZČŠŽ][A-Za-zČŠŽčšž]{1,15}(?:-\d+[A-Z]?)?$')


def _year(text: str) -> str:
    if len(text) == 4:
        return text
    return ('19' if int(text) > 90 else '20') + text


_PUBLISHED = re.compile(r'\(Uradni list RS, št\. [^)]*?z dne (\d{1,2})\. ?(\d{1,2})\. ?(\d{4})\)')


def _consolidates_until(path: str) -> Optional[str]:
    """ISO date the last act a consolidated version includes was published, from its notice ('... obsega:')."""
    with open(path, encoding='utf-8', errors='replace') as f:
        notice = re.sub(r'<[^>]+>', ' ', f.read()).split('obsega:', 1)
    if len(notice) < 2:
        return None
    # The notice ends where the act's title begins
    listed = _PUBLISHED.findall(' '.join(notice[1].split())[:20000].split('neuradno prečiščeno besedilo št.')[0])
    dates = [f'{year}-{int(month):02d}-{int(day):02d}' for day, month, year in listed]
    return max(dates) if dates else None


def _validity(record: dict[str, Any]) -> dict[str, Any]:
    return record.get('evidencniPodatki') or {}


class SloveniaSource(Source):
    code = 'SI'
    name = 'Slovenia'
    source_name = 'PISRS (Pravno-informacijski sistem Republike Slovenije)'
    versions = (ORIGINAL, CONSOLIDATED)
    languages = ('slv',)
    identifier_help = ("the PISRS id of an act (e.g. 'ZAKO7959' for the Zakon o varstvu osebnih podatkov) or its "
                       "link, its abbreviation ('ZVOP-2'), its number in the Official Gazette ('2022-01-4187') or "
                       "Uradni list link, or its Gazette citation ('Uradni list RS, št. 163/22') when that issue "
                       "published no other act")
    eli_patterns = (re.compile(r'^(?P<id>https?://(?:www\.)?pisrs\.si/\S*?[?&/]'
                               r'(?:id=[A-Z]{4}\d{1,6}|sop=\d{4}-\d{2}-\d{4}))'),
                    re.compile(r'^(?P<id>https?://(?:www\.)?uradni-list\.si/\S*?vsebina/\d{4}-\d{2}-\d{4})'))

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
        client = PisrsClient(download_dir=download_dir)
        sop = _SOP.match(identifier.strip())
        if sop:
            record = client.record(sop.group('sop'), key='sop')
            act_id = _validity(record).get('zunanjiID') or sop.group('sop')
        else:
            act_id = self._act_id(client, identifier.strip())
            record = client.record(act_id)
        details = _validity(record)
        versions = client.versions(record)
        if not versions:
            raise FileLoadError(f"PISRS has no text of {act_id}")
        in_force = details.get('veljaOd')

        if version == ORIGINAL:
            if date:
                raise ValueError("A date selects a consolidated version; the original version has none")
            chosen = versions[0]
            version_date = details.get('objavljeno') or details.get('sprejeto')
        else:
            target = date or datetime.date.today().isoformat()
            datetime.date.fromisoformat(target)
            if date and in_force and date < in_force:
                raise FileLoadError(f"{act_id} enters into force on {in_force}, after {date}")
            # The latest version that applies on the date. PISRS dates only recent versions: an older one
            # cannot apply before the last act it consolidates was published, which its notice lists.
            chosen = versions[0]
            for candidate in versions[1:]:
                start = candidate['date']
                if not start and date:
                    start = _consolidates_until(client.download(act_id, candidate))
                if start and start > target:
                    break
                chosen = candidate
            version_date = chosen['date'] or (in_force if chosen['number'] == 0 else None)

        path = client.download(act_id, chosen)
        citation = re.sub(r'<[^>]+>', '', details.get('citat') or '') or None
        meta = {
            'source': f'{PISRS}/pregledPredpisa?id={act_id}',
            'pisrs_id': act_id,
            'title': details.get('naslov'),
            'abbreviation': details.get('kratica'),
            'type': details.get('vrstaAkta'),
            'citation': citation,
            'date_document': details.get('sprejeto'),
            'date_publication': details.get('objavljeno'),
            'date_in_force': in_force,
            'date_no_longer_in_force': details.get('veljaDo'),
            'issuer': details.get('organSprejetja'),
            'consolidation': chosen['name'] if chosen['number'] else None,
        }
        return Retrieval(path=path, parser='si-pisrs', version=version, language='slv', version_date=version_date,
                         meta={key: value for key, value in meta.items() if value})

    @staticmethod
    def _act_id(client: PisrsClient, identifier: str) -> str:
        match = _ID.match(identifier)
        if match:
            return match.group('id')
        match = _CITATION.match(identifier)
        if match:
            found = client.search(issue=(match.group('number'), _year(match.group('year'))))
            if len(found) == 1:
                return found[0]['zunanjiId']
            if not found:
                raise FileLoadError(f"PISRS has no act published in {identifier}")
            listed = '; '.join(f"{x['zunanjiId']}: {x['nazivAkta']}" for x in found[:12])
            raise ValueError(f"{identifier} published {len(found)} acts; give the PISRS id of one: {listed}")
        if _ABBREVIATION.match(identifier):
            found = [x for x in client.search(title=identifier)
                     if (x.get('nazivAkta') or '').lower().endswith(f'({identifier.lower()})')]
            if not found:
                raise FileLoadError(f"PISRS has no act abbreviated {identifier}")
            # Prefer the act in force
            found.sort(key=lambda x: 'Veljaven' not in ((x.get('semafor') or {}).get('naziv') or ''))
            return found[0]['zunanjiId']
        raise ValueError(f"'{identifier}' is not a Slovenian act identifier; use {SloveniaSource.identifier_help}")
