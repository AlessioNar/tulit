"""
Parser for Cypriot laws in the PDF of the Official Gazette (Επίσημη Εφημερίδα).

The Government Printing Office publishes the Official Gazette as PDF; laws
appear in its Annex One (Παράρτημα Πρώτο), several to an issue. Each page
is headed with the number of the law it carries ('N. 125(I)/2018'), and the
notes in the left margin give the heading of each section and the laws and
EU acts it refers to:

- the notice of publication ('Ο περί ... Νόμος του 2018 εκδίδεται με
  δημοσίευση ...') gives the recitals' introduction, the title in capitals
  ('ΝΟΜΟΣ ΠΟΥ ΠΡΟΝΟΕΙ ...') the preface, a preamble (Προοίμιο) the recitals
  and 'Η Βουλή των Αντιπροσώπων ψηφίζει ως ακολούθως:' the formula;
- ΜΕΡΟΣ, ΚΕΦΑΛΑΙΟ and ΤΜΗΜΑ headings become divisions;
- each section ('1. Ο παρών Νόμος ...') becomes an article whose heading is
  its margin note ('Συνοπτικός τίτλος.'); subsections '(1)' become par_N,
  with paragraphs '(α)' folded in. The references in the margin (laws, the
  Official Journal of the EU) are left out;
- text quoted by an amendment («...») stays in the amending section, which
  carries a structured ``amendment``;
- annexes (ΠΑΡΑΡΤΗΜΑ) become the annexes.

An issue may hold several laws: ``number`` ('125(I)/2018') picks one.
Needs the ``pdf`` extra.
"""
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Optional

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.pdf.layout import _pdfplumber, join_lines
from tulit.parser.structure import BodyBuilder, ChildrenBuilder

_LATIN = str.maketrans({'Ι': 'I', 'Χ': 'X', 'Α': 'A', 'Β': 'B'})
_HEADER = re.compile(r'^N\.\s*(?P<number>\d+[A-ZΑ-Ω]?\([IΙ]+\)/\d{4})$')
_NOTICE = re.compile(r'εκδίδεται με δημοσίευση')
_NUMBER = re.compile(r'^Αριθμός\s+(?P<num>\d+[A-ZΑ-Ω]?)\((?P<part>[IΙ]+)\)\s+του\s+(?P<year>\d{4})$')
_FOOTER = re.compile(r'^(Τυπώθηκε στο Τυπογραφείο|Τηλ\.:|Αντίτυπα της Επίσημης|_{3,}$|\d{1,5}$)')
_MASTHEAD = re.compile(r'^(ΕΠΙΣΗΜΗ ΕΦΗΜΕΡΙΔΑ|ΤΗΣ ΚΥΠΡΙΑΚΗΣ ΔΗΜΟΚΡΑΤΙΑΣ|ΠΑΡΑΡΤΗΜΑ ΠΡΩΤΟ$|ΝΟΜΟΘΕΣΙΑ - ΜΕΡΟΣ|'
                       r'Αριθμός \d+[A-ZΑ-Ω]? \w+, \d)')
_FORMULA = re.compile(r'^Η Βουλή των Αντιπροσώπων ψηφίζει ως ακολούθως:?$')
_SECTION = re.compile(r'^(?P<num>\d+[Α-ΩA-Z]?)\.(?:-|\s)\s*(?P<rest>.*)$')
_SUBSECTION = re.compile(r'^\((?P<num>\d+[Α-ΩA-Z]?)\)\s')
_DIVISION = re.compile(r'^(?P<kind>ΜΕΡΟΣ|ΚΕΦΑΛΑΙΟ|ΤΜΗΜΑ|ΤΙΤΛΟΣ|ΥΠΟΤΜΗΜΑ)\s+(?P<num>[IVXΙΧ]+|\d+[Α-Ω]?|[Α-Ω]{1,2}΄?)$')
_ANNEX = re.compile(r'^([Α-Ω]+ )?ΠΑΡΑΡΤΗΜΑ( [Α-ΩIVXΙΧ]+)?$')
_REFERENCE = re.compile(r'(\d+[A-ZΑ-Ω]?\([IΙ]+\)\s+του\s+\d{4}|του \d{4}|Επίσημη|Εφημερίδα|L\.?\s?\d|C\.?\s?\d|σ\. \d|'
                        r'Ε\.Ε\.|ΕΕ:|Κ\.Δ\.Π\.|Κ\.Δ\.Π|\d+\.\d+\.\d{4}|^\d+[,.]?$|^Παράρτημα [ΙΙΙ]+)')
