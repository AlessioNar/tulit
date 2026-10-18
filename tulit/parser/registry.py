"""
Parser Registry Module

This module provides a registry pattern for managing parser implementations.
It allows for dynamic parser discovery and instantiation based on format types.
"""

from typing import Dict, Type, Optional, List, Callable
from tulit.parser.exceptions import ParserError


class ParserRegistry:
    """
    Registry for managing parser implementations.

    This class implements the Registry pattern to allow dynamic parser
    discovery and instantiation. Parsers can be registered with format
    identifiers and aliases, and then retrieved by format name.

    Example
    -------
    >>> registry = ParserRegistry()
    >>> registry.register('xml', XMLParser)
    >>> parser = registry.create('xml')
    """

    def __init__(self):
        """Initialize an empty parser registry."""
        self._parsers: Dict[str, Type] = {}
        self._aliases: Dict[str, str] = {}
        self._factory_functions: Dict[str, Callable] = {}

    def register(self, format_id: str, parser_class: Type,
                 aliases: Optional[List[str]] = None) -> None:
        """
        Register a parser class for a given format.

        Parameters
        ----------
        format_id : str
            Primary identifier for this parser format
        parser_class : Type
            The parser class to register
        aliases : List[str], optional
            Alternative names for this format

        Raises
        ------
        ParserError
            If format_id or any alias is already registered
        """
        if format_id in self._parsers:
            raise ParserError(f"Parser for format '{format_id}' is already registered")

        self._parsers[format_id] = parser_class

        if aliases:
            for alias in aliases:
                if alias in self._aliases:
                    raise ParserError(f"Alias '{alias}' is already registered")
                self._aliases[alias] = format_id

    def register_factory(self, format_id: str, factory_func: Callable,
                         aliases: Optional[List[str]] = None) -> None:
        """
        Register a factory function for creating parser instances.

        This is useful when parser instantiation requires special logic
        or when dealing with parser variants.

        Parameters
        ----------
        format_id : str
            Primary identifier for this parser format
        factory_func : Callable
            Function that returns a parser instance
        aliases : List[str], optional
            Alternative names for this format
        """
        if format_id in self._factory_functions:
            raise ParserError(f"Factory for format '{format_id}' is already registered")

        self._factory_functions[format_id] = factory_func

        if aliases:
            for alias in aliases:
                if alias in self._aliases:
                    raise ParserError(f"Alias '{alias}' is already registered")
                self._aliases[alias] = format_id

    def create(self, format_id: str, *args, **kwargs):
        """
        Create a parser instance for the given format.

        Parameters
        ----------
        format_id : str
            Format identifier or alias
        *args, **kwargs
            Arguments to pass to parser constructor

        Returns
        -------
        Parser
            An instance of the requested parser

        Raises
        ------
        ParserError
            If format_id is not registered
        """
        # Resolve aliases
        actual_format = self._aliases.get(format_id, format_id)

        # Try factory function first
        if actual_format in self._factory_functions:
            return self._factory_functions[actual_format](*args, **kwargs)

        # Fall back to direct class instantiation
        if actual_format not in self._parsers:
            raise ParserError(
                f"No parser registered for format '{format_id}'. "
                f"Available formats: {', '.join(self.list_formats())}"
            )

        parser_class = self._parsers[actual_format]
        return parser_class(*args, **kwargs)

    def list_formats(self) -> List[str]:
        """
        List all registered format identifiers.

        Returns
        -------
        List[str]
            List of format identifiers (not including aliases)
        """
        formats = set(self._parsers.keys())
        formats.update(self._factory_functions.keys())
        return sorted(formats)

    def list_aliases(self) -> Dict[str, str]:
        """
        Get mapping of aliases to their primary format identifiers.

        Returns
        -------
        Dict[str, str]
            Mapping of alias -> format_id
        """
        return self._aliases.copy()

    def is_registered(self, format_id: str) -> bool:
        """
        Check if a format or alias is registered.

        Parameters
        ----------
        format_id : str
            Format identifier or alias to check

        Returns
        -------
        bool
            True if format is registered
        """
        actual_format = self._aliases.get(format_id, format_id)
        return (actual_format in self._parsers or
                actual_format in self._factory_functions)


