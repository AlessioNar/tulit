"""
Parser for Swedish acts as adopted, in the PDF of Svensk författningssamling (SFS).

Since 1 April 2018 the Government Offices publish each act of the Swedish
Code of Statutes as a PDF on svenskforfattningssamling.se, set in one column
with a margin on the right:

- the margin (the SFS number, 'Publicerad den 24 april 2018'), the page
  numbers, the barcode and the footnotes (the preparatory works, 'Senaste
  lydelse ...') are left out of the text, and so are the footnote marks;
- the kind and title ('Lag' / 'med kompletterande bestämmelser till EU:s
  dataskyddsförordning') give the preface, cited as the SFS does: 'Lag
  (2018:218) med kompletterande ...'; 'Utfärdad den ...' and 'Publicerad
  den ...' the dates of the act;
- the enacting words ('Enligt riksdagens beslut föreskrivs följande.',
  'Regeringen föreskriver följande.') become the formula;
- 'AVDELNING I.' headings become parts, 'N kap.' headings chapters, and the
  bold and italic lines above a section its heading;
- each section ('3 §', '3 a §') becomes an article; section numbers restart
  in every chapter, so the eId holds both ('1 kap. 3 §' -> art_1-3); each
  paragraph (stycke), with its list items, becomes a child unp_N;
- the entry into force and transitional provisions, set after a short rule,
  become the annex anx_transitional, one child per numbered point;
- 'På regeringens vägnar' and the signatures become the conclusions, the
  appendices ('Bilaga 1') annexes.

In an act amending another ('Lag om ändring i lagen (2018:218) ...') each
section is the new wording of a section of the amended act: its first child
carries a structured ``amendment`` whose instruction is the clause of the
enacting words naming that section ('dels att 1 kap. 4 § ska ha följande
lydelse'), with the action it states (replace, insert, renumber) and the
wording as quoted structure.

Needs the ``pdf`` extra.
"""
import datetime
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Optional

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.pdf.layout import _pdfplumber
from tulit.parser.structure import BodyBuilder, ChildrenBuilder

MONTHS = ('januari', 'februari', 'mars', 'april', 'maj', 'juni', 'juli', 'augusti', 'september', 'oktober',
          'november', 'december')
_DATE = r'(\d{1,2})\s+(' + '|'.join(MONTHS) + r')\s+(\d{4})'
# 'Utfärdad den' (issued), 'Beslutat den' for a notice (tillkännagivande)
_ISSUED = re.compile(r'^(?:Utfärdad|Beslutad|Beslutat)\s+den\s+' + _DATE)
_PUBLISHED = re.compile(r'Publicera[dt]\s+den\s+' + _DATE)
_NUMBER = re.compile(r'SFS\s+(\d{4}:\d+)')
# Words that open a title and are followed by the SFS number when the act is cited
_KINDS = ('Lag', 'Förordning', 'Kungörelse', 'Tillkännagivande', 'Föreskrifter', 'Beslut', 'Instruktion',
          'Riksdagens beslut', 'Riksdagsstyrelsens föreskrifter')
_SECTION = re.compile(r'^(?P<num>\d+(?: ?[a-z])?) §(?:\s+|$)')
_CHAPTER = re.compile(r'^(?P<num>(?P<token>\d+(?: ?[a-z])?) kap\.)\s*(?P<heading>.*)$')
_PART = re.compile(r'^(?P<num>AVDELNING\s+(?P<token>[IVXLC]+)\.?)\s*(?P<heading>.*)$')
_ANNEX = re.compile(r'^Bilaga(?:\s+(?P<token>\d+[a-z]?))?$')
_SIGNING = re.compile(r'^På (regeringens|Riksdagens|riksdagens|Riksdagsstyrelsens) vägnar')
_IN_FORCE = re.compile(r'^(?:1\.\s+)?(?:(?:Denna|Dessa)\s+\S+|Lagen|Förordningen|Föreskrifterna)\s+'
                       r'(?:träder|ska träda)\s+i\s+kraft')
