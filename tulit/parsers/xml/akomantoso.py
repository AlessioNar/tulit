"""
Akoma Ntoso Parsers Module (Backward Compatibility)

⚠️ DEPRECATED: This module is maintained for backward compatibility only.
   Please use the new modular structure:
   
   from tulit.parsers.xml.akomantoso import (
       AkomaNtosoParser, AKN4EUParser, GermanLegalDocMLParser,
       LuxembourgAKNParser, create_akn_parser, detect_akn_format
   )

This module re-exports all classes and functions from the new akomantoso
package structure to maintain compatibility with existing code.
"""

# Re-export everything from the new module structure
from tulit.parsers.xml.akomantoso import (
    AkomaNtosoParser,
    AKN4EUParser,
    GermanLegalDocMLParser,
    LuxembourgAKNParser,
    detect_akn_format,
    create_akn_parser,
    register_akn_parsers,
)

# Re-export for backward compatibility
__all__ = [
    'AkomaNtosoParser',
    'AKN4EUParser',
    'GermanLegalDocMLParser',
    'LuxembourgAKNParser',
    'detect_akn_format',
    'create_akn_parser',
]
