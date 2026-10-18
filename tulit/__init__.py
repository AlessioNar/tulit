"""
TULIT - The Universal Legal Informatics Toolkit

A comprehensive Python library for retrieving and parsing legal documents from various 
jurisdictions and formats, with support for EU Cellar, Legifrance, and other legal databases.
"""

__version__ = "0.10.0"

from tulit import errors
from tulit.api import download, export, fetch, native_akn

__all__ = ["fetch", "download", "export", "native_akn", "errors", "__version__"]
