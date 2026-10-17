"""
Jurisdictions and the official sources tulit retrieves legislation from.

Each jurisdiction is a ``Source`` registered under its code ('EU', 'AT',
...). ``tulit.fetch`` uses them to download an act in its original or
consolidated version and convert it to legalJSON.
"""
from tulit.sources.base import (
    CONSOLIDATED, ORIGINAL, VERSIONS, Retrieval, Source, eli_pattern
)
from tulit.sources.registry import (
    get_source, list_sources, register_source, source_for_eli
)

__all__ = [
    'CONSOLIDATED', 'ORIGINAL', 'VERSIONS', 'Retrieval', 'Source', 'eli_pattern',
    'get_source', 'list_sources', 'register_source', 'source_for_eli',
]
