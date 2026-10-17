"""
Parser for consolidated Swedish statutes (SFS) in the HTML of the Riksdag open data.

The Riksdag republishes the Government Offices' consolidated text of each
statute (SFST) as flat HTML with anchors:

- ``h2`` gives the title (preface) and the divisions (avdelningar), ``h3``
  the chapters (kapitel), ``h4`` the headings above sections;
- each section (``a.paragraf``, '3 §') becomes an article; section numbers
  restart in every chapter, so the eId holds both ('1 kap. 3 §' -> art_1-3);
- each paragraph (stycke) becomes a child unp_N, list items included;
- where an amendment is pending, a section appears twice, marked
  '/Upphör att gälla U:2027-01-01/' and '/Träder i kraft I:2027-01-01/'; the
  version in force on the requested date (default today) is kept, and
  sections entering into force on a date the government has yet to decide
  are left out;
- the transitional provisions (övergångsbestämmelser) become an annex, one
  child per amending act.
"""
import datetime
import re
from typing import Any, Optional

from lxml import etree, html

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder

_SECTION_NAME = re.compile(r'^(?:K(?P<chapter>\d+[a-z]?))?P(?P<section>\d+\s?[a-z]?)$')
_STYCKE_NAME = re.compile(r'^(?:K\d+[a-z]?)?P\d+[a-z]?S\d+$')
_CHAPTER = re.compile(r'^(?P<num>(?P<token>\d+\s?[a-z]?)\s*kap\.)\s*(?P<heading>.*)$')
_MARKER = re.compile(r'^/(?P<kind>Upphör att gälla U|Träder i kraft I):(?P<when>.*?)/?$', re.DOTALL)
_DATE = re.compile(r'\d{4}-\d{2}-\d{2}')
_AMENDING_ACT = re.compile(r'^\d{4}:\d+(\s|$)')
ORDINALS = {
    'första': '1', 'andra': '2', 'tredje': '3', 'fjärde': '4', 'femte': '5', 'sjätte': '6',
    'sjunde': '7', 'åttonde': '8', 'nionde': '9', 'tionde': '10',
}


def _clean(text: str) -> str:
    return ' '.join(text.split())


