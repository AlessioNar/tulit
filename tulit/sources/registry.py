"""
Registry of the jurisdictions tulit supports.
"""
from typing import Dict, List, Optional, Tuple

from tulit.sources.base import Source

_sources: Dict[str, Source] = {}
_builtins_registered = False


def register_source(source: Source) -> None:
    """Register a source under its jurisdiction code (replacing any previous one)."""
    _sources[source.code.upper()] = source


def _register_builtin_sources() -> None:
    global _builtins_registered
    if _builtins_registered:
        return
    _builtins_registered = True
    from tulit.sources.eu import EUSource
    from tulit.sources.at import AustriaSource
    from tulit.sources.dk import DenmarkSource
    from tulit.sources.nl import NetherlandsSource
    from tulit.sources.sk import SlovakiaSource
    from tulit.sources.fi import FinlandSource
    from tulit.sources.es import SpainSource
    from tulit.sources.lu import LuxembourgSource
    from tulit.sources.ie import IrelandSource
    from tulit.sources.de import GermanySource
    from tulit.sources.ee import EstoniaSource

    for source in (EUSource(), AustriaSource(), DenmarkSource(), NetherlandsSource(),
                   SlovakiaSource(), FinlandSource(), SpainSource(), LuxembourgSource(),
                   IrelandSource(), GermanySource(), EstoniaSource()):
        _sources.setdefault(source.code, source)


def get_source(code: str) -> Source:
    """
    Get the source for a jurisdiction code ('EU', 'AT', ...).

    Raises
    ------
    ValueError
        If no source is registered for that code.
    """
    _register_builtin_sources()
    source = _sources.get(code.upper())
    if source is None:
        raise ValueError(
            f"Unsupported jurisdiction '{code}'. Available: {', '.join(list_sources())}"
        )
    return source


def list_sources() -> List[str]:
    """Jurisdiction codes with a registered source."""
    _register_builtin_sources()
    return sorted(_sources)


def source_for_eli(uri: str) -> Optional[Tuple[Source, str]]:
    """Find the source whose ELI patterns match ``uri``; returns (source, identifier) or None."""
    _register_builtin_sources()
    for source in _sources.values():
        identifier = source.identifier_from_eli(uri)
        if identifier:
            return source, identifier
    return None
