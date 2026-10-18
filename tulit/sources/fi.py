"""
Finland: Finlex (Ministry of Justice).

The original version is the statute as published in the Statute Book
(Suomen säädöskokoelma); the consolidated version is Finlex's consolidated
text (ajantasainen lainsäädäntö). Finlex keeps a consolidated text after
each amending statute ('fin@20180817' after 817/2018): the one in force
today, or on a date, is chosen from the amendments' dates of entry into
force.
"""
import datetime
import re
from typing import Any, Optional

from lxml import etree

from tulit.client.state.finlex import FinlexClient
from tulit.parser.exceptions import FileLoadError, UnsupportedError
from tulit.sources.base import CONSOLIDATED, Retrieval, Source

FINLEX_ELI = 'http://data.finlex.fi/eli/sd'
_CITATION = re.compile(r'^(\d+(?:-\d+)?)\s*/\s*(\d{4})$')
_AKN = '{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}'
_FINLEX = '{http://data.finlex.fi/schema/finlex}'


def statute_number(identifier: str) -> tuple[str, str]:
    """'1050/2018' (number/year) -> ('2018', '1050'); 'sd/2018/1050' or a Finlex ELI -> ('2018', '1050')."""
    text = identifier.strip().rstrip('/')
    match = _CITATION.match(text)
    if match:
        return match.group(2), match.group(1)
    match = re.search(r'(?:^|/)sd/(\d{4})/(\d+(?:-\d+)?)(?:/\w+)?$', text)
    if match:
        return match.group(1), match.group(2)
    raise UnsupportedError(f"'{identifier}' is not a Finnish statute number; use number/year, e.g. '1050/2018'")


class FinlandSource(Source):
    code = 'FI'
    name = 'Finland'
    source_name = 'Finlex (Ministry of Justice)'
    languages = ('fin', 'swe')
    identifier_help = "the statute number/year (e.g. '1050/2018' for the Data Protection Act)"
    eli_patterns = (re.compile(r'^https?://data\.finlex\.fi/eli/(?P<id>sd/\d{4}/\d+)(/\w+)?/?$'),)

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
        year, number = statute_number(identifier)
        language = (language or self.default_language).lower()
        client = FinlexClient(download_dir=download_dir)
        # Finlex numbers the acts of an old decree ('39/1889', the Criminal Code, is 39-001)
        numbers = [number] if '-' in number else [number, f'{number}-001']
        if version == CONSOLIDATED:
            path, version_date, number = self._consolidated(client, year, numbers, language, date)
        else:
            if date:
                raise UnsupportedError("A date selects a consolidated version; the original version has none")
            path = None
            for candidate in numbers:
                path = client.download(year, candidate, consolidated=False, language=language)
                if path is not None:
                    number = candidate
                    break
            if path is None:
                raise FileLoadError(f"Finlex has no text of {numbers[0]}/{year} in {language}")
            version_date = _issued(path)
        consolidated = version == CONSOLIDATED
        return Retrieval(
            path=path,
            parser='akn',
            parser_options={'file_path': path},
            version=version,
            language=language,
            version_date=version_date,
            meta={
                'eli': f'{FINLEX_ELI}/{year}/{number}',
                'source': f'{FinlexClient.BASE_URL}/akn/fi/act/'
                          f"{'statute-consolidated' if consolidated else 'statute'}/{year}/{number}/{language}@",
            },
        )

    @staticmethod
    def _consolidated(client: FinlexClient, year: str, numbers: list[str], language: str,
                      date: Optional[str]) -> tuple[str, Optional[str], str]:
        """The consolidated text in force on ``date`` (today by default), its date and the statute number."""
        target = date or datetime.date.today().isoformat()
        datetime.date.fromisoformat(target)
        for number in numbers:
            versions = client.versions(year, number, language=language)
            if versions:
                break
        else:
            raise FileLoadError(f"Finlex has no consolidated text of {numbers[0]}/{year} in {language}")
        # The latest text lists every amendment and when it entered into force
        latest = client.download(year, number, consolidated=True, language=language, version=versions[-1])
        if latest is None:
            raise FileLoadError(f"Finlex has no consolidated text of {number}/{year} in {language}")
        dates = _amendment_dates(latest)
        known = sorted((dates[v], v) for v in versions if dates.get(v))
        started = [(start, v) for start, v in known if start <= target]
        if not started:
            first = f' from {known[0][0]}' if known else ''
            raise FileLoadError(f"Finlex has no consolidated text of {number}/{year} in force on {target}{first}")
        start, chosen = started[-1]
        if chosen == versions[-1]:
            return latest, start, number
        path = client.download(year, number, consolidated=True, language=language, version=chosen)
        if path is None:
            raise FileLoadError(f"Finlex has no consolidated text {chosen} of {number}/{year}")
        return path, start, number


def _issued(path: str) -> Optional[str]:
    """The date a statute was issued (FRBRWork dateIssued)."""
    found = etree.parse(path).find(f'.//{_AKN}FRBRWork/{_AKN}FRBRdate[@name="dateIssued"]')
    return found.get('date') if found is not None else None


def _amendment_dates(path: str) -> dict[str, str]:
    """
    When each consolidated version of a statute applies from, by version id: '' (the statute as first
    consolidated) from its entry into force, '20180817' from that of the amending statute 817/2018.
    """
    root = etree.parse(path).getroot()
    dates: dict[str, str] = {}
    for reference in root.iter(f'{_FINLEX}statuteReference'):
        ref = reference.find(f'{_FINLEX}ref')
        start = reference.find(f'{_FINLEX}inForce/{_FINLEX}dateEntryIntoForce')
        match = re.search(r'/statute/(\d{4})/(\d+)$', ref.get('href', '')) if ref is not None else None
        if match and start is not None and start.get('date'):
            dates[f'{match.group(1)}{match.group(2).zfill(4)}'] = start.get('date')
    for start in root.iter(f'{_FINLEX}dateEntryIntoForce'):
        if not any(etree.QName(a).localname == 'amendedBy' for a in start.iterancestors()) and start.get('date'):
            dates[''] = start.get('date')
            break
    return dates