class RiksdagenSFSParser(Parser):
    """Parses a consolidated Swedish statute (Riksdag open data HTML) into legalJSON."""

    def __init__(self, date: Optional[str] = None) -> None:
        """``date``: keep the versions of sections in force on this ISO date (default today)."""
        super().__init__()
        self.date = date

    def parse(self, file: str, **options) -> 'RiksdagenSFSParser':
        try:
            with open(file, 'rb') as f:
                markup = f.read().decode('utf-8')
        except (OSError, UnicodeDecodeError) as e:
            raise FileLoadError(f"Cannot read SFS document {file}: {e}") from e
        root = html.fragment_fromstring(markup, create_parent='div')
        title = root.find('h2')
        if title is None:
            raise FileLoadError(f"{file} is not the text of a Swedish statute")
        self.preface = _clean(title.text_content()) or None
        self.date = self.date or datetime.date.today().isoformat()
        self.annexes = []

        events = list(self._events(root, started=False))
        self._build(events)
        return self

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    # Document order as a stream of events
    def _events(self, element: etree._Element, started: bool):
        state = {'started': started}

        def walk(node: etree._Element):
            if node.text and state['started']:
                yield ('text', node.text)
            for child in node:
                if not isinstance(child.tag, str):
                    if child.tail and state['started']:
                        yield ('text', child.tail)
                    continue
                if child.tag == 'hr':
                    state['started'] = True
                elif not state['started'] or child.tag == 'style' or 'sfstoc' in (child.get('class') or ''):
                    pass
                elif child.tag == 'h2':
                    yield ('part', _clean(child.text_content()))
                elif child.tag == 'h3':
                    name = child.get('name') or ''
                    yield ('transitional' if name == 'overgang' else 'chapter', _clean(child.text_content()))
                elif child.tag == 'h4':
                    yield ('heading', _clean(child.text_content()))
                elif child.tag == 'a' and 'paragraf' in (child.get('class') or ''):
                    yield ('section', _clean(child.text_content()), child.get('name') or '')
                elif child.tag == 'a' and _STYCKE_NAME.match(child.get('name') or ''):
                    yield ('stycke',)
                elif child.tag == 'br':
                    yield ('text', '\n')
                elif child.tag == 'i' and _MARKER.match(_clean(child.text_content())):
                    marker = _MARKER.match(_clean(child.text_content()))
                    yield ('marker', marker.group('kind')[-1], marker.group('when'))
                else:
                    yield from walk(child)
                if child.tail and state['started']:
                    yield ('text', child.tail)

        yield from walk(element)

    def _build(self, events: list[tuple]) -> None:
        body = BodyBuilder()
        heading: Optional[str] = None
        chapter_token: Optional[str] = None
        part: Optional[dict[str, Any]] = None
        article: Optional[dict[str, Any]] = None
        transitional: Optional[ChildrenBuilder] = None
        buffer: list[str] = []

        def flush_stycke() -> None:
            text = _clean(''.join(buffer))
            buffer.clear()
            if not text:
                return
            if transitional is not None:
                if _AMENDING_ACT.match(text) or not transitional.children:
                    transitional.add(text)
                else:
                    transitional.extend(text)
            elif article is not None:
                article['children'].add(text)

        def flush_article() -> None:
            nonlocal article, heading
            flush_stycke()
            if article is None:
                return
            if self._in_force(article):
                body.article(article['num'], article['heading'], article['children'].children,
                             token=article['token'])
            elif article['heading'] and heading is None:
                # The heading also belongs to the other version of the section
                heading = article['heading']
            article = None

        for event in events:
            kind = event[0]
            if kind == 'text':
                buffer.append(event[1])
            elif kind == 'stycke':
                flush_stycke()
            elif kind == 'marker' and article is not None:
                article['marker'] = (event[1], event[2])
            elif kind == 'section':
                flush_article()
                match = _SECTION_NAME.match(event[2].replace(' ', ''))
                section = match.group('section') if match else None
                chapter = match.group('chapter') if match and match.group('chapter') else chapter_token
                token = '-'.join(t for t in (chapter, section) if t) or None
                article = {'num': event[1], 'heading': heading, 'token': token,
                           'children': ChildrenBuilder(), 'marker': None}
                heading = None
            elif kind == 'heading':
                flush_article()
                if part is not None and not body.articles and part.get('heading') is None or \
                        part is not None and part.get('_open'):
                    part['heading'] = event[1]
                    part.pop('_open', None)
                else:
                    heading = f'{heading} {event[1]}' if heading else event[1]
            elif kind == 'part':
                flush_article()
                if event[1] == self.preface and not body.chapters and not body.articles:
                    continue
                words = event[1].split()
                token = ORDINALS.get(words[0].lower()) if words else None
                part = body.division('part', event[1], token=token)
                part['_open'] = True
                heading = None
            elif kind == 'chapter':
                flush_article()
                if part is not None:
                    part.pop('_open', None)
                match = _CHAPTER.match(event[1])
                chapter_token = match.group('token').replace(' ', '') if match else None
                body.division('chapter', match.group('num') if match else event[1],
                              heading=(match.group('heading') or None) if match else None, token=chapter_token)
                heading = None
            elif kind == 'transitional':
                flush_article()
                transitional = ChildrenBuilder()
                self.annexes.append({'eId': 'anx_transitional', 'num': None, 'heading': event[1],
                                     'children': transitional.children})
        flush_article()
        flush_stycke()
        for chapter in body.chapters:
            chapter.pop('_open', None)
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure

    def _in_force(self, article: dict[str, Any]) -> bool:
        """Whether a section is in force on the parser's date, from its validity marker."""
        if article['marker'] is None:
            return True
        kind, when = article['marker']
        found = _DATE.search(when)
        if kind == 'I':
            # Enters into force on a date, or on a day the government is yet to decide
            return bool(found) and found.group(0) <= self.date
        return not found or self.date < found.group(0)