_LIST_ITEM = re.compile(r'^(?:\d+[a-z]?\.|[a-zåäö]\)|–|-|•)\s')
_POINT = re.compile(r'^\d+[a-z]?\.\s')
# Enacting words that end where the text begins ('Regeringen tillkännager följande.')
_ENACTED = ('följande.', 'följande:')
# A word broken at the line end ('data-' + 'skyddsförordning'), not a shared ending ('hälso- och')
_BROKEN = re.compile(r'[^\W\d_]-$')
_KEEP_HYPHEN = ('och ', 'eller ', 'samt ', 'respektive ', 'resp. ', 'till ', 'som ')

# Amending acts
_AMENDING = re.compile(r'\bom ändring i\b', re.IGNORECASE)
_NUMBER_TOKEN = r'\d+(?: ?[a-z]\b)?'
_LIST = rf'{_NUMBER_TOKEN}(?:\s*(?:,|och|–|-)\s*{_NUMBER_TOKEN})*'
_REFERENCES = re.compile(rf'(?:(?P<chapter>{_NUMBER_TOKEN})\s*kap\.\s*)?(?P<sections>{_LIST})\s*§')
_CHAPTER_REFERENCE = re.compile(rf'(?P<chapters>{_LIST})\s*kap\.(?!\s*\d)')
# Headings named by their place ('närmast före 6 kap. 8 § och 7 kap. 6 §'): not the sections themselves
_REFERENCE = rf'(?:{_NUMBER_TOKEN}\s*kap\.\s*)?{_LIST}\s*(?:§§?|kap\.)'
_HEADING_PLACE = re.compile(rf'närmast (?:före|efter)\s+{_REFERENCE}(?:\s*(?:,\s*och|,|och)\s*{_REFERENCE})*')
# Clause wording -> action, by priority when a section is named by several clauses
ACTIONS = (
    (re.compile(r'ska införas|nya? (?:paragraf|paragrafer|kapitel|bilaga)'), 'insert'),
    (re.compile(r'följande lydelse|ska lyda'), 'replace'),
    (re.compile(r'ska betecknas'), 'renumber'),
    (re.compile(r'upphöra att gälla|ska upphävas'), 'repeal'),
)


@dataclass
class _Line:
    page: int
    text: str
    x0: float
    x1: float
    top: float
    size: float
    bold: bool
    italic: bool


def _iso(match: Optional[re.Match]) -> Optional[str]:
    if not match:
        return None
    day, month, year = match.groups()[-3:]
    return datetime.date(int(year), MONTHS.index(month) + 1, int(day)).isoformat()


def _join(texts: list[str]) -> str:
    """Join wrapped lines, mending words broken at the line end."""
    joined = ''
    for text in texts:
        text = text.strip()
        if not text:
            continue
        if joined and _BROKEN.search(joined) and text[:1].islower() and not text.startswith(_KEEP_HYPHEN):
            joined = joined[:-1] + text
        else:
            joined = f'{joined} {text}' if joined else text
    return joined


def _key(token: Optional[str]) -> Optional[str]:
    return token.replace(' ', '') if token else None


def _numbers(listed: str) -> list[str]:
    """'1, 2 a och 4–6' -> ['1', '2a', '4', '5', '6']; '4 a–4 d' -> ['4a', '4b', '4c', '4d']."""
    tokens = re.split(r'\s*(,|och|–|-)\s*', listed)
    numbers = [_key(t) for t in tokens[::2]]
    for position, separator in enumerate(tokens[1::2]):
        if separator not in '–-':
            continue
        start = re.match(r'(\d+)([a-z]?)$', numbers[position])
        end = re.match(r'(\d+)([a-z]?)$', numbers[position + 1])
        if not start or not end:
            continue
        if start.group(1) == end.group(1) and start.group(2) and end.group(2):
            numbers.extend(start.group(1) + chr(c) for c in range(ord(start.group(2)) + 1, ord(end.group(2))))
        else:
            numbers.extend(str(n) for n in range(int(start.group(1)) + 1, int(end.group(1))))
            if end.group(2):
                numbers.append(end.group(1))
    return numbers