DIVISIONS = {'ΜΕΡΟΣ': 'part', 'ΤΙΤΛΟΣ': 'title', 'ΚΕΦΑΛΑΙΟ': 'chapter', 'ΤΜΗΜΑ': 'section', 'ΥΠΟΤΜΗΜΑ': 'subsection'}

# Amending phrases, checked in order
ACTIONS = (
    (r'καταργείται|καταργούνται|διαγράφεται|διαγράφονται|με τη διαγραφή|με την κατάργηση', 'delete'),
    (r'αντικαθίσταται|αντικαθίστανται|με την αντικατάσταση', 'replace'),
    (r'προστίθεται|προστίθενται|με την προσθήκη|με την ένθεση|εντίθεται', 'add'),
    (r'τροποποιείται|τροποποιούνται', 'amend'),
)


def amendment_action(text: str) -> Optional[str]:
    """'Το άρθρο 5 του βασικού νόμου αντικαθίσταται ...' -> 'replace'."""
    for pattern, action in ACTIONS:
        if re.search(pattern, text):
            return action
    return None


def normalise_number(number: str) -> str:
    """'125(Ι)/2018' with a Greek capital iota, or '125(I) του 2018' -> '125(I)/2018'."""
    text = ' '.join(number.split()).translate(_LATIN)
    match = re.match(r'^(?:N\.\s*|Ν\.\s*)?(\d+[A-Z]?)\s*\((I+)\)\s*(?:/|του|of)\s*(\d{4})$', text)
    if not match:
        raise ValueError(f"'{number}' is not a Cypriot law number such as '125(I)/2018'")
    return f'{match.group(1)}({match.group(2)})/{match.group(3)}'


@dataclass
class _Line:
    page: int
    top: float
    x0: float
    text: str
    size: float
    bold: bool
    margin: bool = False


def _text(chars: list[dict]) -> str:
    """The text of a run of characters, with a space where they are set apart."""
    parts: list[str] = []
    previous = None
    for char in sorted(chars, key=lambda c: c['x0']):
        if previous is not None and char['x0'] - previous['x1'] > 1.5 and char['text'] != ' ':
            parts.append(' ')
        parts.append(char['text'])
        previous = char
    return ' '.join(''.join(parts).split())


def _gutter(pdf) -> float:
    """The x position between the margin notes and the body: the emptiest column left of the body."""
    occupancy: Counter = Counter()
    for page in pdf.pages:
        for char in page.chars:
            if char['text'].strip():
                for x in range(int(char['x0']), int(char['x1']) + 1):
                    occupancy[x] += 1
    candidates = range(115, 175)
    return float(min(candidates, key=lambda x: (occupancy[x], -x)))


def read_lines(path: str) -> tuple[list[_Line], float]:
    """Body and margin lines of a Gazette PDF, page by page, and the x position between them."""
    pdfplumber = _pdfplumber()
    try:
        pdf = pdfplumber.open(path)
    except Exception as e:  # pdfplumber raises several unrelated types for unreadable files
        raise FileLoadError(f"Cannot read PDF {path}: {e}") from e
    lines: list[_Line] = []
    with pdf:
        gutter = _gutter(pdf)
        for number, page in enumerate(pdf.pages):
            for found in page.extract_text_lines(return_chars=True, x_tolerance=1.5):
                chars = sorted((c for c in found['chars'] if c['text'].strip()), key=lambda c: c['x0'])
                if not chars:
                    continue
                size = Counter(round(c['size'], 1) for c in chars).most_common(1)[0][0]
                bold = 'Bold' in Counter(c['fontname'] for c in chars).most_common(1)[0][0]
                # Split a row where the margin note ends and the body begins
                split = next((i for i in range(1, len(chars))
                              if chars[i - 1]['x1'] <= gutter + 2 and chars[i]['x0'] >= gutter - 2
                              and chars[i]['x0'] - chars[i - 1]['x1'] >= 6), None)
                if split is None and chars[-1]['x1'] <= gutter + 2:
                    split = len(chars)
                if split:
                    lines.append(_Line(number, found['top'], chars[0]['x0'], _text(chars[:split]), size, bold, True))
                rest = chars[split or 0:]
                if rest:
                    lines.append(_Line(number, found['top'], rest[0]['x0'], _text(rest), size, bold))
    return lines, gutter


