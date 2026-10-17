"""
Ireland: Irish Statute Book (Office of the Attorney General) and Revised Acts (Law Reform Commission).
"""
import datetime
import re
from typing import Any, Optional

from lxml import etree

from tulit.client.state.irishstatutebook import IrishStatuteBookClient
from tulit.parser.exceptions import FileLoadError
from tulit.sources.base import CONSOLIDATED, Retrieval, Source

ISB_ELI = 'http://www.irishstatutebook.ie/eli'
_CITATION = re.compile(r'^(?:Act\s+)?(?:No\.?\s*)?(\d+)\s*(?:/|of)\s*(\d{4})$', re.IGNORECASE)
_UPDATED = re.compile(r'Updated to (\d{1,2} \w+ \d{4})')


def act_number(identifier: str) -> tuple[str, str]:
    """'7/2018', 'Act 7 of 2018' or 'eli/2018/act/7' -> ('2018', '7')."""
    text = identifier.strip().rstrip('/')
    match = _CITATION.match(text)
    if match:
        return match.group(2), match.group(1)
    match = re.search(r'(?:^|/)(\d{4})/act/(\d+)', text)
    if match:
        return match.group(1), match.group(2)
    raise ValueError(f"'{identifier}' is not an Irish Act number; use number/year, e.g. '7/2018'")


def _iso(text: Optional[str]) -> Optional[str]:
    """'20180524' or '16 July 2026' -> ISO date."""
    if not text:
        return None
    text = text.strip()
    if re.fullmatch(r'\d{8}', text):
        return f'{text[:4]}-{text[4:6]}-{text[6:]}'
    try:
        return datetime.datetime.strptime(text, '%d %B %Y').date().isoformat()
    except ValueError:
        return None


class IrelandSource(Source):
    code = 'IE'
    name = 'Ireland'
    source_name = 'Irish Statute Book (Acts as enacted) and Law Reform Commission (Revised Acts)'
    languages = ('eng',)
    identifier_help = "the Act number/year (e.g. '7/2018' for the Data Protection Act 2018)"
    eli_patterns = (re.compile(
        r'^(?P<id>https?://(www\.irishstatutebook\.ie|revisedacts\.lawreform\.ie)/eli/\d{4}/act/\d+)(/.*)?$'),)

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
            raise ValueError("Revised Acts are kept up to date as a single version; a date cannot be selected")
        year, number = act_number(identifier)
        consolidated = version == CONSOLIDATED
        client = IrishStatuteBookClient(download_dir=download_dir)
        path = client.download(year, number, status='revised' if consolidated else 'enacted')
        if path is None:
            raise FileLoadError(
                f"No {'Revised' if consolidated else 'enacted'} XML for Act {number} of {year}")

        root = etree.parse(path).getroot()
        enacted = _iso(root.findtext('metadata/dateofenactment'))
        version_date = enacted
        if consolidated:
            front = ' '.join(''.join(root.find('frontmatter').itertext()).split()) \
                if root.find('frontmatter') is not None else ''
            match = _UPDATED.search(front)
            version_date = _iso(match.group(1)) if match else None
        base = client.REVISED_URL if consolidated else client.BASE_URL
        return Retrieval(
            path=path,
            parser='ie-act',
            version=version,
            language='eng',
            version_date=version_date,
            meta={
                'eli': f'{ISB_ELI}/{year}/act/{number}',
                'date_document': enacted,
                'source': f"{base}/{year}/act/{number}/{'revised' if consolidated else 'enacted'}/en/html",
            },
        )
