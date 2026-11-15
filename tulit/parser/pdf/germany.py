"""
Parser for the German Federal Law Gazette (Bundesgesetzblatt, BGBl.) in PDF.

The Gazette is published as PDF only: since 2023 one PDF per promulgation
on recht.bund.de, set in one column; before, the printed issues, set in
two columns below a title running across the page, of which the bgbl.de
archive cuts one PDF per act, from its first to its last page (so a PDF
can begin with the end of the act before and end with the start of the
next one). An act as promulgated reads:

- the type and title ('Gesetz zur ...') and its date ('Vom 6. Mai 2024')
  give the preface; the enacting clause ('Der Bundestag hat das folgende
  Gesetz beschlossen:', 'Auf Grund des § 5 ... verordnet ...:') the formula;
- an omnibus act (Mantelgesetz) is divided into 'Artikel N'. An Artikel
  that enacts a law (its text has §§ or divisions) becomes a part holding
  them; an Artikel that amends another act ('Änderung des ...') becomes an
  article whose children are the numbered amending instructions, each with
  a structured ``amendment`` (action, instruction, the act amended, the
  quoted text); any other Artikel ('Inkrafttreten') an article;
- 'Teil', 'Kapitel', 'Abschnitt', ... headings become divisions, each
  '§ N' an article whose Absätze '(1)', '(2)' are its children;
- text quoted by an amendment („...“) stays in its instruction, whatever
  headings it holds; a table of contents (Inhaltsübersicht) is left out;
- the engrossment ('Das vorstehende Gesetz wird hiermit ausgefertigt ...'),
  place and date and the signatures become the conclusions, 'Anlage'
  headings after them the annexes; running headers and footnotes are
  dropped.

Needs the ``pdf`` extra. Older issues of the archive are scanned images
without text, which this parser cannot read (``has_text`` tells them apart).
"""
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional, Sequence

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.pdf.layout import _pdfplumber
from tulit.parser.structure import BodyBuilder, ChildrenBuilder
from tulit.parser.xml.ris import german_ordinal

_CHARACTERS = str.maketrans({'ﬀ': 'ff', 'ﬁ': 'fi', 'ﬂ': 'fl', 'ﬃ': 'ffi', 'ﬄ': 'ffl', '\xad': '-', '\xa0': ' '})
_GUTTER = 8.0
"""Least gap between the two columns of a page set in two columns."""

_ARTIKEL = re.compile(r'^Artikel\s+(?P<num>\d+[a-z]?|[IVXLC]+)\s*\**$')
_SECTION = re.compile(r'^§\s*(?P<num>\d+[a-z]?)\s*\**$')
_DIVISION = re.compile(r'^(?P<kind>Buch|Teil|Kapitel|Abschnitt|Unterabschnitt|Titel|Untertitel)\s*'
                       r'(?P<num>\d+[a-z]?|[IVXLC]+)\.?$')
_ORDINAL_DIVISION = re.compile(r'^(?P<ordinal>[A-ZÄÖÜ][a-zäöüß]+)\s+'
                               r'(?P<kind>Buch|Teil|Kapitel|Abschnitt|Unterabschnitt|Titel|Untertitel)$')
DIVISIONS = {'Buch': ('book', -0.5), 'Teil': ('part', 0), 'Kapitel': ('chapter', 2), 'Abschnitt': ('section', 3),
             'Unterabschnitt': ('subsection', 4), 'Titel': ('title', 3.5), 'Untertitel': ('subtitle', 4.5)}
_ANNEX = re.compile(r'^(Anlage|Anhang)(\s+\d+[a-z]?|\s+[IVX]+)?\*?(\s*\((zu|nach)\b.*\)|\s+zu\s+(§|Artikel)\s.*)?$')
_PARAGRAPH = re.compile(r'^\((?P<num>\d+[a-z]?)\)\s')
_INSTRUCTION = re.compile(r'^(?P<num>\d+[a-z]?)\.\s+\S')
_VOM = re.compile(r'^Vom\s+\d{1,2}\.\s*[A-ZÄÖÜ][a-zäöü]+\s+\d{4}\s*\**$')
_TOC = re.compile(r'^Inhaltsübersicht$|^Inhaltsverzeichnis$')
_TOC_ENTRY = re.compile(r'^(§|Artikel|Anlage)\s*\d+[a-z]?\s+\S')
_HEADER = re.compile(r'Bundesgesetzblatt\s*Jahrgang\s*\d{4}|Ausgegeben\s+zu\s+Bonn\s+am|^Bundesgesetzblatt$'
                     r'|bundesgesetzblatt\.de|bundesanzeiger-verlag\.de|^Seite\s+\d+\s+von\s+\d+$')
