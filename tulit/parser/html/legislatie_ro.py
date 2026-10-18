"""
Parser for the pages of Romanian acts on the Portal Legislativ (legislatie.just.ro).

The portal shows each form of an act (as published, republished or
consolidated) as HTML whose spans carry classes naming their role, each
structural unit with a number (``_TTL``), a heading (``_DEN``) and a body
(``_BDY``):

- ``S_DEN`` and ``S_HDR`` give the title (preface), ``S_EMT`` and ``S_PUB``
  the issuer and the publication in Monitorul Oficial (the recitals'
  introduction); the paragraphs before the first division or article give
  the considerations and the enacting formula ('Parlamentul României adoptă
  prezenta lege.');
- ``S_CRT`` (Cartea), ``S_PRT`` (Partea), ``S_TTL`` (Titlul), ``S_CAP``
  (Capitolul) and ``S_SEC`` (Secțiunea) become divisions nested as on the
  page, with '§1.' paragraphs of a section as subsections;
- ``S_ART`` becomes an article, its heading the ``S_ART_DEN`` or the
  marginal title printed as its first paragraph; ``S_ALN`` paragraphs '(1)'
  become par_N, with letters (``S_LIT``), points (``S_PCT``) and dashes
  (``S_LIN``) folded in; the points of an amending article ('1. Articolul 1
  va avea următorul cuprins:') carry a structured amendment, with the text
  they introduce as its quoted text;
- the signatures (``S_SMN``) and the record of the adoption become the
  conclusions, ``S_ANX`` the annexes.

The database's editorial notes are left out: the notes (``S_NTA``) and the
records of each change ('(la 21-07-2020, Articolul 11 ... a fost modificat
de ...)'); the provisions they describe are in the text, as amended.
"""
import re
from typing import Any, Optional

from lxml import etree, html

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder
from tulit.parser.xml.legislatie_ro import (_CLOSING, _FORMULA, _LETTER, _PARAGRAPH, _POINT, _amended_act,
                                            _unbalanced, amendment_action)

# A record of a change the database adds after the provision: '(la 02-06-2012, Titlul legii a fost modificat de ...)'
_CHANGE = re.compile(r'^\(la \d{2}-\d{2}-\d{4},')
# A footnote of the database's editor, under a rule: '**) Dispoziţiile de punere în aplicare ... sunt cuprinse în ...'
_FOOTNOTE = re.compile(r'^\*+\)')
_SEPARATOR = re.compile(r'^[-_*.─—=]{3,}$')
_SUBSECTION = re.compile(r'^(?P<num>§\s*\d+(?:\^\d+)?\.?)\s*(?P<heading>.*)$')
_ARTICLE_NUMBER = re.compile(r'(\d+(?:\^\d+)?|[IVXLC]+(?:\^\d+)?|UNIC)\s*$', re.IGNORECASE)
_DIVISION_NUMBER = re.compile(r'^\S+\s+(?:a\s+)?(?P<num>[^\s-]+)')
DIVISIONS = {'cartea': 'part', 'partea': 'part', 'titlul': 'title', 'capitolul': 'chapter', 'secțiunea': 'section',
             'secţiunea': 'section', 'sectiunea': 'section', 'subsecțiunea': 'subsection',
             'subsecţiunea': 'subsection', 'subsectiunea': 'subsection'}
DIVISION_CLASSES = {'S_CRT': 'part', 'S_PRT': 'part', 'S_TTL': 'title', 'S_CAP': 'chapter', 'S_SEC': 'section',
                    'S_SBS': 'subsection', 'S_SSC': 'subsection'}
# Classes of units inside an article, and of what the text leaves out
UNITS = ('S_ALN', 'S_LIT', 'S_PCT', 'S_LIN', 'S_ART')
SKIP = ('S_NTA', 'TAG_COLLAPSED')
BLOCKS = {'S_PAR', 'S_ALN', 'S_ALN_TTL', 'S_ALN_BDY', 'S_LIT', 'S_LIT_TTL', 'S_LIT_BDY', 'S_PCT', 'S_PCT_TTL',
          'S_PCT_BDY', 'S_LIN', 'S_LIN_TTL', 'S_LIN_BDY', 'S_ART', 'S_ART_TTL', 'S_ART_DEN', 'S_ART_BDY', 'S_PRE',
          'S_SMN_PAR', 'S_EMT_TTL', 'S_EMT_BDY', 'S_PUB_TTL', 'S_PUB_BDY'}