# Global registry instance
_global_registry = ParserRegistry()
_builtins_registered = False


def _create_akn_parser(file_path: Optional[str] = None, format: Optional[str] = None):
    """Create an Akoma Ntoso parser, detecting the variant from file_path when given."""
    from tulit.parser.xml.akomantoso import create_akn_parser
    if format is None and file_path is None:
        format = 'akn'
    return create_akn_parser(file_path=file_path, format=format)


def _register_builtin_parsers(registry: ParserRegistry) -> None:
    """
    Register the parsers shipped with tulit.

    Imports happen here rather than at module level because the parser
    modules themselves import this module.
    """
    from tulit.parser.xml.formex import Formex4Parser
    from tulit.parser.xml.boe import BOEXMLParser
    from tulit.parser.xml.akomantoso import (
        AKN4EUParser, GermanLegalDocMLParser, LuxembourgAKNParser
    )
    from tulit.parser.html.cellar import (
        CellarHTMLParser, CellarStandardHTMLParser, ProposalHTMLParser
    )
    from tulit.parser.html.veneto import VenetoHTMLParser
    from tulit.parser.json.legifrance import LegifranceParser
    from tulit.parser.xml.ris import RISParser
    from tulit.parser.xml.bgbl_at import BGBlParser
    from tulit.parser.xml.lexdania import LexDaniaParser
    from tulit.parser.html.retsinformation import RetsinformationHTMLParser
    from tulit.parser.xml.bwb import BWBParser
    from tulit.parser.xml.metalex import MetaLexParser
    from tulit.parser.xml.boe_consolidated import BOEConsolidatedParser
    from tulit.parser.xml.irish import IrishActParser
    from tulit.parser.xml.riigiteataja import RiigiTeatajaParser
    from tulit.parser.html.sejm import SejmELIParser
    from tulit.parser.html.riksdagen import RiksdagenSFSParser
    from tulit.parser.html.narodne_novine import NarodneNovineParser
    from tulit.parser.json.esbirka import EsbirkaParser
    from tulit.parser.pdf.malta import MaltaPDFParser
    from tulit.parser.pdf.portugal import DiarioRepublicaParser
    from tulit.parser.json.dre_consolidated import DREConsolidatedParser
    from tulit.parser.html.likumi import LikumiParser
    from tulit.parser.html.ejustice import EJusticeParser
    from tulit.parser.pdf.cyprus import CyprusGazetteParser
    from tulit.parser.html.darzhaven_vestnik import DarzhavenVestnikParser
    from tulit.parser.xml.dila import DilaParser
    from tulit.parser.xml.legislatie_ro import LegislatieParser
    from tulit.parser.html.pisrs import PisrsParser
    from tulit.parser.html.njt import NJTParser
    from tulit.parser.html.etar import TARParser
    from tulit.parser.pdf.greece import GovernmentGazetteParser
    from tulit.parser.pdf.sweden import SFSPDFParser
    from tulit.parser.xml.akomantoso.normattiva import NormattivaAKNParser
    from tulit.parser.xml.akomantoso.leg import LegParser

    registry.register('formex', Formex4Parser, aliases=['fmx4', 'formex4'])
    registry.register_factory('akn', _create_akn_parser, aliases=['akomantoso', 'akoma-ntoso'])
    registry.register('akn4eu', AKN4EUParser)
    registry.register('leg', LegParser, aliases=['leos'])
    registry.register('legaldocml-de', GermanLegalDocMLParser, aliases=['akn-de'])
    registry.register('akn-lu', LuxembourgAKNParser)
    registry.register('cellar-xhtml', CellarHTMLParser, aliases=['xhtml'])
    registry.register('cellar-html', CellarStandardHTMLParser, aliases=['html'])
    registry.register('eu-proposal', ProposalHTMLParser, aliases=['proposal'])
    registry.register('boe', BOEXMLParser)
    registry.register('veneto', VenetoHTMLParser)
    registry.register('legifrance', LegifranceParser)
    registry.register('ris', RISParser, aliases=['at-ris'])
    registry.register('ris-bgbl', BGBlParser, aliases=['at-bgbl'])
    registry.register('lexdania', LexDaniaParser, aliases=['dk-lexdania'])
    registry.register('retsinformation-html', RetsinformationHTMLParser)
    registry.register('bwb', BWBParser, aliases=['nl-bwb'])
    registry.register('metalex', MetaLexParser, aliases=['sk-metalex'])
    registry.register('boe-consolidated', BOEConsolidatedParser, aliases=['es-boe-consolidated'])
    registry.register('ie-act', IrishActParser, aliases=['isb'])
    registry.register('riigiteataja', RiigiTeatajaParser, aliases=['ee-rt'])
    registry.register('pl-eli', SejmELIParser, aliases=['sejm'])
    registry.register('se-sfs', RiksdagenSFSParser, aliases=['riksdagen'])
    registry.register('se-sfs-pdf', SFSPDFParser, aliases=['sfs-pdf'])
    registry.register('hr-nn', NarodneNovineParser, aliases=['narodne-novine'])
    registry.register('cz-esbirka', EsbirkaParser, aliases=['esbirka'])
    registry.register('mt-pdf', MaltaPDFParser, aliases=['malta'])
    registry.register('pt-dre-pdf', DiarioRepublicaParser, aliases=['dre'])
    registry.register('pt-dre-consolidated', DREConsolidatedParser, aliases=['dre-consolidated'])
    registry.register('lv-likumi', LikumiParser, aliases=['likumi'])
    registry.register('be-ejustice', EJusticeParser, aliases=['ejustice', 'justel'])
    registry.register('cy-gazette-pdf', CyprusGazetteParser, aliases=['cy-gazette'])
    registry.register('bg-dv', DarzhavenVestnikParser, aliases=['darzhaven-vestnik'])
    registry.register('fr-dila', DilaParser, aliases=['dila', 'legi', 'jorf'])
    registry.register('ro-legislatie', LegislatieParser, aliases=['legislatie-just'])
    registry.register('si-pisrs', PisrsParser, aliases=['pisrs'])
    registry.register('hu-njt', NJTParser, aliases=['njt'])
    registry.register('lt-tar', TARParser, aliases=['tar'])
    registry.register('gr-fek-pdf', GovernmentGazetteParser, aliases=['fek'])
    registry.register('it-normattiva', NormattivaAKNParser, aliases=['normattiva'])


