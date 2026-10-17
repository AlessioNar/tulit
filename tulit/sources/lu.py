"""
Luxembourg: Legilux (Service central de législation).
"""
import datetime
import re
from typing import Any, Optional

from tulit.client.state.legilux import LEGILUX_DATA, LegiluxClient, act_path
from tulit.parser.exceptions import FileLoadError
from tulit.sources.base import CONSOLIDATED, Retrieval, Source

IN_FORCE = 'http://data.legilux.public.lu/resource/authority/application-status/in-force'


class LuxembourgSource(Source):
    code = 'LU'
    name = 'Luxembourg'
    source_name = 'Legilux (Service central de législation)'
    languages = ('fra',)
    identifier_help = "a Legilux ELI path (e.g. 'etat/leg/loi/2016/07/23/n21') or ELI URI"
    eli_patterns = (re.compile(
        r'^(?P<id>https?://(data\.)?legilux\.public\.lu/eli/etat/[a-z]+/[a-z]+/\d{4}/\d{2}/\d{2}/[\w-]+)(/.*)?$'),)

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
        client = LegiluxClient(download_dir=download_dir)
        path = act_path(identifier)
        work = client.work_metadata(path) if metadata or version != CONSOLIDATED else {}

        if version == CONSOLIDATED:
            target = date or datetime.date.today().isoformat()
            dates = [d for d in client.consolidation_dates(path) if d <= target]
            if not dates:
                raise FileLoadError(f"No consolidated version of {path} on or before {target}")
            version_date = dates[-1]
            file = client.download_version(path, consolidated=version_date)
            source = f"{LEGILUX_DATA}/eli/{path}/consolide/{version_date.replace('-', '')}"
        else:
            version_date = work.get('publicationDate')
            file = client.download_version(path)
            source = f'{LEGILUX_DATA}/eli/{path}/jo'

        status = work.get('inForceStatus')
        return Retrieval(
            path=file,
            parser='akn',
            parser_options={'file_path': file},
            version=version,
            language='fra',
            version_date=version_date,
            meta={
                'eli': f'http://data.legilux.public.lu/eli/{path}/jo',
                'date_document': work.get('dateDocument'),
                'in_force': (status == IN_FORCE) if status else None,
                'source': source,
            },
        )