BLOCK_TAGS = {'br', 'p', 'div', 'tr', 'td', 'th', 'li', 'table'}
QUOTES = ('"', '„', '«')


def _class(element: Any) -> str:
    return (element.get('class') or '') if isinstance(element.tag, str) else ''


def _is_change(element: Any) -> bool:
    """Whether an element is the database's record of a change, or a footnote of its editor."""
    text = (element.text or '').strip()
    return _class(element) == 'S_PAR' and bool(_CHANGE.match(text) or _FOOTNOTE.match(text))


def clean(text: str) -> str:
    """Without the asterisks of the database's notes: 'LEGE nr. 31 (**republicată**)*)' -> '... (republicată)'."""
    text = re.sub(r'\(\*+([^()*]+?)\*+\)', r'(\1)', text)
    out = ''
    for piece in re.split(r'(\*+\))', text):
        if piece.startswith('*'):
            # A note's marker, unless its parenthesis closes one the text opened: '(actualizată ...*)'
            piece = ')' if out.count('(') > out.count(')') else ''
        out += piece
    return ' '.join(out.replace('*', ' ').split())


def text_of(element: Any) -> str:
    """The text of an element without the database's notes, with blocks set apart by a space."""
    parts: list[str] = []

    def walk(node: Any) -> None:
        if node.text:
            parts.append(node.text)
        for child in node:
            if isinstance(child.tag, str):
                name = _class(child)
                if not (name in SKIP or name.endswith('_SHORT') or _is_change(child)):
                    block = name in BLOCKS or child.tag in BLOCK_TAGS
                    parts.append(' ' if block else '')
                    walk(child)
                    parts.append(' ' if block else '')
            if child.tail:
                parts.append(child.tail)

    walk(element)
    text = ' '.join(''.join(parts).split())
    return re.sub(r' (?=[,;:.)](?:\s|$))', '', text)


def _heading_like(text: str) -> bool:
    """Whether a paragraph reads as the title printed above a provision ('Statul român')."""
    return (0 < len(text) < 200 and text[:1].isupper() and not re.search(r'[.;:,!?"”]$', text)
            and not text.startswith(('§', 'Abrogat')) and not _CLOSING.match(text) and not _SEPARATOR.match(text))


def _content(element: Any) -> list[Any]:
    """The child elements of a body that hold text of the act (not notes or controls)."""
    return [child for child in element if isinstance(child.tag, str) and _class(child) not in SKIP
            and not _is_change(child) and (text_of(child) or _class(child) in UNITS)]


def _part(element: Any, suffix: str) -> Optional[Any]:
    """The number (_TTL), heading (_DEN) or body (_BDY) of a unit."""
    return element.find(f"span[@class='{_class(element)}{suffix}']")


class _Body(BodyBuilder):
    def close(self, rank: float) -> None:
        """Close the divisions of a rank or deeper (when the page closes them)."""
        while self._stack and self._stack[-1][0] >= rank:
            self._stack.pop()


