"""
Latvia: Latvijas Vēstnesis (likumi.lv and vestnesis.lv).

The original version is the official publication in Latvijas Vēstnesis; the
consolidated version is the systematised text on likumi.lv, as in force
today or on a date.
"""
import datetime
import re
from typing import Any, Optional

from tulit.client.state.latvia import LIKUMI, VESTNESIS, LikumiClient
from tulit.parser.exceptions import FileLoadError
from tulit.sources.base import CONSOLIDATED, ORIGINAL, Retrieval, Source

_ID = re.compile(r'^(?:https?://(?:www\.)?(?:likumi\.lv|vestnesis\.lv)/ta/(?:en/en/)?id/)?'
                 r'(?P<id>\d{1,7})(?:[-/?#].*)?$')


def act_id(identifier: str) -> str:
    """'300099', 'https://likumi.lv/ta/id/300099-fizisko-...' or a vestnesis.lv link -> '300099'."""
    match = _ID.match(identifier.strip())
    if not match:
        raise ValueError(f"'{identifier}' is not a likumi.lv identifier; use {LatviaSource.identifier_help}")
    return match.group('id')


class LatviaSource(Source):
    code = 'LV'
    name = 'Latvia'
    source_name = 'Latvijas Vēstnesis (likumi.lv, vestnesis.lv)'
    versions = (ORIGINAL, CONSOLIDATED)
    languages = ('lav',)
    identifier_help = ("the likumi.lv identifier of an act (e.g. '300099' for the Fizisko personu datu "
                       "apstrādes likums) or its likumi.lv or vestnesis.lv link")
    eli_patterns = (
        re.compile(r'^(?P<id>https?://likumi\.lv/ta/id/\d+)([-/?#].*)?$'),
        re.compile(r'^(?P<id>https?://www\.vestnesis\.lv/ta/id/\d+)([-/?#].*)?$'),
    )

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
        number = act_id(identifier)
        client = LikumiClient(download_dir=download_dir)
        current = client.download(number)
        found = client.metadata(current)
        in_force = found.get('date_in_force')
        meta = {key: found[key] for key in ('title', 'type', 'issuer', 'date_document', 'date_publication',
                                            'publication', 'op_number', 'date_in_force') if found.get(key)}

        if version == ORIGINAL:
            if date:
                raise ValueError("A date selects a consolidated version; the original version has none")
            try:
                path = client.download_publication(number)
                meta['source'] = f'{VESTNESIS}/{number}'
            except FileLoadError:
                # Early acts have no text in Latvijas Vēstnesis: the first version on likumi.lv
                versions = client.versions(current)
                path = client.download(number, in_force) if in_force and versions else current
                meta['source'] = f'{LIKUMI}/{number}'
            return Retrieval(path=path, parser='lv-likumi', version=ORIGINAL, language='lav',
                             version_date=found.get('date_document'), meta=meta)

        if date:
            datetime.date.fromisoformat(date)
            if in_force and date < in_force:
                raise FileLoadError(f"Act {number} enters into force on {in_force}, after {date}")
            path = client.download(number, date)
        else:
            path = current
        target = date or datetime.date.today().isoformat()
        # The amendment notes of a version link to the versions they made; the latest started it
        started = [d for d in client.versions(path) if d <= target]
        meta['source'] = f'{LIKUMI}/{number}'
        return Retrieval(path=path, parser='lv-likumi', version=CONSOLIDATED, language='lav',
                         version_date=started[-1] if started else in_force, meta=meta)
