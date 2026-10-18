"""
TULIT - The Universal Legal Informatics Toolkit

Retrieves the legislation of the EU and its 27 Member States from their official
sources, as adopted and as in force on any date, as legalJSON; exports it to
Akoma Ntoso 3.0 and LEOS packages.
"""

__version__ = "1.0.0"

from tulit import errors
from tulit.api import download, export, fetch, native_akn

__all__ = ["fetch", "download", "export", "native_akn", "errors", "__version__"]