class LegislatieHtmlParser(Parser):
    """Parses a page of a Romanian act from the Portal Legislativ into legalJSON."""

    def parse(self, file: str, **options) -> 'LegislatieHtmlParser':
        try:
            document = html.parse(file, parser=html.HTMLParser(encoding='utf-8')).getroot()
        except (OSError, etree.XMLSyntaxError, etree.ParserError) as e:
            raise FileLoadError(f"Cannot read Portal Legislativ page {file}: {e}") from e
        if document is None:
            raise FileLoadError(f"{file} is empty")
        content = document.xpath("//div[@id='div_Formaconsolidata']") or \
            document.xpath("//div[contains(concat(' ', @class, ' '), ' content_forma_act ')][.//span[@class='S_DEN']]")
        if not content:
            title = document.xpath("//span[@class='S_DEN']")
            if not title:
                raise FileLoadError(f"{file} holds no act text")
            content = [title[0].getparent()]
        self.body = _Body()
        self._title: list[str] = []
        self._intro: list[str] = []
        self._front: list[str] = []
        self._closing: list[str] = []
        self._signature: list[str] = []
        self._started = False
        self._published = False
        self._last: Optional[ChildrenBuilder] = None
        self._read(content[0], 0)
        self._finish()
        if not self.preface:
            raise FileLoadError(f"{file} holds no act text")
        return self

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    # The page, element by element

    def _read(self, container: Any, depth: int) -> None:
        for element in container:
            if not isinstance(element.tag, str):
                continue
            name = _class(element)
            if name in SKIP or name.endswith('_SHORT') or _is_change(element):
                continue
            if name == 'S_DEN':
                self._title.append(text_of(element))
            elif name == 'S_HDR':
                self._title.append(text_of(element))
            elif name in ('S_EMT', 'S_PUB'):
                self._intro.append(text_of(element))
                self._published = True
            elif name == 'S_ART':
                self._article(element)
            elif name == 'S_ANX':
                self._annex(element)
            elif name == 'S_SMN':
                self._signature.extend(text_of(line) for line in element if text_of(line))
            elif name in DIVISION_CLASSES and _part(element, '_BDY') is not None:
                self._division(element, depth)
            elif _part(element, '_BDY') is not None and \
                    _part(element, '_BDY').xpath(".//span[@class='S_ART'][not(ancestor::span[@class='S_NTA'])]"):
                # A lettered paragraph of a section heading articles ('A. Directoratul')
                self._division(element, depth, 'subsection')
            elif name == 'S_PAR' and self._subsection(element, depth):
                continue
            else:
                text = text_of(element)
                if text and not _SEPARATOR.match(text):
                    self._paragraph(text)

    def _paragraph(self, text: str) -> None:
        """A paragraph outside the articles: title, considerations, formula, or closing words."""
        if self._closing or (self._started and _CLOSING.match(text)):
            self._closing.append(text)
        elif not self._started:
            if self._published:
                self._front.append(text)
            else:
                # Older pages print the rest of the title as a paragraph
                self._title.append(text)
        elif self._last is not None:
            # Text between articles that heads nothing stays with the article above
            self._last.add(text)
        else:
            self._front.append(text)

    def _subsection(self, element: Any, depth: int) -> bool:
        """'§1. Dispoziţii generale' in a section: a subsection, closed by the next one."""
        if depth == 0:
            return False
        match = _SUBSECTION.match(text_of(element))
        if not match:
            return False
        self._started = True
        number = match.group('num').replace(' ', '')
        self.body.division('subsection', number, heading=match.group('heading') or None,
                           token=re.sub(r'\D+', '', number.replace('^', '-')) or None, rank=depth)
        return True

    def _division(self, element: Any, depth: int, kind: Optional[str] = None) -> None:
        self._started = True
        number = text_of(_part(element, '_TTL')) if _part(element, '_TTL') is not None else ''
        heading = clean(text_of(_part(element, '_DEN'))) if _part(element, '_DEN') is not None else ''
        body = _part(element, '_BDY')
        heading = heading or ' '.join((body.text or '').split())
        content = _content(body)
        if not heading and len(content) > 1 and _class(content[0]) == 'S_PAR' \
                and _heading_like(text_of(content[0])) and not _SUBSECTION.match(text_of(content[0])):
            # A heading changed by an amendment is printed as the first paragraph
            heading = text_of(content[0])
            content[0].set('class', 'S_HEADING')
            content[0].text, content[0][:] = '', []
        word = number.split(' ', 1)[0].lower()
        kind = DIVISIONS.get(word, kind or DIVISION_CLASSES.get(_class(element), 'subsection'))
        match = _DIVISION_NUMBER.match(number)
        token = match.group('num').replace('^', '-') if match else None
        self.body.division(kind, number or None, heading=heading or None, token=token, rank=depth)
        self._read(body, depth + 1)
        self.body.close(depth)

    def _article(self, element: Any) -> None:
        self._started = True
        number = text_of(_part(element, '_TTL')) if _part(element, '_TTL') is not None else ''
        heading = clean(text_of(_part(element, '_DEN'))) if _part(element, '_DEN') is not None else ''
        body = _part(element, '_BDY')
        content = _content(body) if body is not None else []
        if not heading and len(content) > 1 and _class(content[0]) == 'S_PAR' and _heading_like(text_of(content[0])):
            heading = text_of(content.pop(0))
        children = ChildrenBuilder()
        self._act: Optional[str] = None
        self._quoting = self._open_quote = False
        for unit in content:
            if self._closing:
                self._closing.append(text_of(unit))
                continue
            self._unit(unit, children)
        match = _ARTICLE_NUMBER.search(number)
        token = match.group(1).replace('^', '-') if match else None
        if token and token.upper() == 'UNIC':
            token = '1'
        self.body.article(number or None, heading or None, children.children, token=token)
        self._last = children

    def _unit(self, unit: Any, children: ChildrenBuilder) -> None:
        """A paragraph, letter, point or dash of an article."""
        name = _class(unit)
        text = text_of(unit)
        if not text or _SEPARATOR.match(text):
            return
        if _CLOSING.match(text) and name == 'S_PAR':
            self._closing.append(text)
            return
        if self._quoting and (text.startswith(QUOTES) or self._open_quote):
            # Text an amendment introduces
            child = children.children[-1]
            child['text'] = f"{child['text']} {text}"
            if child.get('amendment') is not None:
                child['amendment']['quoted'].append({'kind': 'text', 'text': text.strip('"„”«»')})
            if _unbalanced(text):
                self._open_quote = not self._open_quote
            return
        self._quoting = self._open_quote = False
        # Pages mark paragraphs '(1)' as S_ALN, or as S_PAR or S_LIT holding the number in their text
        label = unit.find("span[@class='S_ALN_TTL']") if name == 'S_ALN' else None
        paragraph = _PARAGRAPH.match(text)
        number = text_of(label).strip('()') if label is not None and text_of(label) else \
            (paragraph.group('num') if paragraph else None)
        found = _amended_act(text)
        action = amendment_action(text)
        point = bool(_POINT.match(text)) and bool(action) and not text.startswith(QUOTES)
        if number:
            child = children.add(text, number=number, token=number.replace('^', '-'))
        elif point:
            child = children.add(text)
        elif children.children and (name in ('S_LIT', 'S_PCT', 'S_LIN') or _LETTER.match(text)
                                    or _POINT.match(text) or text[:1].islower() or text.startswith(('–', '-'))):
            children.extend(text)
            return
        else:
            child = children.add(text)
        if found and action:
            self._act = found
        if action and not text.startswith(QUOTES) and (_POINT.match(text) or text.endswith(':')):
            child['amendment'] = {'action': action, 'instruction': text, 'amended_act': found or self._act,
                                  'quoted': []}
            self._quoting = text.endswith(':')

    def _annex(self, element: Any) -> None:
        number = text_of(_part(element, '_TTL')) if _part(element, '_TTL') is not None else ''
        heading = text_of(_part(element, '_DEN')) if _part(element, '_DEN') is not None else ''
        body = _part(element, '_BDY')
        annex = ChildrenBuilder()
        blocks = _content(body) if body is not None else []
        for block in blocks:
            text = text_of(block)
            if text and not _SEPARATOR.match(text):
                annex.add(text)
        if not blocks and body is not None and text_of(body):
            annex.add(text_of(body))
        self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': number or None,
                             'heading': heading or None, 'children': annex.children})

    def _finish(self) -> None:
        self.preface = clean(' '.join(self._title)) or None
        self.recitals_init = ' '.join(self._intro) or None
        formula = next((i for i in range(len(self._front) - 1, -1, -1) if _FORMULA.search(self._front[i])), None)
        considerations = self._front
        if formula is not None:
            self.formula = self._front[formula]
            considerations = self._front[:formula] + self._front[formula + 1:]
        self.recitals = [{'eId': f'rct_{n}', 'text': text} for n, text in enumerate(considerations, start=1)]
        self.chapters, self.articles, self.structure = self.body.chapters, self.body.articles, self.body.structure
        if self._closing or self._signature:
            adopted = [t for t in self._closing
                       if t.startswith(('Această lege', 'Aceasta lege', 'Constituția', 'Constituţia'))]
            signature = [t for t in self._closing + self._signature if t not in adopted and not _SEPARATOR.match(t)]
            self.conclusions = {'conclusion_text': ' '.join(adopted) or None, 'signature': ' '.join(signature) or None}