_IMPRINT = re.compile(r'^Herausgeber:\s*(Der\s+|Das\s+)?Bundesministeri')
_FOOTNOTE = re.compile(r'^(\*+\)?|\d{1,2}\)|[¹²³⁴⁵⁶⁷⁸⁹])\s?\S')
_CLOSING = re.compile(r'^(Die verfassungsmäßigen Rechte des Bundesrates|Das vorstehende Gesetz wird hiermit '
                      r'ausgefertigt|Der Bundesrat hat zugestimmt\.?$)')
_PLACE_DATE = re.compile(r'^[A-ZÄÖÜ][\w .-]{1,30}, den \d{1,2}\.\s*[A-ZÄÖÜ][a-zäöü]+\s+\d{4}$')
_AMENDING_TITLE = re.compile(r'^(Weitere\s+|Erneute\s+|Sonstige\s+|Redaktionelle\s+)?'
                             r'(Änderung(en)?|Folgeänderung(en)?|Aufhebung|Ablösung)\b', re.IGNORECASE)
_CONJUNCTION = re.compile(r'^(und|oder|bis|sowie|beziehungsweise|bzw\.)\b')
_CITATION = re.compile(r'BGBl\.\s*(?:\d{4}\s+)?I{1,3}\s*(?:\d{4}\s*)?(?:S\.\s*\d+|Nr\.\s*\d+[a-z]?)')

# Amending verbs, checked in order
ACTIONS = (
    (r'\baufgehoben\b', 'delete'), (r'\bgestrichen\b', 'delete'), (r'\bentfällt\b|\bentfallen\b', 'delete'),
    (r'\beingefügt\b', 'insert'), (r'\bvorangestellt\b', 'insert'), (r'\bangefügt\b', 'add'),
    (r'\bersetzt\b', 'replace'), (r'\bgefasst\b', 'replace'), (r'\berhält\b.*\bFassung\b', 'replace'),
    (r'\bumnummeriert\b|\bwerden die\b.*\b(Absätze|Nummern|Paragraphen)\b', 'renumber'),
    (r'\bgeändert\b', 'amend'),
)


@dataclass
class _Line:
    page: int
    column: int
    """0 for the page or its left column, 1 for the right column, 2 across both."""
    top: float
    x0: float
    x1: float
    text: str
    size: float
    font: str
    bold: bool
    left: float = 0.0
    right: float = 0.0
    """Edges of the text frame of the line's column."""


def amendment_action(instruction: str) -> str:
    """
    The action of an amending instruction, read from its words outside quotes and before any colon.

    'In § 2 wird das Wort „x“ durch das Wort „y“ ersetzt.' -> 'replace';
    '§ 35 wird wie folgt geändert:' -> 'amend'.
    """
    words = _unquoted(instruction).split(':', 1)[0]
    for pattern, action in ACTIONS:
        if re.search(pattern, words):
            return action
    return 'amend'


def _unquoted(text: str) -> str:
    """Text without what stands in German quotes (nested quotes included)."""
    depth, out = 0, []
    for char in text:
        if char == '„':
            depth += 1
        elif char == '“' and depth:
            depth -= 1
        elif not depth:
            out.append(char)
    return ''.join(out)


def quotations(text: str) -> list[str]:
    """The top-level quotations of a text ('... das Wort „a“ durch das Wort „b“ ...' -> ['a', 'b'])."""
    depth, found, current = 0, [], []
    for char in text:
        if char == '„':
            if depth:
                current.append(char)
            depth += 1
        elif char == '“' and depth:
            depth -= 1
            if depth:
                current.append(char)
            else:
                found.append(' '.join(''.join(current).split()))
                current = []
        elif depth:
            current.append(char)
    if depth and current:
        found.append(' '.join(''.join(current).split()))
    return [quote for quote in found if quote]


