"""
Croatia: Narodne novine (Official Gazette).

Croatia publishes acts as adopted; there is no official consolidated text.
"""
import datetime
import re
from typing import Any, Optional

from tulit.client.state.croatia import NN_ELI, NarodneNovineClient
from tulit.sources.base import ORIGINAL, Retrieval, Source

_ELI = re.compile(r'(?:eli/sluzbeni/|^)(?P<year>\d{4})/(?P<issue>\d+)/(?P<item>\d+)(?:/|$)')
_ARTICLE_URL = re.compile(r'clanci/sluzbeni/(?P<year>\d{4})_\d{2}_(?P<issue>\d+)_(?P<item>\d+)\.html')
_CITATION = re.compile(r'^NN\s*(?P<issue>\d+)\s*/\s*(?P<year>\d{2,4})\s*[,(]?\s*(?:br\.?\s*)?(?P<item>\d+)\)?$',
                       re.IGNORECASE)


MONTHS = ('siječnja', 'veljače', 'ožujka', 'travnja', 'svibnja', 'lipnja', 'srpnja', 'kolovoza',
          'rujna', 'listopada', 'studenoga', 'prosinca')
_DATE = re.compile(r'(\d{1,2})\.\s*(%s|studenog)\s+(\d{4})' % '|'.join(MONTHS))
# A place and a date, as the adopting body signs an act
_SIGNED = re.compile(r'[A-ZČĆŠŽĐ][a-zčćšžđ]+,\s*' + _DATE.pattern)


def adoption_date(path: str) -> Optional[str]:
    """
    The last place and date in the act ('Zagreb, 14. prosinca 2018.'), when the adopting body signed it.

    None when the act is not signed with a place and date (dates in its text are not its own).
    """
    with open(path, encoding='utf-8', errors='replace') as f:
        text = f.read()
    found = _SIGNED.findall(text)
    if not found:
        return None
    day, month, year = found[-1]
    month_number = MONTHS.index('studenoga' if month == 'studenog' else month) + 1
    return datetime.date(int(year), month_number, int(day)).isoformat()


def item_reference(identifier: str) -> tuple[str, str, str]:
    """'2018/42/805', an ELI or article URL, or 'NN 42/2018, 805' -> ('2018', '42', '805')."""
    text = identifier.strip()
    match = _ELI.search(text) or _ARTICLE_URL.search(text)
    if match:
        return match.group('year'), str(int(match.group('issue'))), match.group('item')
    match = _CITATION.match(text)
    if match:
        year = match.group('year')
        if len(year) == 2:
            year = ('19' if int(year) >= 90 else '20') + year
        return year, str(int(match.group('issue'))), match.group('item')
    raise ValueError(f"'{identifier}' is not a Narodne novine reference; use year/issue/item, "
                     f"e.g. '2018/42/805', or 'NN 42/2018, 805'")


class CroatiaSource(Source):
    code = 'HR'
    name = 'Croatia'
    source_name = 'Narodne novine (Official Gazette)'
    versions = (ORIGINAL,)
    languages = ('hrv',)
    identifier_help = ("the gazette reference of an act as year/issue/item (e.g. '2018/42/805' for the "
                       "Zakon o provedbi Opće uredbe o zaštiti podataka) or 'NN 42/2018, 805'")
    eli_patterns = (
        re.compile(r'^(?P<id>https?://narodne-novine\.nn\.hr/eli/sluzbeni/\d{4}/\d+/\d+)(/.*)?$'),
        re.compile(r'^(?P<id>https?://narodne-novine\.nn\.hr/clanci/sluzbeni/\d{4}_\d{2}_\d+_\d+\.html)$'),
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
        if date:
            raise ValueError("Narodne novine publishes acts as adopted; a date cannot be selected")
        year, issue, item = item_reference(identifier)
        client = NarodneNovineClient(download_dir=download_dir)
        path = client.download(year, issue, item)
        found = client.metadata(year, issue, item) if metadata else {}
        adopted = found.get('date_document') or adoption_date(path)
        meta = {
            'eli': f'{NN_ELI}/{year}/{issue}/{item}',
            'date_document': adopted,
            'source': f'{NN_ELI}/{year}/{issue}/{item}',
        }
        if found.get('repeals'):
            meta['repeals'] = found['repeals']
        if found.get('amends'):
            meta['amends'] = found['amends']
        return Retrieval(
            path=path,
            parser='hr-nn',
            version=version,
            language='hrv',
            version_date=adopted,
            meta=meta,
        )
