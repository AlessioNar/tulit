"""
Parser for Greek legislation in the PDF of the Government Gazette (ΦΕΚ).

The National Printing House publishes each issue of the Government Gazette
(Εφημερίδα της Κυβερνήσεως) as PDF, set in two columns; laws, presidential
decrees and acts of legislative content appear in Part A (Τεύχος Α΄), one
law to an issue, sometimes several decrees:

- the masthead, the page headers ('3382 ΕΦΗΜΕΡΙΔΑ ΤΗΣ ΚΥΒΕΡΝΗΣΕΩΣ
  Τεύχος A’ 137/29.08.2019'), the contents of older issues and the table
  of contents (ΠΙΝΑΚΑΣ ΠΕΡΙΕΧΟΜΕΝΩΝ) of recent laws are left out;
- the number and title ('ΝΟΜΟΣ ΥΠ’ ΑΡΙΘΜ. 4624 Αρχή Προστασίας ...') give
  the preface, the President's title and 'Εκδίδομε τον ακόλουθο νόμο που
  ψήφισε η Βουλή:' the formula, and the citations of a decree ('Έχοντας
  υπόψη: 1. ...') the recitals;
- ΜΕΡΟΣ, ΤΙΤΛΟΣ, ΚΕΦΑΛΑΙΟ and ΤΜΗΜΑ headings become divisions;
- each 'Άρθρο N' becomes an article, the lines set in below it its heading;
  numbered paragraphs ('1. ...') become par_N, with points ('α) ...')
  folded in;
- text quoted by an amendment («...») stays in the amending paragraph,
  which carries a structured ``amendment``;
- the order to publish ('Παραγγέλλομε τη δημοσίευση ...'), the place and
  date and the signatures become the conclusions, the annexes (ΠΑΡΑΡΤΗΜΑ)
  the annexes.

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

_GREEK = str.maketrans({'∆': 'Δ', '’': '΄', "'": '΄', '´': '΄', '−': '-'})
_HEADER = re.compile(r'(ΕΦΗΜΕΡΙ[ΔΣ]Α?Σ?\s+T?Τ?ΗΣ ΚΥΒΕΡΝΗΣΕΩΣ|Τεύχος [AΑΒΓΔ]΄?\s*\d+/\d{2}\.\d{2}\.\d{4})')
_MASTHEAD = re.compile(r'Αρ\. Φύλλου|ΤΕΥΧΟΣ (ΠΡΩΤΟ|ΔΕΥΤΕΡΟ|ΤΡΙΤΟ|ΤΕΤΑΡΤΟ)')
_BARCODE = re.compile(r'^\*\d{10,}\*$')
_BACK_COVER = re.compile(r'helpdesk\.et@et\.gr|grammateia@et\.gr')
_NUMBER = re.compile(r'^(?P<kind>ΝΟΜΟΣ|NOMOΣ|ΠΡΟΕΔΡΙΚΟ ΔΙΑΤΑΓΜΑ|ΠΡΑΞΗ ΝΟΜΟΘΕΤΙΚΟΥ ΠΕΡΙΕΧΟΜΕΝΟΥ)\s*'
                     r'(?:ΥΠ΄?\s*ΑΡΙΘ[ΜM]?\.?\s*(?P<num>\d+))?')
_ARTICLE = re.compile(r'^Άρθρο\s+(?P<num>\d+[Α-Ωα-ω]?|πρώτο|δεύτερο|τρίτο|μόνο|[Α-Ω]+΄?)\s*$')
_DIVISION = re.compile(r'^(?P<kind>ΜΕΡΟΣ|ΤΙΤΛΟΣ|ΚΕΦΑΛΑΙΟ|ΤΜΗΜΑ|ΥΠΟΚΕΦΑΛΑΙΟ)\s+(?P<num>[Α-Ω]{1,3}΄?|\d+|[IVX]+)\s*$')
_PARAGRAPH = re.compile(r'^(?P<num>\d+[α-ω]?)\.\s+\S')
_POINT = re.compile(r'^(\(?[α-ω]{1,3}[΄\']?\)|\(?[ivx]+\)|-|–|•)\s')
_FORMULA = re.compile(r'(Εκδίδομε τον ακόλουθο νόμο που ψήφισε η Βουλή:?|αποφασίζουμε:?|'
                      r'Εκδίδομε την ακόλουθη πράξη νομοθετικού περιεχομένου:?)\s*$', re.IGNORECASE)
_CLOSING = re.compile(r'^(Παραγγέλλομε τη δημοσίευση|Αθήνα, \d|Στον .* αναθέτουμε τη δημοσίευση)')
_TOC = re.compile(r'^ΠΙΝΑΚΑΣ ΠΕΡΙΕΧΟΜΕΝΩΝ$')
_ANNEX = re.compile(r'^ΠΑΡΑΡΤΗΜΑ(\s+[Α-ΩIVX\d]+΄?)?$')
DIVISIONS = {'ΜΕΡΟΣ': 'part', 'ΤΙΤΛΟΣ': 'title', 'ΚΕΦΑΛΑΙΟ': 'chapter', 'ΤΜΗΜΑ': 'section',
             'ΥΠΟΚΕΦΑΛΑΙΟ': 'subsection'}
ORDINALS = {'πρώτο': '1', 'δεύτερο': '2', 'τρίτο': '3', 'μόνο': '1'}

# Amending phrases, checked in order
ACTIONS = (
    (r'καταργείται|καταργούνται|διαγράφεται|διαγράφονται|απαλείφεται|απαλείφονται', 'delete'),
    (r'αντικαθίσταται|αντικαθίστανται', 'replace'),
    (r'προστίθεται|προστίθενται|συμπληρώνεται|συμπληρώνονται', 'add'),
    (r'τροποποιείται|τροποποιούνται', 'amend'),
)


def amendment_action(text: str) -> Optional[str]:
    """'Το άρθρο 5 του ν. 4624/2019 αντικαθίσταται ως εξής:' -> 'replace'."""
    for pattern, action in ACTIONS:
        if re.search(pattern, text):
            return action
    return None


def _amended_act(text: str) -> Optional[str]:
    """The act an instruction names ('... του ν. 4624/2019 (Α΄ 137) ...')."""
    match = re.search(r'\b(ν\.\s*\d+/\d{4}|π\.δ\.\s*\d+/\d{4}|ν\.δ\.\s*\d+/\d{4}|α\.ν\.\s*\d+/\d{4})', text)
    return match.group(1) if match else None


@dataclass
class _Line:
    page: int
    column: int
    top: float
    x0: float
    x1: float
    text: str
    size: float
    bold: bool
    left: float = 0.0
    right: float = 0.0
    """Edges of the line's column."""