def join_lines(texts: Iterable[str]) -> str:
    """
    Join the lines of a paragraph, mending words broken at the line end.

    'Bundesra-' + 'tes' -> 'Bundesrates'; a hyphen before a capital stays part
    of a compound ('Telekommunikation-' + 'Datenschutz') and one before a
    conjunction stands for the omitted part ('Anpassungs-' + 'und').
    """
    joined = ''
    for text in texts:
        text = text.strip()
        if not text:
            continue
        if not joined:
            joined = text
        elif joined.endswith('-') and len(joined) > 1 and joined[-2].isalpha():
            if _CONJUNCTION.match(text):
                joined = f'{joined} {text}'
            elif text[:1].islower():
                joined = joined[:-1] + text
            else:
                joined += text
        else:
            joined = f'{joined} {text}'
    return joined


def _line_text(chars: Sequence[dict]) -> str:
    """The text of a line, with spaces where its characters are set apart (also in letter-spaced names)."""
    visible = [c for c in chars if c['text'].strip()]
    gaps = sorted(b['x0'] - a['x1'] for a, b in zip(visible, visible[1:]))
    median = gaps[len(gaps) // 2] if gaps else 0.0
    size = Counter(round(c.get('size', 0)) for c in visible).most_common(1)[0][0] if visible else 9
    # Words are set apart by about a quarter of the font size, letters by much less; letter-spaced
    # text ('D e r  B u n d e s p r ä s i d e n t') sets its words further apart than its letters
    if median > 0.12 * size and len(visible) >= 3:
        limit = median * 1.6 + 0.5
    else:
        limit = min(0.17 * size, median + 0.11 * size)
    parts: list[str] = []
    previous = None
    for char in chars:
        if not char['text'].strip():
            parts.append(' ')
            continue
        if previous is not None and char['x0'] - previous['x1'] > limit:
            parts.append(' ')
        parts.append(char['text'])
        previous = char
    # Glyphs without a character (check boxes of forms) read '(cid:12)'
    text = re.sub(r'\(cid:\d+\)', ' ', ''.join(parts))
    return ' '.join(text.split()).translate(_CHARACTERS).strip()


def _make_line(chars: list[dict], page: int, column: int) -> Optional[_Line]:
    chars = sorted(chars, key=lambda c: c['x0'])
    text = _line_text(chars)
    visible = [c for c in chars if c['text'].strip()]
    if not text or not visible:
        return None
    sizes = Counter(round(c.get('size', 0), 1) for c in visible)
    fonts = Counter(c.get('fontname', '') for c in visible)
    font = fonts.most_common(1)[0][0]
    return _Line(page=page, column=column, top=min(c['top'] for c in visible), x0=visible[0]['x0'],
                 x1=max(c['x1'] for c in visible), text=text, size=sizes.most_common(1)[0][0], font=font,
                 bold=bool(re.search(r'bold|black|heavy|semibold|,bd', font, re.IGNORECASE)))


def _split(chars: list[dict], middle: float) -> tuple[str, list[dict], list[dict]]:
    """How a line stands to the middle of the page: 'full' across it, 'split' by a gutter, or 'left'/'right'."""
    visible = [c for c in chars if c['text'].strip()]
    left = [c for c in visible if (c['x0'] + c['x1']) / 2 < middle]
    right = [c for c in visible if (c['x0'] + c['x1']) / 2 >= middle]
    if left and right:
        gap = min(c['x0'] for c in right) - max(c['x1'] for c in left)
        return ('split' if gap >= _GUTTER else 'full'), left, right
    return ('left' if left else 'right'), left, right


def read_lines(path: str) -> list[_Line]:
    """The lines of a Gazette PDF in reading order: pages in two columns column by column, below any title."""
    pdfplumber = _pdfplumber()
    try:
        pdf = pdfplumber.open(path)
    except Exception as e:  # pdfplumber raises several unrelated types for unreadable files
        raise FileLoadError(f"Cannot read PDF {path}: {e}") from e
    with pdf:
        pages = []
        for page in pdf.pages:
            page = page.dedupe_chars()
            middle = float(page.width) / 2
            found = [_split(sorted(line['chars'], key=lambda c: c['x0']), middle) + (line,)
                     for line in page.extract_text_lines(return_chars=True, x_tolerance=1.5)]
            pages.append(found)
    # The whole document is set in one column or in two (pages of tables aside)
    split_pages = sum(1 for found in pages if sum(1 for kind, *_ in found if kind == 'split') >= 3)
    two_columns = split_pages >= max(1, 0.3 * len(pages))

    lines: list[_Line] = []
    for number, found in enumerate(pages):
        if not two_columns:
            lines.extend(filter(None, (_make_line(line['chars'], number, 0) for *_, line in found)))
            continue
        left_lines: list[_Line] = []
        right_lines: list[_Line] = []
        for kind, left, right, line in found:
            if kind == 'full':
                lines.extend(left_lines + right_lines)
                left_lines, right_lines = [], []
                made = _make_line(line['chars'], number, 2)
                if made:
                    lines.append(made)
                continue
            if left:
                made = _make_line(left, number, 0)
                if made:
                    left_lines.append(made)
            if right:
                made = _make_line(right, number, 1)
                if made:
                    right_lines.append(made)
        lines.extend(left_lines + right_lines)
    _set_frames(lines)
    return lines


def _set_frames(lines: list[_Line]) -> None:
    """The left and right edges of the body text of each page column, from edges shared by several lines."""
    grouped: dict[tuple[int, int], list[_Line]] = {}
    for line in lines:
        grouped.setdefault((line.page, line.column), []).append(line)
    frames: dict[tuple[int, int], tuple[float, float]] = {}
    for key, group in grouped.items():
        lefts = Counter(round(line.x0) for line in group)
        rights = Counter(round(line.x1) for line in group)
        shared_left = [x for x, count in lefts.items() if count >= 3]
        shared_right = [x for x, count in rights.items() if count >= 2]
        frames[key] = (float(min(shared_left)) if shared_left else min(line.x0 for line in group),
                       float(max(shared_right)) if shared_right else max(line.x1 for line in group))
    for line in lines:
        if line.column == 2 and (line.page, 0) in frames and (line.page, 1) in frames:
            line.left, line.right = frames[(line.page, 0)][0], frames[(line.page, 1)][1]
        else:
            line.left, line.right = frames[(line.page, line.column)]


def _norm(text: str) -> str:
    return re.sub(r'[\W_]+', '', text).lower()


@dataclass
class _Unit:
    """An article (or Artikel) being read: its number, heading lines and children."""
    num: Optional[str]
    token: Optional[str]
    artikel: bool = False
    heading: list[str] = field(default_factory=list)
    kind: Optional[str] = None
    """None until its content shows it: 'article' or 'amending' (an Artikel enacting a law becomes a division)."""
    lines: list[tuple['_Line', bool]] = field(default_factory=list)
    """Its text lines, with whether each stands in quotes."""


class BundesgesetzblattParser(Parser):
    """Parses an act of the German Federal Law Gazette (PDF) into legalJSON."""

    def __init__(self, title: Optional[str] = None, annexes: Sequence[str] = ()) -> None:
        """
        ``title``: the act's title, as the archive lists it, to find the act on
        a first page it shares with the act before; ``annexes``: PDFs of
        annexes published apart from the text.
        """
        super().__init__()
        self.title = title
        self.annex_files = list(annexes)

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def parse(self, file: str, title: Optional[str] = None, annexes: Optional[Sequence[str]] = None,
              **options: Any) -> 'BundesgesetzblattParser':
        """Parse the PDF of an act (``title`` and ``annexes`` override those given to the constructor)."""
        title = title or self.title
        annexes = self.annex_files if annexes is None else annexes
        lines = read_lines(file)
        if not lines:
            raise FileLoadError(f"{file} has no text (a scanned issue?)")
        self._measure(lines)
        lines = self._clean(lines)
        lines = self._front(lines, title)
        # The text of the act itself, now that its start is known (a first page may hold the end of another)
        self._measure(lines)
        self._read(lines)
        for path in annexes:
            annex_lines = self._clean(read_lines(path))
            self._read_annex_file(annex_lines)
        return self

    # ===== layout =====

    def _measure(self, lines: list[_Line]) -> None:
        sizes: Counter = Counter()
        fonts: Counter = Counter()
        # The body text: lines filling their column between the date of the act and the place and date of
        # its signature (annexes, often forms or treaties in two languages, come after)
        start = next((i for i, line in enumerate(lines) if _VOM.match(line.text)), 0)
        end = next((i for i in range(start, len(lines)) if _PLACE_DATE.match(lines[i].text)), len(lines))
        full = [line for line in lines[start:end] if line.x1 - line.x0 >= 0.7 * (line.right - line.left)]
        if len(full) < 5:
            full = [line for line in lines if line.page < 3 and line.x1 - line.x0 >= 0.7 * (line.right - line.left)]
        for line in full if len(full) >= 5 else lines:
            sizes[line.size] += len(line.text)
            fonts[line.font] += len(line.text)
        self._size = sizes.most_common(1)[0][0]
        self._font = fonts.most_common(1)[0][0]
        pitches = Counter(round(b.top - a.top) for a, b in zip(lines, lines[1:])
                          if a.page == b.page and a.column == b.column and 0 < b.top - a.top < 3 * self._size)
        self._pitch = float(pitches.most_common(1)[0][0]) if pitches else self._size * 1.2

    def _plain(self, line: _Line) -> bool:
        """Whether a line is set as body text: its font and size, not bold."""
        return not line.bold and line.font == self._font and abs(line.size - self._size) < 0.6

    @staticmethod
    def _set_in(line: _Line) -> bool:
        """Whether a line starts well inside its column (a centred heading), not at its margin."""
        return line.x0 > line.left + 12

    @staticmethod
    def _centred(line: _Line) -> bool:
        return abs((line.x0 + line.x1) / 2 - (line.left + line.right) / 2) < 40

    def _clean(self, lines: list[_Line]) -> list[_Line]:
        """Drop running headers, the imprint and footnotes."""
        kept: list[_Line] = []
        dropping: Optional[tuple[int, int]] = None
        for line in lines:
            small = line.size < self._size * 0.9
            if dropping == (line.page, line.column) and small:
                continue
            dropping = None
            masthead = line.size >= self._size * 1.4 and re.match(r'^Teil\s+I{1,2}$', line.text)
            if masthead or _HEADER.search(line.text) or _HEADER.search(line.text.replace(' ', '')):
                continue
            if _IMPRINT.match(line.text) or (small and _FOOTNOTE.match(line.text)):
                dropping = (line.page, line.column)
                continue
            kept.append(line)
        return kept

    # ===== title and enacting clause =====

    def _front(self, lines: list[_Line], title: Optional[str]) -> list[_Line]:
        """Read the title from the head of the act; returns the lines after its date ('Vom ...')."""
        start = 0
        if title:
            target = _norm(title)[:60]
            for index in range(len(lines)):
                window = _norm(' '.join(line.text for line in lines[index:index + 8]))
                if target and window.startswith(target):
                    start = index
                    break
        vom = next((i for i in range(start, min(len(lines), start + 40)) if _VOM.match(lines[i].text)), None)
        if vom is None:
            vom = next((i for i, line in enumerate(lines) if _VOM.match(line.text)), None)
        if vom is None:
            # A notice without a date ('Hinweis auf ...'): its title is set larger than its text
            end = start
            while end < len(lines) and lines[end].size >= self._size * 1.12:
                end += 1
            self.preface = title or re.sub(r'\s*\*+\)?', '', join_lines(line.text for line in lines[start:end])) or None
            return lines[end:] if not title else lines[start:]
        if not title or start >= vom:
            # The title: the lines set larger than the text just before the date
            start = vom
            while start > 0 and lines[start - 1].size >= self._size * 1.12:
                start -= 1
        self.preface = re.sub(r'\s*\*+\)?', '', join_lines(line.text for line in lines[start:vom])) or title
        return lines[vom + 1:]

    def _is_heading(self, line: _Line) -> Optional[tuple[str, re.Match]]:
        """Whether a line is the number line of an Artikel, §, division or annex heading."""
        for kind, pattern in (('artikel', _ARTIKEL), ('section', _SECTION), ('division', _DIVISION),
                              ('division', _ORDINAL_DIVISION), ('annex', _ANNEX)):
            # Headings are centred; an annex heading may stand at the margin, set apart in bold
            if not (self._set_in(line) or kind == 'annex' and not self._plain(line)):
                continue
            match = pattern.match(line.text)
            if match and (kind != 'division' or 'ordinal' not in match.groupdict()
                          or german_ordinal(match.group('ordinal'))):
                return kind, match
        return None

    # ===== body =====

    def _read(self, lines: list[_Line]) -> None:
        self._body = BodyBuilder()
        self._unit: Optional[_Unit] = None
        self._capture: Optional[Any] = None
        self._annex: Optional[dict[str, Any]] = None
        self._phase = 'formula'
        self._formula: list[str] = []
        self._closing: list[str] = []
        self._signatures: list[str] = []
        self._depth = 0
        self._toc: Optional[list[_Line]] = None
        self._has_headings = self._headings_follow(lines)
        # Without headings, an enacting clause ('Auf Grund ... verordnet ...:') opens the text, if any
        self._formula_end = next((i for i, line in enumerate(lines[:8]) if line.text.rstrip().endswith(':')), -1)
        self._lines = lines
        for self._index, line in enumerate(lines):
            if self._line(line) == 'end':
                break
        self._flush()
        self._close_annex()
        self.formula = join_lines(self._formula) or None
        self.chapters, self.articles, self.structure = (self._body.chapters, self._body.articles,
                                                        self._body.structure)
        if self._closing or self._signatures:
            self.conclusions = {'conclusion_text': join_lines(self._closing) or None,
                                'signature': ', '.join(self._signatures) or None}

    def _headings_follow(self, lines: list[_Line]) -> bool:
        """Whether the act is divided into Artikel or §§ (a short notice may be one block of text)."""
        depth = 0
        for line in lines:
            quoted = depth > 0 or line.text.startswith('„')
            depth = max(0, depth + line.text.count('„') - line.text.count('“'))
            found = None if quoted else self._is_heading(line)
            if found and found[0] in ('artikel', 'section', 'division'):
                return True
            if _CLOSING.match(line.text) or _PLACE_DATE.match(line.text):
                return False
        return False

    def _line(self, line: _Line) -> Optional[str]:
        text = line.text
        quoted = self._depth > 0 or text.startswith('„')
        self._depth = max(0, self._depth + text.count('„') - text.count('“'))
        heading = None if quoted else self._is_heading(line)

        # The end of the act: the title of the next one, after the signatures
        if self._phase in ('conclusions', 'annex') and line.size >= self._size * 1.25 and heading is None \
                and self._next_act():
            return 'end'
        if not quoted and (_CLOSING.match(text) or (_PLACE_DATE.match(text) and self._phase != 'annex')):
            self._flush()
            self._phase = 'conclusions'
            self._closing.append(text)
            return None
        within_anhang = self._annex is not None and (self._annex['num'] or '').startswith('Anhang')
        if heading and heading[0] == 'annex' and not (within_anhang and text.startswith('Anlage')) and (
                self._phase in ('conclusions', 'annex') or not self._amending()):
            self._flush()
            self._close_annex()
            self._phase = 'annex'
            self._annex = {'num': re.sub(r'\*+', '', text), 'heading': [], 'lines': []}
            self._capture = self._annex
            return None
        if self._phase == 'conclusions' and self._signatures and (line.bold or line.size >= self._size * 1.2) \
                and not _PLACE_DATE.match(text):
            # A heading after the signatures: a text published with the act (a treaty, 'EU-Rechtsakte:')
            self._phase = 'annex'
            self._annex = {'num': None, 'heading': [], 'lines': []}
            self._capture = self._annex
        if self._phase == 'conclusions':
            dated = any(_PLACE_DATE.match(closing) for closing in self._closing)
            if not dated or _PLACE_DATE.match(text):
                # The engrossment and the place and date, before the signatures
                self._closing.append(text)
            elif self._signatures and text[:1].islower():
                self._signatures[-1] = f'{self._signatures[-1]} {text}'
            else:
                self._signatures.append(text)
            return None
        if self._phase == 'annex' and heading and heading[0] == 'artikel' and not self._closing:
            # The annexes of an Artikel end where the next Artikel begins
            self._close_annex()
            self._phase = 'body'
        if self._phase == 'annex':
            annex = self._annex
            reference = not annex['heading'] and not annex['lines'] and re.match(r'^\((zu|nach)\b.*\)$', text)
            if reference or self._capture is annex and not self._plain(line) and len(annex['heading']) < 4 \
                    and (annex['num'] is None or self._centred(line)):
                annex['heading'].append(text)
            else:
                self._capture = None
                annex['lines'].append(line)
            return None

        # A table of contents, up to the first heading of the text
        if not quoted and _TOC.match(text.replace(' ', '')):
            self._toc = []
            self._phase = 'body'
            return None
        if self._toc is not None:
            if heading and heading[0] in ('artikel', 'section'):
                buffered, self._toc = self._toc, None
                self._replay_toc(buffered)
            else:
                self._toc.append(line)
                return None

        if self._phase == 'formula':
            if heading is None and self._has_headings:
                self._formula.append(text)
                return None
            if heading is None and self._index <= self._formula_end:
                self._formula.append(text)
                return None
            self._phase = 'body'

        # Heading lines after a number line ('§ 3' / 'Verarbeitung durch öffentliche Stellen')
        if self._capture is not None:
            if heading is None and not quoted and not self._plain(line) and len(self._capture_lines()) < 12 \
                    and not _PARAGRAPH.match(text):
                self._capture_lines().append(re.sub(r'\*+$', '', text))
                return None
            self._close_capture()

        if heading and heading[0] == 'artikel':
            self._flush()
            self._unit = _Unit(num=f"Artikel {heading[1].group('num')}", token=heading[1].group('num'),
                               artikel=True)
            self._capture = self._unit
            return None
        if heading and heading[0] in ('section', 'division') and not self._amending():
            self._enacting()
            self._flush()
            if heading[0] == 'section':
                self._unit = _Unit(num=f"§ {heading[1].group('num')}", token=heading[1].group('num'), kind='article')
                self._capture = self._unit
            else:
                self._division(heading[1], text)
            return None

        self._content(line, quoted)
        return None

    def _next_act(self) -> bool:
        """Whether a large line after the signatures is the title of the next act: its date ('Vom ...') follows."""
        following = self._lines[self._index + 1:self._index + 12]
        return any(_VOM.match(line.text) for line in following)

    def _capture_lines(self) -> list[str]:
        capture = self._capture
        if isinstance(capture, _Unit):
            return capture.heading
        return capture['heading']

    def _replay_toc(self, buffered: list[_Line]) -> None:
        """The division headings that follow the table of contents and precede its first § or Artikel."""
        last_entry = max((i for i, line in enumerate(buffered) if _TOC_ENTRY.match(line.text)), default=-1)
        tail = buffered[last_entry + 1:]
        first = next((i for i, line in enumerate(tail) if (self._is_heading(line) or ('', None))[0] == 'division'),
                     None)
        if first is None:
            return
        for line in tail[first:]:
            self._line(line)

    def _enacting(self) -> None:
        """An Artikel whose content starts with a § or a division enacts a law: it becomes a part."""
        unit = self._unit
        if unit is None or not unit.artikel or unit.kind is not None or unit.lines:
            return
        self._body.division('part', unit.num, ' '.join(unit.heading) or None, token=unit.token, rank=-1)
        self._unit = None

    def _division(self, match: re.Match, text: str) -> None:
        kind = match.group('kind')
        type_, rank = DIVISIONS[kind]
        if 'ordinal' in match.groupdict():
            token = str(german_ordinal(match.group('ordinal')))
        else:
            token = match.group('num')
        chapter = self._body.division(type_, text, None, token=token, rank=rank)
        chapter['heading'] = None
        self._capture = {'heading': [], 'chapter': chapter}

    def _content(self, line: _Line, quoted: bool) -> None:
        if self._unit is None:
            # Text outside any article: an act without §§, or the text after a division heading
            self._unit = _Unit(num=None, token=None)
        self._unit.lines.append((line, quoted))

    @staticmethod
    def _decide(unit: _Unit) -> str:
        """
        Whether an Artikel amends other acts: its heading says so ('Änderung des ...'), or, without a
        heading, its first sentence ('Die ... Verordnung vom ... (BGBl. I S. 5) wird wie folgt geändert:').
        """
        if unit.kind is None:
            heading = ' '.join(unit.heading)
            opening = _unquoted(join_lines(line.text for line, _ in unit.lines[:10]))
            # Its first paragraph, up to a colon ('... wird wie folgt geändert:')
            first = re.split(r'\s\(2\)\s', opening.split(':')[0])[0][:800]
            instructs = re.search(r'wie folgt geändert', first) or (
                _CITATION.search(first) and re.search(r'\b(ersetzt|eingefügt|angefügt|gestrichen|aufgehoben|'
                                                      r'gefasst|vorangestellt)\b|\berhält\b.*\bFassung\b', first))
            unit.kind = 'amending' if _AMENDING_TITLE.match(heading) or (not heading and instructs) else 'article'
        return unit.kind

    def _amending(self) -> bool:
        """Whether the Artikel being read amends other acts (its headings are then quoted text)."""
        unit = self._unit
        if unit is None:
            return False
        if unit.kind is None and not unit.lines:
            # Nothing read yet: only its heading tells
            return bool(_AMENDING_TITLE.match(' '.join(unit.heading)))
        return self._decide(unit) == 'amending'

    def _items(self, unit: _Unit) -> list[dict[str, Any]]:
        """The children of an article: its numbered paragraphs or amending instructions."""
        items: list[dict[str, Any]] = []
        amending = self._decide(unit) == 'amending'
        for line, quoted in unit.lines:
            text = line.text
            indented = line.x0 > line.left + 4
            if not quoted:
                if amending:
                    match = _INSTRUCTION.match(text) or (_PARAGRAPH.match(text) if indented else None)
                else:
                    match = _PARAGRAPH.match(text) if indented else None
                numbered = [item for item in items if item['num']]
                if match and self._follows(numbered[-1]['num'] if numbered else None, match.group('num')):
                    items.append({'num': match.group('num'), 'lines': [text]})
                    continue
            # The text of a notice, outside any article: a new paragraph starts with an indented line
            new_paragraph = unit.num is None and not quoted and items and items[-1]['lines'] \
                and 6 <= line.x0 - line.left <= 14 and items[-1]['lines'][-1].rstrip().endswith(('.', ':'))
            if not items or new_paragraph:
                items.append({'num': None, 'lines': []})
            items[-1]['lines'].append(text)
        return items

    @staticmethod
    def _follows(previous: Optional[str], number: str) -> bool:
        """Whether a paragraph or instruction number continues the sequence ('3' after '2', '2a' after '2')."""
        digits = int(re.match(r'\d+', number).group(0))
        if previous is None:
            return digits == 1
        last = int(re.match(r'\d+', previous).group(0))
        if number[-1].isalpha():
            return digits == last
        return digits == last + 1

    def _flush(self) -> None:
        """Add the article being read."""
        self._close_capture()
        unit, self._unit = self._unit, None
        if unit is None:
            return
        if unit.artikel:
            # An Artikel stands outside the law the Artikel before it enacted
            self._body.close_divisions()
        children = ChildrenBuilder()
        intro_act = None
        texts = [(item['num'], join_lines(item['lines'])) for item in self._items(unit)]
        texts = [(num, text) for num, text in texts if text]
        numbered = any(num for num, _ in texts)
        for num, text in texts:
            child = children.add(text, number=num)
            if unit.kind != 'amending':
                continue
            citation = _CITATION.search(_unquoted(text))
            if num is None and numbered:
                # The sentence naming the act amended ('Das ... Gesetz vom ... wird wie folgt geändert:')
                intro_act = citation.group(0) if citation else intro_act
                continue
            child['amendment'] = {
                'action': amendment_action(text),
                'instruction': text,
                'amended_act': intro_act or (citation.group(0) if citation else None),
                'quoted': [{'kind': 'text', 'text': quote} for quote in quotations(text)],
            }
        self._body.article(unit.num, ' '.join(unit.heading) or None, children.children, token=unit.token)

    def _close_capture(self) -> None:
        capture = self._capture
        if isinstance(capture, dict) and 'chapter' in capture:
            capture['chapter']['heading'] = join_lines(capture['heading']) or None
        self._capture = None

    def _close_annex(self) -> None:
        annex, self._annex = self._annex, None
        if annex is None:
            return
        children = ChildrenBuilder()
        block: list[str] = []
        previous: Optional[_Line] = None
        for line in annex['lines']:
            gap = line.top - previous.top if previous and previous.page == line.page else None
            if block and (gap is None or gap > self._pitch * 1.45 or gap < 0
                          or _PARAGRAPH.match(line.text) or _INSTRUCTION.match(line.text)):
                children.add(join_lines(block))
                block = []
            block.append(line.text)
            previous = line
        if block:
            children.add(join_lines(block))
        if not children.children and not annex['heading']:
            return
        # 'Anlage 2 (zu § 3)' -> anx_2; 'Anlage', 'Anhang zu Artikel 1' and lists without a number by position
        number = re.match(r'^Anlage\s+(\d+[a-z]?|[IVX]+)\b', annex['num'] or '')
        used = {a['eId'] for a in self.annexes}
        token = number.group(1) if number and f'anx_{number.group(1)}' not in used else str(len(self.annexes) + 1)
        while f'anx_{token}' in used:
            token = f'{token}-{len(used)}'
        self.annexes.append({'eId': f'anx_{token}', 'num': annex['num'],
                             'heading': join_lines(annex['heading']) or None, 'children': children.children})

    def _read_annex_file(self, lines: list[_Line]) -> None:
        """An annex published as a PDF of its own."""
        self._phase = 'annex'
        self._depth = 0
        if not lines:
            return
        first = lines[0]
        if _ANNEX.match(first.text):
            self._annex = {'num': first.text, 'heading': [], 'lines': []}
            self._capture = self._annex
            lines = lines[1:]
        else:
            self._annex = {'num': f'Anlage {len(self.annexes) + 1}', 'heading': [], 'lines': []}
        for line in lines:
            self._line(line)
        self._close_annex()