def _section_references(clause: str) -> set[tuple[Optional[str], Optional[str]]]:
    """'6 kap. 8 § och 7 kap. 3 a och 6 §§' -> {('6', '8'), ('7', '3a'), ('7', '6')}; chapters alone with None."""
    clause = _HEADING_PLACE.sub(' ', clause)
    found: set[tuple[Optional[str], Optional[str]]] = set()
    for match in _REFERENCES.finditer(clause):
        chapter = _key(match.group('chapter'))
        found.update((chapter, number) for number in _numbers(match.group('sections')))
    for match in _CHAPTER_REFERENCE.finditer(clause):
        found.update((chapter, None) for chapter in _numbers(match.group('chapters')))
    return found


def _margin_text(page) -> str:
    """Text in the right margin of the first page: the SFS number and 'Publicerad den ...'."""
    right = 422 * float(page.width) / 595.3
    margin = page.within_bbox((right, 0, float(page.width), float(page.height) * 0.4))
    return ' '.join((margin.extract_text() or '').split())


def masthead(path: str) -> dict[str, Optional[str]]:
    """The SFS number and the dates on the first page of an act: {'number', 'issued', 'published'}."""
    pdfplumber = _pdfplumber()
    try:
        pdf = pdfplumber.open(path)
    except Exception as e:  # pdfplumber raises several unrelated types for unreadable files
        raise FileLoadError(f"Cannot read PDF {path}: {e}") from e
    with pdf:
        if not pdf.pages:
            raise FileLoadError(f"{path} has no pages")
        margin = _margin_text(pdf.pages[0])
        text = ' '.join((pdf.pages[0].extract_text() or '').split())
    number = _NUMBER.search(margin)
    return {'number': number.group(1) if number else None,
            'issued': _iso(re.search(r'(?:Utfärdad|Beslutad|Beslutat)\s+den\s+' + _DATE, text)),
            'published': _iso(_PUBLISHED.search(margin))}