def _text(chars: list[dict]) -> str:
    parts: list[str] = []
    previous = None
    for char in sorted(chars, key=lambda c: c['x0']):
        if previous is not None and char['x0'] - previous['x1'] > 1.5 and char['text'] != ' ':
            parts.append(' ')
        parts.append(char['text'])
        previous = char
    return ' '.join(''.join(parts).split()).translate(_GREEK)


def _gutter(page) -> float:
    """The x position between the two columns: the emptiest position around the middle of the page."""
    occupancy: Counter = Counter()
    for char in page.chars:
        if char['text'].strip() and char['size'] >= 8.5:
            for x in range(int(char['x0']), int(char['x1']) + 1):
                occupancy[x] += 1
    middle = int(page.width / 2)
    return float(min(range(middle - 20, middle + 21), key=lambda x: (occupancy[x], abs(x - middle))))


def _crosses(chars: list[dict], gutter: float) -> bool:
    """Whether a line runs across the gutter: no gap between its words there."""
    chars = sorted((c for c in chars if c['text'].strip()), key=lambda c: c['x0'])
    for previous, char in zip(chars, chars[1:]):
        if previous['x1'] <= gutter + 1 and char['x0'] >= gutter - 1:
            return char['x0'] - previous['x1'] < 3
        if previous['x0'] < gutter < previous['x1']:
            return True
    return False


