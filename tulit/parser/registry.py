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


def get_parser_registry() -> ParserRegistry:
    """
    Get the global parser registry instance.
    
    Returns
    -------
    ParserRegistry
        The global parser registry
    """
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
    _global_registry.register(format_id, parser_class, factory, aliases)


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
    return _global_registry.create(format_id, **kwargs)
