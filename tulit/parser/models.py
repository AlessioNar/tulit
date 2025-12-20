"""
Domain Models Module

This module contains domain model classes representing legal document structures.
These models provide a clear, type-safe representation of legal documents,
independent of the parsing implementation.
"""

from dataclasses import dataclass
from typing import Optional, List, Any, Dict


@dataclass
class Citation:
    """Represents a citation in a legal document."""
    eId: str
    text: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert citation to dictionary format."""
        return {'eId': self.eId, 'text': self.text}


@dataclass
class Recital:
    """Represents a recital (whereas clause) in a legal document."""
    eId: str
    text: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert recital to dictionary format."""
        return {'eId': self.eId, 'text': self.text}


@dataclass
class ArticleChild:
    """
    Represents a child element of an article (paragraph, point, etc.).
    
    Attributes
    ----------
    eId : str
        Element identifier
    text : str
        Content text
    amendment : bool, optional
        Whether this is an amendment marker
    """
    eId: str
    text: str
    amendment: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert article child to dictionary format."""
        result = {'eId': self.eId, 'text': self.text}
        if self.amendment is not None:
            result['amendment'] = self.amendment
        return result


@dataclass
class Article:
    """
    Represents an article in a legal document.
    
    Attributes
    ----------
    eId : str
        Article identifier
    num : str
        Article number
    heading : str, optional
        Article heading/title
    children : List[ArticleChild]
        Child elements (paragraphs, points)
    """
    eId: str
    num: str
    heading: Optional[str] = None
    children: List[ArticleChild] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert article to dictionary format."""
        result = {
            'eId': self.eId,
            'num': self.num,
            'children': [child.to_dict() if isinstance(child, ArticleChild) else child 
                        for child in self.children]
        }
        if self.heading:
            result['heading'] = self.heading
        return result


@dataclass
class Chapter:
    """
    Represents a chapter in a legal document.
    
    Attributes
    ----------
    eId : str
        Chapter identifier
    num : str
        Chapter number
    heading : str, optional
        Chapter heading/title
    """
    eId: str
    num: str
    heading: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chapter to dictionary format."""
        result = {'eId': self.eId, 'num': self.num}
        if self.heading:
            result['heading'] = self.heading
        return result