def read_lines(path: str) -> list[_Line]:
    """The lines of a Gazette PDF, column by column, without the masthead, page headers and footers."""
    pdfplumber = _pdfplumber()
    try:
        pdf = pdfplumber.open(path)
    except Exception as e:  # pdfplumber raises several unrelated types for unreadable files
        raise FileLoadError(f"Cannot read PDF {path}: {e}") from e
    lines: list[_Line] = []
    with pdf:
        for number, page in enumerate(pdf.pages):
            gutter = _gutter(page)
            found = page.extract_text_lines(return_chars=True, x_tolerance=1.5)
            # The page header and the masthead span the page; the columns start below them
            header_bottom = 0.0
            for line in found:
                text = _text(line['chars'])
                large = max((c['size'] for c in line['chars']), default=0) > 12
                if line['top'] < 330 and (_HEADER.search(text) or _MASTHEAD.search(text) or large):
                    header_bottom = max(header_bottom, line['bottom'])
            if any(_BACK_COVER.search(_text(line['chars'])) for line in found):
                # The National Printing House's notice on the last page
                continue
            body = [line for line in found if line['top'] > header_bottom + 1
                    and Counter(round(c['size'], 1) for c in line['chars']).most_common(1)[0][0] >= 8.5]
            # Pages set in one column (the signatures, some annexes) are read across
            crossing = sum(1 for line in body if _crosses(line['chars'], gutter))
            single = bool(body) and crossing > len(body) * 0.25
            columns: list[list[_Line]] = [[], []]
            for line in body:
                chars = [c for c in line['chars'] if c['text'].strip()]
                if not chars:
                    continue
                size = Counter(round(c['size'], 1) for c in chars).most_common(1)[0][0]
                bold = 'Bold' in Counter(c['fontname'] for c in chars).most_common(1)[0][0]
                for column in (0, 1):
                    if single:
                        part = chars if column == 0 else []
                    else:
                        part = [c for c in chars if ((c['x0'] + c['x1']) / 2 < gutter) == (column == 0)]
                    if part:
                        text = _text(part)
                        if text and not _BARCODE.match(text):
                            columns[column].append(_Line(number, column, line['top'], part[0]['x0'],
                                                         max(c['x1'] for c in part), text, size, bold))
            for column_lines in columns:
                if not column_lines:
                    continue
                # The column's left edge: the outermost position shared by several lines
                lefts = Counter(round(line.x0) for line in column_lines)
                rights = Counter(round(line.x1) for line in column_lines)
                left = min((x for x, n in lefts.items() if n >= 3), default=min(lefts))
                right = max((x for x, n in rights.items() if n >= 3), default=max(rights))
                for line in column_lines:
                    line.left, line.right = float(left), float(right)
                lines.extend(sorted(column_lines, key=lambda line: line.top))
    return lines


