"""
Lithuania: Register of Legal Acts (Teisės aktų registras), through e-seimas.lrs.lt.

The original version is the act as published in the Register of Legal Acts;
the consolidated version is the Register's consolidated text (suvestinė
redakcija) in force today or on a date.
"""
import datetime
import re
from typing import Any, Optional

from tulit.client.state.lithuania import ESEIMAS, EseimasClient
from tulit.parser.exceptions import FileLoadError, UnsupportedError
from tulit.sources.base import CONSOLIDATED, ORIGINAL, Retrieval, Source

_TAR = re.compile(r'^(?:TAR\s*,?\s*|i\.\s*k\.\s*)?(?P<code>\d{4}-\d{5})$', re.IGNORECASE)
_NUMBER = re.compile(r'^(?:Nr\.\s*)?(?P<number>[IVXL]+-\d+)$')
_DOCUMENT = re.compile(r'^(?P<id>TAIS\.\d+|[0-9a-f]{32})$')
_LINK = re.compile(r'^https?://e-seimas\.lrs\.lt/portal/legalAct/lt/TAD/(?P<id>TAIS\.\d+|[0-9a-f]{32})'
                   r'(?:/(?P<version>[A-Za-z]{10}|asr))?(?:[/?#].*)?$')
_DATE = re.compile(r'(\d{4}-\d{2}-\d{2})')


class LithuaniaSource(Source):
    code = 'LT'
    name = 'Lithuania'
    source_name = 'Register of Legal Acts (Teisės aktų registras), via e-seimas.lrs.lt'
    versions = (ORIGINAL, CONSOLIDATED)
    languages = ('lit',)
    version_from_identifier = True
    identifier_help = ("the TAR identification code of an act (e.g. '2018-11733'), the number of a Seimas act "
                       "(e.g. 'I-1374' for the Asmens duomenų teisinės apsaugos įstatymas), its e-seimas "
                       "document id ('TAIS.29193') or its e-seimas link")
    eli_patterns = (re.compile(r'^(?P<id>https?://e-seimas\.lrs\.lt/portal/legalAct/lt/TAD/[0-9A-Za-z.]+'
                               r'(?:/[A-Za-z]{10}|/asr)?)(?:[?#].*)?$'),)

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
        client = EseimasClient(download_dir=download_dir)
        document, named_version = self._document(client, identifier.strip())
        if version is None:
            version = CONSOLIDATED if named_version else ORIGINAL
        found = client.metadata(document) if metadata else {}
        meta: dict[str, Any] = {key: found[key] for key in ('type', 'issuer', 'number', 'tar', 'publication',
                                                            'date_document', 'date_in_force') if found.get(key)}
        publication = _DATE.search(found.get('publication', ''))
        if publication:
            meta['date_publication'] = publication.group(1)

        if version == ORIGINAL:
            if date:
                raise UnsupportedError("A date selects a consolidated version; the original version has none")
            meta['source'] = f'{ESEIMAS}/portal/legalAct/lt/TAD/{document}'
            return Retrieval(path=client.download(document), parser='lt-tar', version=ORIGINAL, language='lit',
                             version_date=found.get('date_document'), meta=meta)

        versions = client.versions(document)
        if not versions:
            raise FileLoadError(f"The Register of Legal Acts has no consolidated version of {identifier}; an "
                                f"amending act's changes are consolidated into the act it amends")
        if named_version and named_version != 'asr' and not date:
            chosen = next(((start, v) for start, v in versions if v == named_version), None)
            if chosen is None:
                raise FileLoadError(f"{identifier} names no consolidated version of {document}")
        else:
            target = date or datetime.date.today().isoformat()
            datetime.date.fromisoformat(target)
            started = [(start, v) for start, v in versions if start <= target]
            if not started:
                raise FileLoadError(f"The first consolidated version of {identifier} applies from {versions[0][0]}, "
                                    f"after {target}")
            chosen = started[-1]
        meta['source'] = f'{ESEIMAS}/portal/legalAct/lt/TAD/{document}/{chosen[1]}'
        return Retrieval(path=client.download_version(document, chosen[1]), parser='lt-tar', version=CONSOLIDATED,
                         language='lit', version_date=chosen[0], meta=meta)

    def _document(self, client: EseimasClient, identifier: str) -> tuple[str, Optional[str]]:
        """The e-seimas document id an identifier names, and the consolidated version it names, if any."""
        match = _LINK.match(identifier)
        if match:
            return match.group('id'), match.group('version')
        if _DOCUMENT.match(identifier):
            return identifier, None
        match = _TAR.match(identifier)
        if match:
            return client.find('registration', match.group('code'))['id'], None
        match = _NUMBER.match(identifier)
        if match:
            return client.find('number', match.group('number'))['id'], None
        raise UnsupportedError(f"'{identifier}' is not a Lithuanian act identifier; use {self.identifier_help}")