class SFSPDFParser(Parser):
    """Parses an act as published in Svensk författningssamling (PDF) into legalJSON."""

    def __init__(self) -> None:
        super().__init__()
        self.number: Optional[str] = None
        self.issued: Optional[str] = None
        self.published: Optional[str] = None

    def parse(self, file: str, **options) -> 'SFSPDFParser':
        lines, rules, margin_text = self._read(file)
        if not lines:
            raise FileLoadError(f"{file} has no text: not an act of Svensk författningssamling")
        number = _NUMBER.search(margin_text)
        self.number = number.group(1) if number else None
        self.published = _iso(_PUBLISHED.search(margin_text))
        start = self._masthead(lines, file)
        self._build(lines[start:], rules)
        if _AMENDING.search(self.preface or ''):
            self._amendments()
        return self

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def get_formula(self) -> Optional[str]:
        return self.formula

    # Reading the PDF
    def _read(self, file: str) -> tuple[list[_Line], dict[int, list[float]], str]:
        """Body lines in reading order, short rules by page, and the text of the first page's margin."""
        pdfplumber = _pdfplumber()
        try:
            pdf = pdfplumber.open(file)
        except Exception as e:  # pdfplumber raises several unrelated types for unreadable files
            raise FileLoadError(f"Cannot read PDF {file}: {e}") from e
        lines: list[_Line] = []
        rules: dict[int, list[float]] = {}
        margin_text = ''
        with pdf:
            for number, page in enumerate(pdf.pages):
                scale = float(page.width) / 595.3
                body_right = 422 * scale
                if number == 0:
                    margin_text = _margin_text(page)
                # The body column, without the barcode on the left and the margin on the right;
                # footnote marks are set small (in the title, at 9 points)
                title_end = 200 * scale if number == 0 else 0

                def text_size(o, title_end=title_end):
                    if o.get('object_type') != 'char':
                        return True
                    return o.get('size', 0) >= (10 if o.get('top', 0) < title_end else 8.5)

                body = page.within_bbox((40 * scale, 0, body_right, float(page.height))).filter(text_size)
                found = self._lines(body, number)
                # Footnotes at the foot of the page, set smaller than the text
                while found and found[-1].size <= 9.5 and found[-1].top > float(page.height) * 0.55:
                    found.pop()
                lines.extend(found)
                for shape in list(page.rects) + list(page.lines):
                    width, height = shape['x1'] - shape['x0'], abs(shape['bottom'] - shape['top'])
                    if height <= 2.5 and 30 * scale <= width <= 120 * scale and shape['x0'] < 100 * scale:
                        rules.setdefault(number, []).append(float(shape['top']))
        return lines, rules, margin_text

    @staticmethod
    def _lines(page, number: int) -> list[_Line]:
        lines = []
        for found in page.extract_text_lines(return_chars=True, x_tolerance=1.5):
            text = ' '.join(found['text'].split())
            chars = [c for c in found.get('chars') or [] if c.get('text', '').strip()]
            if not text or not chars:
                continue
            fonts = Counter(c.get('fontname', '') for c in chars)
            font = fonts.most_common(1)[0][0]
            sizes = Counter(round(c.get('size', 0), 1) for c in chars)
            lines.append(_Line(page=number, text=text, x0=float(found['x0']), x1=float(found['x1']),
                               top=float(found['top']), size=sizes.most_common(1)[0][0],
                               bold='Bold' in font, italic='Italic' in font or 'Oblique' in font))
        return lines

    def _masthead(self, lines: list[_Line], file: str) -> int:
        """Read the title and the issue date; returns the index of the first line after them."""
        first_page = [line for line in lines if line.page == 0]
        issued_at = next((i for i, line in enumerate(first_page) if _ISSUED.match(line.text)), None)
        if issued_at is None:
            raise FileLoadError(f"{file} is not an act of Svensk författningssamling (no 'Utfärdad den')")
        self.issued = _iso(_ISSUED.match(first_page[issued_at].text))
        title = [line.text for line in first_page[:issued_at]
                 if line.text != 'Svensk författningssamling' and line.size >= 12]
        if title and title[0] in _KINDS and len(title) > 1:
            kind, rest = title[0], _join(title[1:])
            self.preface = f'{kind} ({self.number}) {rest}' if self.number else f'{kind} {rest}'
        else:
            text = _join(title)
            self.preface = f'{text} ({self.number})' if self.number and text else (text or None)
        return issued_at + 1

    # Building the document
    def _build(self, lines: list[_Line], rules: dict[int, list[float]]) -> None:
        # The left edge of the text on each page: the leftmost shared by several lines (list items are
        # set in, the tables of an appendix may start further left)
        edges = Counter(round(line.x0) for line in lines)
        default_margin = edges.most_common(1)[0][0] if edges else 0
        margins = {}
        for page in {line.page for line in lines}:
            on_page = Counter(round(line.x0) for line in lines if line.page == page)
            margins[page] = min((x for x, count in on_page.items() if count >= 2), default=default_margin)
        right = max((line.x1 for line in lines), default=0)
        body = BodyBuilder()
        formula: list[str] = []
        article: Optional[dict[str, Any]] = None
        children: Optional[ChildrenBuilder] = None
        heading: list[str] = []
        division: Optional[dict[str, Any]] = None  # a division whose heading continues on the next line
        paragraph: list[str] = []
        transitional: Optional[ChildrenBuilder] = None
        annex: Optional[dict[str, Any]] = None
        closing: list[str] = []
        mode = 'formula'  # formula, body, transitional, closing, annex
        chapter_token: Optional[str] = None
        unused_rules = {page: sorted(tops) for page, tops in rules.items()}

        def flush_paragraph() -> None:
            text = _join(paragraph)
            paragraph.clear()
            if not text:
                return
            if mode == 'formula':
                formula.append(text)
            elif mode == 'transitional':
                # Numbered points, and paragraphs, are children; their list items ('a) ...') are not
                if transitional.children and _LIST_ITEM.match(text) and not _POINT.match(text):
                    transitional.extend(text)
                else:
                    transitional.add(text)
            elif mode == 'annex':
                annex['_children'].add(text)
            elif children is not None:
                if children.children and _LIST_ITEM.match(text):
                    children.extend(text)
                else:
                    children.add(text)

        def flush_article() -> None:
            nonlocal article, children
            flush_paragraph()
            if article is not None:
                body.article(article['num'], article['heading'], children.children, token=article['token'])
            article, children = None, None

        def start_transitional() -> None:
            nonlocal mode, transitional
            flush_article()
            mode = 'transitional'
            transitional = ChildrenBuilder()
            self.annexes.append({'eId': 'anx_transitional', 'num': None, 'heading': None,
                                 'children': transitional.children})

        previous: Optional[_Line] = None
        for line in lines:
            text = line.text
            gap = line.top - previous.top if previous and previous.page == line.page else None
            # A new block: space above the line or, at the top of a page, the previous line ending
            # short of the right edge or a sentence
            if gap is None:
                spaced = previous is None or previous.x1 < right - 25 or previous.text.endswith(('.', ':'))
            else:
                spaced = gap > line.size * 1.45
            margin = margins[line.page]
            indented = line.x0 > margin + 6
            at_margin = abs(line.x0 - margin) <= 6
            emphasised = line.bold or line.italic

            # A short rule above the line opens the transitional provisions
            page_rules = unused_rules.get(line.page) or []
            if page_rules and page_rules[0] < line.top:
                page_rules.pop(0)
                if mode in ('body', 'formula') and (body.articles or article is not None or formula or paragraph):
                    start_transitional()

            # 'Bilaga 1', set in italic or bold, or to the right
            appendix = bool(_ANNEX.match(text)) and (emphasised or line.x0 > margin + 100)
            if mode != 'annex' and appendix:
                flush_article()
                if mode == 'closing':
                    self._close(closing)
                mode = 'annex'
                match = _ANNEX.match(text)
                annex = {'eId': f"anx_{match.group('token') or len(self.annexes) + 1}", 'num': text,
                         'heading': None, '_children': ChildrenBuilder()}
                self.annexes.append(annex)
            elif mode == 'annex':
                if appendix:
                    flush_paragraph()
                    match = _ANNEX.match(text)
                    annex = {'eId': f"anx_{match.group('token') or len(self.annexes) + 1}", 'num': text,
                             'heading': None, '_children': ChildrenBuilder()}
                    self.annexes.append(annex)
                elif line.bold and line.size >= 12 and not annex['_children'].children and \
                        (annex['heading'] is None or not paragraph):
                    annex['heading'] = f"{annex['heading']} {text}" if annex['heading'] else text
                elif previous is not None and previous.page == line.page and not spaced and not indented \
                        and previous.x1 >= right - 25 and paragraph:
                    paragraph.append(text)
                else:
                    flush_paragraph()
                    paragraph.append(text)
            elif _SIGNING.match(text) and at_margin:
                flush_article()
                mode = 'closing'
                closing.append(text)
            elif mode == 'closing':
                closing.append(text)
            elif mode == 'transitional':
                if spaced or indented:
                    flush_paragraph()
                paragraph.append(text)
            elif _PART.match(text) and not line.bold and line.size >= 12.5:
                flush_article()
                if mode == 'formula':
                    mode = 'body'
                match = _PART.match(text)
                division = body.division('part', match.group('num').rstrip('.'),
                                         heading=match.group('heading') or None, token=match.group('token'))
                heading = []
            elif division is not None and division['type'] == 'part' and not line.bold and line.size >= 12.5 \
                    and text.isupper():
                division['heading'] = f"{division['heading']} {text}" if division['heading'] else text
            elif line.bold and line.size >= 12 and _CHAPTER.match(text) and at_margin:
                flush_article()
                mode = 'body'
                match = _CHAPTER.match(text)
                chapter_token = _key(match.group('token'))
                division = body.division('chapter', match.group('num'), heading=match.group('heading') or None,
                                         token=chapter_token)
                heading = []
            elif division is not None and division['type'] == 'chapter' and line.bold and line.size >= 12 \
                    and not spaced and division['heading']:
                division['heading'] = f"{division['heading']} {text}"
            elif emphasised and at_margin and not _SECTION.match(text) and \
                    (spaced or (previous is not None and (previous.bold or previous.italic))):
                flush_article()
                if mode == 'formula':
                    mode = 'body'
                division = None
                heading.append(text)
            elif at_margin and _SECTION.match(text) and \
                    (spaced or (previous is not None and (previous.bold or previous.italic))):
                flush_article()
                mode = 'body'
                division = None
                match = _SECTION.match(text)
                section = _key(match.group('num'))
                article = {'num': f"{match.group('num')} §", 'heading': ' '.join(heading) or None,
                           'token': '-'.join(t for t in (chapter_token, section) if t)}
                children = ChildrenBuilder()
                heading = []
                paragraph.append(text[match.end():])
            elif indented and spaced and _IN_FORCE.match(text) and (body.articles or article is not None
                                                                    or formula or paragraph):
                start_transitional()
                paragraph.append(text)
            else:
                division = None
                if indented or (spaced and mode == 'formula'):
                    flush_paragraph()
                if mode == 'formula' and not paragraph and formula and formula[-1].endswith(_ENACTED):
                    # The enacting words are over: an act without sections (a notice) goes on with its text
                    mode = 'body'
                if mode == 'body' and article is None:
                    # Text outside any section: an unnumbered article, under the heading above it
                    article = {'num': None, 'heading': ' '.join(heading) or None, 'token': None}
                    children = ChildrenBuilder()
                    heading = []
                paragraph.append(text)
            previous = line

        flush_article()
        flush_paragraph()
        if mode == 'closing':
            self._close(closing)
        for item in self.annexes:
            builder = item.pop('_children', None)
            if builder is not None:
                item['children'] = builder.children
        self.formula = ' '.join(formula) or None
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure

    def _close(self, closing: list[str]) -> None:
        if closing:
            self.conclusions = {'conclusion_text': closing[0], 'signature': ' '.join(closing[1:]) or None}
            closing.clear()

    # Amending acts
    def _amendments(self) -> None:
        """Mark each section of an amending act as the new wording of a section of the amended act."""
        formula = self.formula or ''
        # The amended act, as the title names it: 'lagen (2018:218) med ...', 'brottsbalken'
        amended = _AMENDING.split(self.preface or '', maxsplit=1)[-1].strip() or None
        parts = re.split(r'\bdels\s+', formula)
        clauses = [f'dels {part.strip()}' for part in parts[1:]] if len(parts) > 1 else [formula]
        named: dict[tuple[Optional[str], Optional[str]], tuple[int, str, str]] = {}
        actions_found = set()
        for clause in clauses:
            for priority, (pattern, action) in enumerate(ACTIONS):
                if pattern.search(clause):
                    break
            else:
                continue
            actions_found.add(action)
            for reference in _section_references(clause):
                if reference not in named or priority < named[reference][0]:
                    named[reference] = (priority, action, clause.rstrip(',. ') + '.')
        single = next(iter(actions_found)) if len(actions_found) == 1 else None
        for article in self.articles:
            if not article['children']:
                continue
            chapter, _, section = article['eId'][4:].rpartition('-')
            chapter = chapter or None
            found = named.get((chapter, section)) or named.get((chapter, None))
            if found:
                action, instruction = found[1], found[2]
            else:
                action, instruction = (single or 'amend'), formula
            quoted = ([{'text': article['heading']}] if article['heading'] else []) + \
                [{'text': child['text']} for child in article['children']]
            article['children'][0]['amendment'] = {
                'action': action,
                'instruction': instruction,
                'amended_act': amended,
                'quoted': [{'kind': 'structure', 'children': quoted}],
            }