class GovernmentGazetteParser(Parser):
    """Parses a Greek law, decree or act of legislative content (ΦΕΚ PDF) into legalJSON."""

    def __init__(self, number: Optional[str] = None) -> None:
        """``number``: the act's number ('70'), to find it in an issue holding several acts."""
        super().__init__()
        self.number = str(number) if number else None

    def parse(self, file: str, **options) -> 'GovernmentGazetteParser':
        lines = self._own_lines(read_lines(file))
        if not lines:
            raise FileLoadError(f"{file} holds no act {self.number or ''}".strip())
        lines = self._without_contents(lines)
        start = self._read_front(lines)
        self._read_body(lines[start:])
        return self

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _own_lines(self, lines: list[_Line]) -> list[_Line]:
        """The lines of the requested act (or of the first one) in an issue that may hold several."""
        starts = [(i, _NUMBER.match(line.text)) for i, line in enumerate(lines) if _NUMBER.match(line.text)]
        if not starts:
            return lines
        index = 0
        if self.number:
            index = next((n for n, (_, match) in enumerate(starts) if match.group('num') == self.number), None)
            if index is None:
                return []
        begin = starts[index][0]
        end = starts[index + 1][0] if index + 1 < len(starts) else len(lines)
        # The item number ('(2)') and group heading of the next act precede it
        while end > begin + 1 and re.fullmatch(r'\(\d+\)|[Α-Ω ]+ΔΙΑΤΑΓΜΑΤΑ|ΝΟΜΟΙ', lines[end - 1].text):
            end -= 1
        return lines[begin:end]

    @staticmethod
    def _without_contents(lines: list[_Line]) -> list[_Line]:
        """
        Without the table of contents of recent laws.

        It ends at the President's title or the formula when it precedes them, or else at the first article
        heading standing alone ('Άρθρο 1'; its entries carry their titles), with the divisions above it.
        """
        toc = next((i for i, line in enumerate(lines) if _TOC.match(line.text)), None)
        if toc is None:
            return lines
        end = next((i for i in range(toc + 1, len(lines))
                    if re.match(r'^[ΟΗH] ΠΡΟΕΔΡΟΣ', lines[i].text) or _FORMULA.search(lines[i].text)
                    or _ARTICLE.match(lines[i].text)), None)
        if end is None:
            return lines
        if _ARTICLE.match(lines[end].text):
            # Back over the divisions opening the body: each a heading line and its title in capitals
            while True:
                division = next((k for k in range(end - 1, max(toc, end - 5), -1) if _DIVISION.match(lines[k].text)),
                                None)
                titles = [lines[k].text for k in range(division + 1, end)] if division is not None else []
                if division is None or not all(text == text.upper() for text in titles):
                    break
                end = division
        return lines[:toc] + lines[end:]

    def _read_front(self, lines: list[_Line]) -> int:
        """Number, title, formula and citations; returns where the body starts."""
        texts = [line.text for line in lines]
        formula = next((i for i, text in enumerate(texts) if _FORMULA.search(text)), None)
        if formula is None:
            return next((i for i, line in enumerate(lines) if _ARTICLE.match(line.text)), len(lines))
        president = next((i for i in range(formula + 1) if re.match(r'^[ΟΗH] ΠΡΟΕΔΡΟΣ', texts[i])), None)
        end = president if president is not None else formula
        self.preface = join_lines(texts[:end]) or None
        opening = texts[end:formula + 1]
        # A decree's citations ('Έχοντας υπόψη: 1. ...') run from the President's title to the formula
        citations = next((i for i, text in enumerate(opening) if text.startswith('Έχοντας υπόψη')), None)
        if citations is not None:
            self.formula = join_lines(opening[:citations] + opening[-1:])
            self.recitals_init = 'Έχοντας υπόψη:'
            recitals: list[list[str]] = []
            rest = opening[citations][len('Έχοντας υπόψη'):].lstrip(' :')
            for text in ([rest] if rest else []) + opening[citations + 1:-1]:
                if re.match(r'^\d+\.\s', text) or not recitals:
                    recitals.append([text])
                else:
                    recitals[-1].append(text)
            self.recitals = [{'eId': f'rct_{n}', 'text': join_lines(r)} for n, r in enumerate(recitals, start=1)]
        else:
            self.formula = join_lines(opening)
        return formula + 1

    def _read_body(self, lines: list[_Line]) -> None:
        body = BodyBuilder()
        article: Optional[dict[str, Any]] = None
        annex: Optional[ChildrenBuilder] = None
        division: Optional[dict[str, Any]] = None
        paragraph: list[str] = []
        closing: list[str] = []
        quoting = 0
        heading = False

        def flush_paragraph() -> None:
            if not paragraph:
                return
            text = join_lines(paragraph)
            paragraph.clear()
            target = annex if annex is not None else (article['children'] if article else None)
            if target is None:
                return
            match = _PARAGRAPH.match(text)
            if annex is None and target.children and not match and (_POINT.match(text) or text.startswith('«')):
                target.extend(text)
                current = target.children[-1]
                if current.get('amendment') is not None and '«' in text:
                    current['amendment']['quoted'].append({'kind': 'text', 'text': text.strip('«» ')})
                return
            child = target.add(text, number=match.group('num') if match and annex is None else None)
            instruction = text.split('«')[0]
            action = amendment_action(instruction) if annex is None else None
            if action:
                found = re.findall(r'«([^«»]{30,})»', text)
                if not found and '«' in text:
                    # A quotation that runs on beyond the document's end
                    found = [text.split('«', 1)[1]]
                quoted = [{'kind': 'text', 'text': q.strip(' »')} for q in found]
                child['amendment'] = {'action': action, 'instruction': instruction.strip(),
                                      'amended_act': _amended_act(instruction), 'quoted': quoted}

        def flush_article() -> None:
            nonlocal article
            flush_paragraph()
            if article is not None:
                body.article(article['num'], article['heading'], article['children'].children, token=article['token'])
            article = None

        for line in lines:
            text = line.text
            indent = line.x0 - line.left
            if quoting:
                # The next article in sequence ends a quotation left open by a misprint
                match = _ARTICLE.match(text)
                following = article and article['token'].isdigit() and match \
                    and match.group('num') == str(int(article['token']) + 1)
                if not following:
                    paragraph.append(text)
                    quoting = max(quoting + text.count('«') - text.count('»'), 0)
                    continue
                quoting = 0
            if closing:
                closing.append(text)
                continue
            if _CLOSING.match(text) and (article is not None or body.articles):
                flush_article()
                closing.append(text)
                continue
            if _ANNEX.match(text) and (article is not None or body.articles) and indent > 10:
                flush_article()
                annex = ChildrenBuilder()
                self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': text, 'heading': None,
                                     'children': annex.children})
                continue
            if annex is not None:
                if self.annexes[-1]['heading'] is None and not annex.children and not paragraph and indent > 10:
                    self.annexes[-1]['heading'] = text
                    continue
                if paragraph and indent > 4:
                    flush_paragraph()
                paragraph.append(text)
                continue
            match = _DIVISION.match(text)
            if match and indent > 10:
                flush_article()
                division = body.division(DIVISIONS[match.group('kind')], text, token=match.group('num').strip('΄'))
                continue
            match = _ARTICLE.match(text)
            if match and indent > 10:
                flush_article()
                number = match.group('num')
                article = {'num': text, 'heading': None, 'children': ChildrenBuilder(),
                           'token': ORDINALS.get(number, number).strip('΄')}
                heading = True
                division = None
                continue
            if division is not None and article is None:
                division['heading'] = f"{division['heading']} {text}" if division.get('heading') else text
                continue
            if article is None:
                continue
            # The article's heading is set in further than its paragraphs
            short = line.x1 < line.right - 15 and not text.endswith(('.', ':', '·', ';', ','))
            if heading and (indent > 11 or line.bold or (short and not article['heading'])) \
                    and not _PARAGRAPH.match(text) and not _POINT.match(text):
                article['heading'] = f"{article['heading']} {text}" if article['heading'] else text
                continue
            heading = False
            # Text quoted by an amendment opens a line after an instruction ending with a colon
            if text.startswith('«') and paragraph and paragraph[-1].rstrip().endswith(':'):
                paragraph.append(text)
                quoting = max(text.count('«') - text.count('»'), 0)
                continue
            # A paragraph starts on an indented line after the end of a sentence
            if paragraph and (indent > 4 or _PARAGRAPH.match(text)) and paragraph[-1].rstrip().endswith(
                    ('.', ':', '·', ';', '»', '».', '»·', '»:')):
                flush_paragraph()
            paragraph.append(text)
        flush_article()
        flush_paragraph()
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        if closing:
            split = next((i for i, text in enumerate(closing) if re.match(r'^Αθήνα, \d', text)), 1)
            self.conclusions = {'conclusion_text': join_lines(closing[:split]) or None,
                                'signature': ' '.join(closing[split:]) or None}