class CyprusGazetteParser(Parser):
    """Parses a Cypriot law (Official Gazette PDF) into legalJSON."""

    def __init__(self, number: Optional[str] = None) -> None:
        """``number``: the law's number ('125(I)/2018'), to find it in an issue holding several laws."""
        super().__init__()
        self.number = normalise_number(number) if number else None

    def parse(self, file: str, **options) -> 'CyprusGazetteParser':
        lines, self.gutter = read_lines(file)
        lines = self._own_lines(lines)
        if not lines:
            raise FileLoadError(f"{file} holds no law {self.number or ''}".strip())
        body = [line for line in lines if not line.margin]
        self.notes = [line for line in lines if line.margin]
        # The body's left edge: where most lines start
        self.left = float(Counter(round(line.x0) for line in body).most_common(1)[0][0])
        start = self._read_front(body)
        self._read_body(body[start:])
        return self

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _own_lines(self, lines: list[_Line]) -> list[_Line]:
        """The lines of the requested law (or of the first one), without headers, footers and masthead."""
        # Where each law starts: its notice of publication, followed by its number
        starts: list[tuple[int, Optional[str]]] = []
        for i, line in enumerate(lines):
            if line.margin:
                continue
            match = _NUMBER.match(line.text)
            if match:
                number = f"{match.group('num')}({match.group('part')})/{match.group('year')}".translate(_LATIN)
                notice = i
                for j in range(i - 1, max(i - 8, -1), -1):
                    if not lines[j].margin and re.match(r'^Οι? ', lines[j].text):
                        notice = j
                        break
                starts.append((notice, number))
        if not starts:
            return [line for line in lines if not self._skip(line)]
        index = 0
        if self.number:
            index = next((n for n, (_, number) in enumerate(starts) if number == self.number), None)
            if index is None:
                return []
        begin = starts[index][0]
        end = starts[index + 1][0] if index + 1 < len(starts) else len(lines)
        return [line for line in lines[begin:end] if not self._skip(line)]

    @staticmethod
    def _skip(line: _Line) -> bool:
        return bool(_HEADER.match(line.text) or _FOOTER.match(line.text) or line.size > 10.5
                    or (_MASTHEAD.match(line.text) and line.bold))

    def _read_front(self, lines: list[_Line]) -> int:
        """Notice of publication, number, title, preamble and enacting formula; returns where the body starts."""
        texts = [line.text for line in lines]
        number = next((i for i, text in enumerate(texts) if _NUMBER.match(text)), None)
        formula = next((i for i, text in enumerate(texts) if _FORMULA.match(text)), None)
        first = next((i for i, line in enumerate(lines)
                      if self._section(line) or _DIVISION.match(line.text)), len(lines))
        if number is not None:
            if number:
                self.recitals_init = join_lines(texts[:number])
            title: list[str] = []
            for text in texts[number + 1:formula if formula is not None else first]:
                if text != text.upper():
                    break
                title.append(text)
            self.preface = join_lines(title) or None
            preamble_start = number + 1 + len(title)
        else:
            preamble_start = 0
        if formula is not None:
            self.formula = texts[formula]
            preamble = texts[preamble_start:formula]
            if preamble:
                text = join_lines(preamble)
                self.recitals = [{'eId': 'rct_1', 'text': re.sub(r'^Προοίμιο\.\s*', '', text)}]
            return formula + 1
        return first

    def _section(self, line: _Line) -> Optional[re.Match]:
        """A section's first line: its number, indented from the body's left edge."""
        match = _SECTION.match(line.text)
        if match and match.group('rest') and self.gutter < line.x0 < self.gutter + 45:
            return match
        return None

    def _heading(self, line: _Line, until: Optional[_Line]) -> Optional[str]:
        """The margin note beside a section, up to its full stop, without the references below it."""
        note: list[str] = []
        for margin in self.notes:
            if (margin.page, margin.top) < (line.page, line.top - 2):
                continue
            if until is not None and (margin.page, margin.top) >= (until.page, until.top - 2):
                break
            if margin.page != line.page and not note:
                break
            if _REFERENCE.search(margin.text) and not note:
                break
            note.append(margin.text)
            if margin.text.endswith('.'):
                break
        return join_lines(note) or None

    def _read_body(self, lines: list[_Line]) -> None:
        body = BodyBuilder()
        section: Optional[dict[str, Any]] = None
        annex: Optional[ChildrenBuilder] = None
        paragraph: list[str] = []
        quoting = 0
        basic_act: Optional[str] = None
        division: Optional[dict[str, Any]] = None
        sections = [i for i, line in enumerate(lines) if self._section(line)]

        def flush_paragraph() -> None:
            nonlocal basic_act
            if not paragraph:
                return
            text = join_lines(paragraph)
            paragraph.clear()
            target = annex if annex is not None else (section['children'] if section else None)
            if target is None:
                return
            match = _SUBSECTION.match(text)
            if match and annex is None:
                child = target.add(text, number=match.group('num'))
            elif target.children and annex is None and (re.match(r'^\([α-ωivx]+\)|^«|^Νοείται', text) or quoting):
                target.extend(text)
                current = target.children[-1]
                if current.get('amendment') is not None and '«' in text:
                    current['amendment']['quoted'].append({'kind': 'text', 'text': text})
                return
            else:
                child = target.add(text)
            found = re.search(r'μαζί με (?:τους|τον) (περί .+? Νόμ\w+ .*?)\s*\(που στο εξής θα αναφέρ\w+ ως «ο βασικός '
                              r'νόμος»\)', text)
            if found:
                basic_act = found.group(1)
            action = amendment_action(text) if annex is None else None
            if action:
                quoted = [{'kind': 'text', 'text': q} for q in re.findall(r'«([^«»]{20,})»', text)]
                act = basic_act if 'βασικού νόμου' in text or 'βασικός νόμος' in text else None
                child['amendment'] = {'action': action, 'instruction': text, 'amended_act': act, 'quoted': quoted}

        def flush_section() -> None:
            nonlocal section
            flush_paragraph()
            if section is not None:
                body.article(section['num'], section['heading'], section['children'].children, token=section['token'])
            section = None

        for i, line in enumerate(lines):
            text = line.text
            if quoting:
                paragraph.append(text)
                quoting = max(quoting + text.count('«') - text.count('»'), 0)
                continue
            if section is not None and _ANNEX.match(text) and line.x0 > self.left + 40:
                flush_section()
                annex = ChildrenBuilder()
                self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': text, 'heading': None,
                                     'children': annex.children})
                continue
            if annex is not None:
                if self.annexes[-1]['heading'] is None and not annex.children and not paragraph \
                        and text == text.upper() and line.x0 > self.left + 20:
                    self.annexes[-1]['heading'] = text
                    continue
                if re.match(r'^(\d+\.|\([α-ω\d]+\)|[Α-Ω])', text) and paragraph and \
                        paragraph[-1].endswith(('.', ':', '·', ';')):
                    flush_paragraph()
                paragraph.append(text)
                continue
            match = _DIVISION.match(text)
            if match:
                flush_section()
                division = body.division(DIVISIONS[match.group('kind')], text,
                                         token=match.group('num').translate(_LATIN))
                continue
            if division is not None and text == text.upper() and not self._section(line):
                # The division's heading, in capitals, over one or more lines
                division['heading'] = f"{division['heading']} {text}" if division.get('heading') else text
                continue
            division = None
            match = self._section(line)
            if match:
                flush_section()
                following = next((lines[j] for j in sections if j > i), None)
                section = {'num': f"{match.group('num')}.", 'heading': self._heading(line, following),
                           'token': match.group('num').translate(_LATIN), 'children': ChildrenBuilder()}
                paragraph.append(match.group('rest'))
                quoting = max(text.count('«') - text.count('»'), 0)
                continue
            if section is None:
                continue
            if _SUBSECTION.match(text) or (re.match(r'^\([α-ωivx]+\)\s', text) and paragraph
                                           and paragraph[-1].endswith((':', '·', ';', '.', '−', '-', 'και'))):
                flush_paragraph()
            paragraph.append(text)
            quoting = max(text.count('«') - text.count('»'), 0)
        flush_section()
        flush_paragraph()
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
