"""
Helpers for building the legalJSON body: divisions, articles and their children.

Parsers that read a document element by element (rather than through a
format-specific strategy) use ``BodyBuilder`` to get the same output as the
Formex parser: typed divisions with parent links, the nested ``structure``
skeleton, and eIds following the EU subdivision authority table used in ELI
subdivision URIs (``prt_``, ``tit_``, ``cpt_``, ``sct_``, ``sbs_``, ``art_``, ``par_``, ``unp_``).
"""
import re
from typing import Any, Iterable, Optional

from lxml import etree

# Division type -> (eId prefix, rank). Lower ranks enclose higher ones.
DIVISION_TYPES = {
    'part': ('prt', 0),
    'title': ('tit', 1),
    'chapter': ('cpt', 2),
    'section': ('sct', 3),
    'subsection': ('sbs', 4),
}
GENERIC_DIVISION = ('div', 5)

_TOKEN = re.compile(r'[0-9]+[a-zA-Z]*|\b[IVXLCDM]+\b|\b[a-zA-Z]\b')


def eid_token(num: Optional[str]) -> Optional[str]:
    """
    The number part of a published number, usable in an eId.

    '5. Abschnitt' -> '5', 'Chapter III' -> 'III', '§ 35a' -> '35a',
    'Art. 2' -> '2', '(1a)' -> '1a'. Returns None when there is no number.
    """
    if not num:
        return None
    match = _TOKEN.search(num.replace('§', ' '))
    return match.group(0) if match else None


def element_text(element: etree._Element, block_tags: Iterable[str],
                 skip_tags: Iterable[str] = ()) -> str:
    """
    Text of an XML element with whitespace normalised.

    Elements whose local name is in ``block_tags`` are separated by a space
    from what follows, so '<num>1.</num><p>Text</p>' reads '1. Text'; inline
    elements are joined as-is. Elements in ``skip_tags`` are left out, but
    their tail text is kept.
    """
    blocks, skip = set(block_tags), set(skip_tags)
    parts: list[str] = []

    def walk(node: etree._Element) -> None:
        if node.text:
            parts.append(node.text)
        for child in node:
            if isinstance(child.tag, str):
                name = etree.QName(child).localname
                if name not in skip:
                    walk(child)
                    tail = (child.tail or '').lstrip()
                    if name in blocks and not tail.startswith((',', ';', '.', ':', ')', ']')):
                        parts.append(' ')
            if child.tail:
                parts.append(child.tail)

    walk(element)
    return ' '.join(''.join(parts).split())


class ChildrenBuilder:
    """Collects the children of one article, numbering them par_N / unp_N."""

    def __init__(self) -> None:
        self.children: list[dict[str, Any]] = []
        self._used: set[str] = set()
        self._unnumbered = 0

    def add(self, text: str, number: Optional[str] = None) -> dict[str, Any]:
        """Start a new child; ``number`` is the published paragraph number, if any."""
        token = eid_token(number)
        if token:
            eid = self._unique(f'par_{token.lower()}')
        else:
            self._unnumbered += 1
            eid = self._unique(f'unp_{self._unnumbered}')
        child = {'eId': eid, 'text': text, 'amendment': None}
        self.children.append(child)
        return child

    def extend(self, text: str) -> None:
        """Append text to the current child (e.g. list items of a paragraph)."""
        if not text:
            return
        if not self.children:
            self.add(text)
        else:
            current = self.children[-1]
            current['text'] = f"{current['text']} {text}".strip()

    def _unique(self, eid: str) -> str:
        base, n = eid, 2
        while eid in self._used:
            eid = f'{base}_{n}'
            n += 1
        self._used.add(eid)
        return eid


class BodyBuilder:
    """
    Builds ``chapters``, ``articles`` and ``structure`` in document order.

    Open a division with ``division()`` when its heading appears; it stays
    open until a division of the same or a higher level starts. Articles
    added with ``article()`` belong to the innermost open division.
    """

    def __init__(self) -> None:
        self.chapters: list[dict[str, Any]] = []
        self.articles: list[dict[str, Any]] = []
        self.structure: list[dict[str, Any]] = []
        self._stack: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
        self._used: set[str] = set()
        self._counts: dict[str, int] = {}

    @property
    def current_division(self) -> Optional[dict[str, Any]]:
        return self._stack[-1][2] if self._stack else None

    def division(self, type_: str, num: Optional[str] = None,
                 heading: Optional[str] = None, token: Optional[str] = None) -> dict[str, Any]:
        """
        Open a division ('part', 'title', 'chapter', 'section', 'subsection').

        ``token`` overrides the number taken from ``num`` for the eId.
        """
        prefix, rank = DIVISION_TYPES.get(type_, GENERIC_DIVISION)
        while self._stack and self._stack[-1][0] >= rank:
            self._stack.pop()
        parent = self.current_division
        self._counts[prefix] = self._counts.get(prefix, 0) + 1
        eid = self._unique(f'{prefix}_{token or eid_token(num) or self._counts[prefix]}')

        chapter = {'eId': eid, 'type': type_, 'num': num, 'heading': heading,
                   'parent': parent['eId'] if parent else None}
        node = {'eId': eid, 'type': type_, 'num': num, 'children': []}
        container = self._stack[-1][1]['children'] if self._stack else self.structure
        container.append(node)
        self.chapters.append(chapter)
        self._stack.append((rank, node, chapter))
        return chapter

    def close_divisions(self) -> None:
        """Close all open divisions (e.g. before final provisions outside any division)."""
        self._stack.clear()

    def article(self, num: Optional[str], heading: Optional[str],
                children: list[dict[str, Any]], token: Optional[str] = None) -> dict[str, Any]:
        """Add an article to the innermost open division."""
        self._counts['art'] = self._counts.get('art', 0) + 1
        eid = self._unique(f"art_{token or eid_token(num) or self._counts['art']}")
        parent = self.current_division
        article = {'eId': eid, 'num': num, 'heading': heading, 'children': children,
                   'parent': parent['eId'] if parent else None}
        container = self._stack[-1][1]['children'] if self._stack else self.structure
        container.append({'eId': eid, 'type': 'article'})
        self.articles.append(article)
        return article

    def _unique(self, eid: str) -> str:
        base, n = eid, 2
        while eid in self._used:
            eid = f'{base}_{n}'
            n += 1
        self._used.add(eid)
        return eid
