"""
Belgium: Moniteur belge / Belgisch Staatsblad and Justel (eJustice).

The original version is the act as published in the Moniteur belge (in
electronic form since June 1997); the consolidated version is Justel's text,
in force today or on a date, chosen among its archived versions. Both in
French and Dutch, the official languages of the federal State.
"""
import datetime
import re
from typing import Any, Optional

from tulit.client.state.belgium import TYPES, EJusticeClient
from tulit.parser.exceptions import FileLoadError
from tulit.sources.base import CONSOLIDATED, ORIGINAL, Retrieval, Source

_DUTCH = {dutch: french for french, dutch in TYPES.items()}
_ELI = re.compile(r'^(?:https?://www\.ejustice\.just\.fgov\.be/eli/)?(?P<type>[a-z]+)/(?P<year>\d{4})/(?P<month>\d{2})/'
                  r'(?P<day>\d{2})/(?P<numac>\d{4}[0-9A-Z]\d{5})(?:/(?:justel|moniteur|staatsblad))?/?$')


def act_reference(identifier: str) -> tuple[str, str, str, Optional[str]]:
    """
    'loi/2018/07/30/2018040581' or its ELI (French or Dutch) -> ('loi', '2018-07-30', '2018040581', language).

    The language is the one the ELI is written in ('nld' for wet, decreet, ...), None when it says none.
    """
    match = _ELI.match(identifier.strip())
    if not match or (match.group('type') not in TYPES and match.group('type') not in _DUTCH):
        raise ValueError(f"'{identifier}' is not a Belgian ELI; use {BelgiumSource.identifier_help}")
    doc_type = match.group('type')
    language = 'nld' if doc_type in _DUTCH else ('fra' if identifier.strip().startswith('http') else None)
    date = f"{match.group('year')}-{match.group('month')}-{match.group('day')}"
    return _DUTCH.get(doc_type, doc_type), date, match.group('numac'), language


class BelgiumSource(Source):
    code = 'BE'
    name = 'Belgium'
    source_name = 'Moniteur belge / Belgisch Staatsblad and Justel (FPS Justice)'
    versions = (ORIGINAL, CONSOLIDATED)
    languages = ('fra', 'nld')
    identifier_help = ("the ELI of an act (e.g. 'https://www.ejustice.just.fgov.be/eli/loi/2018/07/30/2018040581', "
                       "or in Dutch .../eli/wet/...) or its type, date and NUMAC as 'loi/2018/07/30/2018040581'")
    eli_patterns = (re.compile(r'^(?P<id>https?://www\.ejustice\.just\.fgov\.be/eli/[a-z]+/\d{4}/\d{2}/\d{2}/'
                               r'\d{4}[0-9A-Z]\d{5})(/.*)?$'),)

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
        doc_type, act_date, numac, eli_language = act_reference(identifier)
        language = language or eli_language or self.default_language
        client = EJusticeClient(download_dir=download_dir)
        meta: dict[str, Any] = {'eli': client.eli(doc_type, act_date, numac, language)}

        if version == ORIGINAL:
            if date:
                raise ValueError("A date selects a consolidated version; the original version has none")
            try:
                path = client.download(doc_type, act_date, numac, language)
                meta['source'] = client.eli(doc_type, act_date, numac, language, 'publication')
            except FileLoadError as e:
                if 'only as PDF' not in str(e):
                    raise
                # Published before June 1997, as PDF only: Justel's first version of the text
                path = self._first_justel_version(client, doc_type, act_date, numac, language)
                meta['source'] = client.eli(doc_type, act_date, numac, language, 'justel')
            if metadata:
                try:
                    found = client.metadata(client.download(doc_type, act_date, numac, language, consolidated=True))
                    meta.update({key: value for key, value in found.items() if value})
                except FileLoadError:
                    # Not every publication is consolidated by Justel
                    pass
            return Retrieval(path=path, parser='be-ejustice', version=ORIGINAL, language=language,
                             version_date=act_date, meta=meta)

        current = client.download(doc_type, act_date, numac, language, consolidated=True)
        found = client.metadata(current)
        meta.update({key: value for key, value in found.items() if value})
        meta['source'] = client.eli(doc_type, act_date, numac, language, 'justel')
        target = date or datetime.date.today().isoformat()
        datetime.date.fromisoformat(target)
        in_force = found.get('date_in_force')
        if date and in_force and date < in_force:
            raise FileLoadError(f"{identifier} enters into force on {in_force}, after {date}")

        path, start = current, None
        link = client.archive_link(current)
        if link:
            number, url = link
            latest = client.download_archive(url, numac, language, number)
            archives = client.archives(latest)
            if archives and target < archives[-1][1]:
                # An archived version: the first one still in force on the date
                chosen = next(n for n, until in archives if target < until)
                path = latest if chosen == number else client.download_archive(url, numac, language, chosen)
                if self._partial(client, path, current):
                    raise FileLoadError(f"Justel's version of {identifier} in force on {target} (archive {chosen}) "
                                        f"holds only the articles changed then, not the whole text")
                earlier = [until for n, until in archives if n < chosen]
                start = earlier[-1] if earlier else in_force
            elif archives:
                start = archives[-1][1]
        else:
            start = in_force
        return Retrieval(path=path, parser='be-ejustice', version=CONSOLIDATED, language=language,
                         version_date=start, meta=meta)

    @staticmethod
    def _first_justel_version(client: EJusticeClient, doc_type: str, act_date: str, numac: str,
                              language: str) -> str:
        current = client.download(doc_type, act_date, numac, language, consolidated=True)
        link = client.archive_link(current)
        if not link:
            return current
        first = client.download_archive(link[1], numac, language, 1)
        if BelgiumSource._partial(client, first, current):
            raise FileLoadError(f"The Moniteur belge publishes {doc_type}/{act_date}/{numac} only as PDF, and Justel's "
                                f"first version holds only the articles changed then, not the whole text")
        return first

    @staticmethod
    def _partial(client: EJusticeClient, path: str, current: str) -> bool:
        """Whether a Justel archive holds far fewer articles than the current text."""
        return client.article_count(path) < client.article_count(current) / 2
