"""
Common interface for the jurisdictions tulit retrieves legislation from.

A ``Source`` knows how to find an act of one jurisdiction from its
identifier, download it in the original or consolidated version, and which
parser turns the download into legalJSON. ``tulit.fetch`` works the same way
for every source.
"""
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Pattern, Sequence

ORIGINAL = 'original'
CONSOLIDATED = 'consolidated'
VERSIONS = (ORIGINAL, CONSOLIDATED)


@dataclass
class Retrieval:
    """What a source downloaded and how to read it."""

    path: str
    """File, or folder for multi-file documents, to hand to the parser."""

    parser: Optional[str]
    """Format id of the parser in the parser registry; None for a document tulit cannot read, such as a
    scanned PDF without text, which ``tulit.download`` still returns."""

    version: str
    """'original' or 'consolidated'."""

    language: str
    """Language of the text, as an ISO 639-3 code (e.g. 'eng', 'deu')."""

    version_date: Optional[str] = None
    """ISO date the text is valid from (consolidated) or was published (original)."""

    meta: dict[str, Any] = field(default_factory=dict)
    """Document metadata known to the source (eli, date_document, in_force, source, ...)."""

    parser_options: dict[str, Any] = field(default_factory=dict)
    """Keyword arguments for creating the parser."""


class Source(ABC):
    """A jurisdiction and the official source tulit retrieves its legislation from."""

    code: str = ''
    """Jurisdiction code: 'EU' or the ISO 3166-1 alpha-2 code of a Member State."""

    name: str = ''
    """Human-readable name of the jurisdiction."""

    source_name: str = ''
    """Name of the official source."""

    versions: Sequence[str] = VERSIONS
    """Text versions this source can deliver."""

    languages: Sequence[str] = ()
    """ISO 639-3 codes of the languages available; the first is the default."""

    identifier_help: str = ''
    """Description of the identifiers ``retrieve`` accepts, for error messages and docs."""

    eli_patterns: Sequence[Pattern] = ()
    """Regular expressions matching this source's ELI URIs, with a named group 'id'."""

    options: Sequence[str] = ()
    """Names of the source-specific keyword options ``retrieve`` accepts."""

    version_from_identifier: bool = False
    """True when identifiers name a specific version (e.g. a consolidation document);
    ``retrieve`` then gets version=None when none is requested and returns that document."""

    @property
    def default_version(self) -> str:
        return ORIGINAL if ORIGINAL in self.versions else self.versions[0]

    @property
    def default_language(self) -> Optional[str]:
        return self.languages[0] if self.languages else None

    def identifier_from_eli(self, uri: str) -> Optional[str]:
        """Return the identifier ``retrieve`` expects for an ELI URI of this source, or None."""
        for pattern in self.eli_patterns:
            match = pattern.match(uri)
            if match:
                return match.group('id')
        return None

    @abstractmethod
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
        """
        Download an act.

        Parameters
        ----------
        identifier : str
            The act's identifier in this source (see ``identifier_help``).
        version : str or None
            'original' or 'consolidated'; None only for sources with
            ``version_from_identifier``, meaning the version the identifier names.
        date : str or None
            ISO date: the consolidated version in force on that date. None means today.
        language : str or None
            ISO 639-3 language code; None means the source's default.
        download_dir : str
            Directory for the downloaded files.
        metadata : bool
            Whether to look up document metadata (may need extra requests).
        **options
            Source-specific options.
        """


def eli_pattern(prefix: str, id_pattern: str = r'.+?') -> Pattern:
    """Compile an ELI URI pattern for ``prefix``, accepting http and https and a trailing slash."""
    prefix = re.sub(r'^https?://', '', prefix)
    return re.compile(rf'^https?://{re.escape(prefix)}(?P<id>{id_pattern})/?$')
