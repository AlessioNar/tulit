"""
Text Normalization Strategies Module

This module provides text normalization strategies following the Strategy pattern.
Different normalization algorithms can be selected at runtime, making parsers
more flexible and testable.
"""

import re
from abc import ABC, abstractmethod
from typing import List, Optional


class TextNormalizationStrategy(ABC):
    """
    Abstract base class for text normalization strategies.
    
    The Strategy pattern allows different text cleaning/normalization
    algorithms to be selected at runtime, making parsers more flexible
    and testable.
    
    Example
    -------
    >>> normalizer = WhitespaceNormalizer()
    >>> clean_text = normalizer.normalize("  multiple   spaces  ")
    "multiple spaces"
    """
    
    @abstractmethod
    def normalize(self, text: str) -> str:
        """
        Normalize the given text according to the strategy's rules.
        
        Parameters
        ----------
        text : str
            Text to normalize
        
        Returns
        -------
        str
            Normalized text
        """
        pass


class WhitespaceNormalizer(TextNormalizationStrategy):
    """
    Normalizes whitespace in text.
    
    - Removes newlines, tabs, carriage returns
    - Collapses multiple spaces to single space
    - Strips leading/trailing whitespace
    - Optionally fixes spacing before punctuation
    """
    
    def __init__(self, fix_punctuation: bool = True):
        """
        Initialize whitespace normalizer.
        
        Parameters
        ----------
        fix_punctuation : bool, optional
            Whether to remove spaces before punctuation (default: True)
        """
        self.fix_punctuation = fix_punctuation
    
    def normalize(self, text: str) -> str:
        """Remove and normalize whitespace."""
        if not text:
            return text
        
        # Remove newlines, tabs, carriage returns
        text = text.replace('\n', '').replace('\t', '').replace('\r', '')
        
        # Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        # Fix spacing before punctuation
        if self.fix_punctuation:
            text = re.sub(r'\s+([.,!?;:\'])', r'\1', text)
        
        return text


class UnicodeNormalizer(TextNormalizationStrategy):
    """
    Normalizes unicode characters in text.
    
    - Replaces non-breaking spaces with regular spaces
    - Optionally normalizes unicode to a specific form (NFC, NFD, NFKC, NFKD)
    """
    
    def __init__(self, unicode_form: Optional[str] = None, replace_nbsp: bool = True):
        """
        Initialize unicode normalizer.
        
        Parameters
        ----------
        unicode_form : str, optional
            Unicode normalization form ('NFC', 'NFD', 'NFKC', 'NFKD')
        replace_nbsp : bool, optional
            Whether to replace non-breaking spaces with regular spaces (default: True)
        """
        import unicodedata
        
        self.unicode_form = unicode_form
        self.replace_nbsp = replace_nbsp
        self._unicodedata = unicodedata
        
        if unicode_form and unicode_form not in ('NFC', 'NFD', 'NFKC', 'NFKD'):
            raise ValueError(f"Invalid unicode form: {unicode_form}")
    
    def normalize(self, text: str) -> str:
        """Normalize unicode characters."""
        if not text:
            return text
        
        # Replace non-breaking spaces
        if self.replace_nbsp:
            text = text.replace('\u00A0', ' ')
        
        # Apply unicode normalization
        if self.unicode_form:
            text = self._unicodedata.normalize(self.unicode_form, text)
        
        return text


class PatternReplacementNormalizer(TextNormalizationStrategy):
    """
    Normalizes text using regex pattern replacements.
    
    Useful for removing specific markers, formatting codes, or
    document-specific artifacts.
    """
    
    def __init__(self, patterns: List[tuple[str, str]]):
        """
        Initialize pattern replacement normalizer.
        
        Parameters
        ----------
        patterns : List[tuple[str, str]]
            List of (pattern, replacement) tuples for regex substitution
            
        Example
        -------
        >>> normalizer = PatternReplacementNormalizer([
        ...     (r'▼[A-Z]\\d*', ''),  # Remove consolidation markers
        ...     (r'^\\(\\d+\\)', '')     # Remove leading numbers in parentheses
        ... ])
        """
        self.patterns = patterns
    
    def normalize(self, text: str) -> str:
        """Apply pattern replacements."""
        if not text:
            return text
        
        for pattern, replacement in self.patterns:
            text = re.sub(pattern, replacement, text)
        
        return text


class CompositeNormalizer(TextNormalizationStrategy):
    """
    Composite strategy that applies multiple normalizers in sequence.
    
    This allows combining different normalization strategies in a specific
    order to achieve complex text cleaning operations.
    
    Example
    -------
    >>> normalizer = CompositeNormalizer([
    ...     UnicodeNormalizer(),
    ...     WhitespaceNormalizer(),
    ...     PatternReplacementNormalizer([(r'▼[A-Z]\\d*', '')])
    ... ])
    >>> clean_text = normalizer.normalize(raw_text)
    """
    
    def __init__(self, strategies: List[TextNormalizationStrategy]):
        """
        Initialize composite normalizer.
        
        Parameters
        ----------
        strategies : List[TextNormalizationStrategy]
            List of normalizers to apply in order
        """
        if not strategies:
            raise ValueError("CompositeNormalizer requires at least one strategy")
        
        self.strategies = strategies
    
    def normalize(self, text: str) -> str:
        """Apply all strategies in sequence."""
        if not text:
            return text
        
        for strategy in self.strategies:
            text = strategy.normalize(text)
        
        return text


# Predefined common normalizers for convenience
def create_standard_normalizer() -> CompositeNormalizer:
    """
    Create a standard text normalizer suitable for most legal documents.
    
    Applies:
    1. Unicode normalization (non-breaking spaces)
    2. Whitespace normalization (newlines, tabs, multiple spaces)
    3. Punctuation spacing fixes
    
    Returns
    -------
    CompositeNormalizer
        Composite normalizer with standard strategies
    """
    return CompositeNormalizer([
        UnicodeNormalizer(replace_nbsp=True),
        WhitespaceNormalizer(fix_punctuation=True)
    ])


def create_html_normalizer() -> CompositeNormalizer:
    """
    Create a normalizer for HTML-based legal documents.
    
    Applies:
    1. Pattern removal (consolidation markers)
    2. Unicode normalization
    3. Whitespace normalization
    
    Returns
    -------
    CompositeNormalizer
        Composite normalizer for HTML documents
    """
    return CompositeNormalizer([
        PatternReplacementNormalizer([
            (r'▼[A-Z]\d*', ''),  # Remove consolidation markers
        ]),
        UnicodeNormalizer(replace_nbsp=True),
        WhitespaceNormalizer(fix_punctuation=True)
    ])


def create_formex_normalizer() -> CompositeNormalizer:
    """
    Create a normalizer for Formex XML documents.
    
    Applies:
    1. Pattern removal (leading parentheses numbers)
    2. Unicode normalization
    3. Whitespace normalization
    
    Returns
    -------
    CompositeNormalizer
        Composite normalizer for Formex documents
    """
    return CompositeNormalizer([
        PatternReplacementNormalizer([
            (r'^\(\d+\)', ''),  # Remove leading numbers in parentheses
        ]),
        UnicodeNormalizer(replace_nbsp=True),
        WhitespaceNormalizer(fix_punctuation=True)
    ])