def get_parser_registry() -> ParserRegistry:
    """
    Get the global parser registry instance.

    The parsers shipped with tulit are registered on first use.

    Returns
    -------
    ParserRegistry
        The global parser registry
    """
    global _builtins_registered
    if not _builtins_registered:
        _builtins_registered = True
        _register_builtin_parsers(_global_registry)
    return _global_registry


def register_parser(format_id: str, parser_class: Type = None,
                    factory: Callable = None,
                    aliases: Optional[List[str]] = None) -> None:
    """
    Convenience function to register a parser in the global registry.

    Parameters
    ----------
    format_id : str
        Primary identifier for the parser
    parser_class : Type, optional
        Parser class to register
    factory : Callable, optional
        Factory function that returns a parser instance
    aliases : List[str], optional
        Alternative names for the parser

    Example
    -------
    >>> register_parser('xml', XMLParser, aliases=['xmldoc'])
    """
    if (parser_class is None) == (factory is None):
        raise ParserError("Provide exactly one of parser_class or factory")
    registry = get_parser_registry()
    if factory is not None:
        registry.register_factory(format_id, factory, aliases)
    else:
        registry.register(format_id, parser_class, aliases)


def get_parser(format_id: str, **kwargs):
    """
    Convenience function to get a parser from the global registry.

    Parameters
    ----------
    format_id : str
        Parser format identifier or alias
    **kwargs : dict
        Arguments to pass to parser constructor/factory

    Returns
    -------
    Parser
        Instantiated parser

    Example
    -------
    >>> parser = get_parser('xml', schema_path='schema.xsd')
    """
    return get_parser_registry().create(format_id, **kwargs)
