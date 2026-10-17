"""
TULIT - The Universal Legal Informatics Toolkit

A comprehensive Python library for retrieving and parsing legal documents from various 
jurisdictions and formats, with support for EU Cellar, Legifrance, and other legal databases.
"""

__version__ = "0.7.0"

from tulit.api import fetch

__all__ = ["fetch", "__version__"]
