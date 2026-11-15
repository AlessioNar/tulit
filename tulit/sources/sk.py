"""
Slovakia: Slov-Lex (Ministry of Justice).
"""
import datetime
import re
from typing import Any, Optional

from tulit.client.state.slovakia import PORTAL, SlovLexClient, act_path, version_in_url
from tulit.parser.exceptions import FileLoadError
from tulit.parser.xml.metalex import MetaLexParser
from tulit.sources.base import CONSOLIDATED, ORIGINAL, Retrieval, Source


class SlovakiaSource(Source):
    code = 'SK'
    name = 'Slovakia'
    source_name = 'Slov-Lex (Ministry of Justice of the Slovak Republic)'
    languages = ('slk',)
    identifier_help = "the citation number/year of an act in the Collection of Laws (e.g. '18/2018')"
    eli_patterns = (re.compile(r'^(?P<id>https?://(www\.)?slov-lex\.sk/([\w-]+/)*SK/ZZ/\d{4}/\d+(/\d{8})?/?)$'),)
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
        client = SlovLexClient(download_dir=download_dir)
        path = act_path(identifier)
        named = version_in_url(identifier)
        if version is None:
            # A URL naming a version ('.../SK/ZZ/2018/18/20180525') is that consolidated version
            version = CONSOLIDATED if named and not date else ORIGINAL
            date = date or named
        if version == ORIGINAL:
            file = client.download(path)
            version_date = None
        else:
            target = date or datetime.date.today().isoformat()
            version_date = client.version_on(path, target)
            if version_date is None:
                raise FileLoadError(f"No version of {path} in force on {target}")
            file = client.download(path, version_date)

        act = MetaLexParser().parse(file)
        if version == ORIGINAL:
            version_date = act.metadata('slovlex-owl:vyhlaseny')
        stamp = '' if version == ORIGINAL else '/' + version_date.replace('-', '')
        meta = {
            'date_document': act.metadata('slovlex-owl:schvaleny'),
            'source': f'{PORTAL}/{path}{stamp}',
        }
        return Retrieval(
            path=file,
            parser='metalex',
            version=version,
            language='slk',
            version_date=version_date,
            meta=meta,
        )
