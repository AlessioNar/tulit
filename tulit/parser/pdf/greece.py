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
  which carries a structured ``amendment``; so does a treaty or a code an
  article ratifies, with its own articles numbered from 1;
- pages of a treaty reproduced as signed, whose fonts carry no character
  codes, are left out;
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
# Latin capitals set by mistake in Greek words ('NOMOΣ', 'ΜΕΡΟΣ ΙII')
_LOOKALIKES = str.maketrans('ABEHIKMNOPTXYZ', 'ΑΒΕΗΙΚΜΝΟΡΤΧΥΖ')
_MIXED = re.compile(r'\S*[Α-Ωα-ωΆ-Ώά-ώ΄]\S*')
_HEADER = re.compile(r'(ΕΦΗΜΕΡΙ[ΔΣ]Α?Σ?\s+T?Τ?ΗΣ ΚΥΒΕΡΝΗΣΕΩΣ|Τεύχος [AΑΒΓΔ]΄?\s*\d+/\d{2}\.\d{2}\.\d{4})')
_MASTHEAD = re.compile(r'Αρ\. Φύλλου|ΤΕΥΧΟΣ (ΠΡΩΤΟ|ΔΕΥΤΕΡΟ|ΤΡΙΤΟ|ΤΕΤΑΡΤΟ)')
_BARCODE = re.compile(r'^\*\d{10,}\*$')
_BACK_COVER = re.compile(r'helpdesk\.et@et\.gr|grammateia@et\.gr')
_NUMBER = re.compile(r'^(?P<kind>ΝΟΜΟΣ|ΠΡΟΕΔΡΙΚΟ ΔΙΑΤΑΓΜΑ|ΠΡΑΞΗ ΝΟΜΟΘΕΤΙΚΟΥ ΠΕΡΙΕΧΟΜΕΝΟΥ)\s*'
                     r'(?:ΥΠ΄?\s*ΑΡΙΘΜ?\.?\s*(?P<num>\d+))?')

# Articles of acts of legislative content and ratifying laws are numbered in words ('Άρθρο εικοστό πρώτο')
_UNITS = ('πρώτο', 'δεύτερο', 'τρίτο', 'τέταρτο', 'πέμπτο', 'έκτο', 'έβδομο', 'όγδοο', 'ένατο')
_TENS = ('δέκατο', 'εικοστό', 'τριακοστό', 'τεσσαρακοστό', 'πεντηκοστό', 'εξηκοστό', 'εβδομηκοστό', 'ογδοηκοστό',
         'ενενηκοστό')
ORDINALS = {'μόνο': '1', 'ενδέκατο': '11', 'δωδέκατο': '12', 'εκατοστό': '100'}
ORDINALS.update({unit: str(n) for n, unit in enumerate(_UNITS, start=1)})
ORDINALS.update({ten: str(10 * n) for n, ten in enumerate(_TENS, start=1)})
ORDINALS.update({f'{ten} {unit}': str(10 * t + u) for t, ten in enumerate(_TENS, start=1)
                 for u, unit in enumerate(_UNITS, start=1)})
_ARTICLE = re.compile(r'^Άρθρο\s+(?P<num>\d+[Α-Ωα-ω]?|'
                      + '|'.join(sorted(ORDINALS, key=len, reverse=True)) + r'|[Α-Ω]+΄?)\s*$')
# A division's title sometimes runs on its number without a space ('ΚΕΦΑΛΑΙΟ Α΄ΕΝΣΩΜΑΤΩΣΗ ΟΔΗΓΙΑΣ')
_DIVISION = re.compile(r'^(?P<head>(?P<kind>ΜΕΡΟΣ|ΤΙΤΛΟΣ|ΚΕΦΑΛΑΙΟ|ΤΜΗΜΑ|ΥΠΟΚΕΦΑΛΑΙΟ)\s+'
                       r'(?P<num>[Α-Ω]{1,3}΄?|\d+|[IVXΙ]+))(?:\s*|(?<=΄)\s*(?P<title>[Α-Ω«(][^a-zα-ωά-ώ]*))$')
_PARAGRAPH = re.compile(r'^(?P<num>\d+[α-ω]?)\.\s+\S')
_POINT = re.compile(r'^(\(?[α-ω]{1,3}[΄\']?\)|\(?[ivx]+\)|-|–|•)\s')
_FORMULA = re.compile(r'(Εκδίδομε τον ακόλουθο νόμο που ψήφισε η Βουλή:?|αποφασίζουμε:?|'
                      r'Εκδίδομε την ακόλουθη πράξη νομοθετικού περιεχομένου:?)\s*$', re.IGNORECASE)
_CLOSING = re.compile(r'^(Παραγγέλλ?ομε τη δημοσίευση|Αθήνα, \d|Στον .* αναθέτουμε τη δημοσίευση)')
_TOC = re.compile(r'^(ΠΙΝΑΚΑΣ ΠΕΡΙΕΧΟΜΕΝΩΝ|Πίνακας Περιεχομένων)$')
_ANNEX = re.compile(r'^ΠΑΡΑΡΤΗΜΑ(\s+[Α-ΩIVX\d]+΄?)?$')
DIVISIONS = {'ΜΕΡΟΣ': 'part', 'ΤΙΤΛΟΣ': 'title', 'ΚΕΦΑΛΑΙΟ': 'chapter', 'ΤΜΗΜΑ': 'section',
             'ΥΠΟΚΕΦΑΛΑΙΟ': 'subsection'}

# Amending phrases, checked in order
ACTIONS = (
    (r'καταργείται|καταργούνται|διαγράφεται|διαγράφονται|απαλείφεται|απαλείφονται', 'delete'),
    (r'αντικαθίσταται|αντικαθίστανται', 'replace'),
    (r'προστίθεται|προστίθενται|συμπληρώνεται|συμπληρώνονται', 'add'),
    (r'τροποποιείται|τροποποιούνται', 'amend'),
)


# What an amending instruction names: an act ('ν. 4624/2019', 'Π.δ. 169/2007', 'Κ.Φ.Ε.'), or the list of
# provisions repealed that follows its colon
_REFERENCE = re.compile(r'\b(?:ν|π\.\s?δ|ν\.\s?δ|α\.\s?ν|β\.\s?δ|ν\.\s?π\.\s?δ)\.\s*\d|\bνόμου\s+\d|Κώδικα|'
                        r'Πράξης Νομοθετικού Περιεχομένου|Π\.Ν\.Π\.|απόφασης|κ\.υ\.α\.|\b[Α-Ω]\.[Α-Ω]\.[Α-Ω]\.|'
                        r'\(\s*[ΑΒΔ]΄\s*\d|:\s*$', re.IGNORECASE)


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


def _open_division(body: BodyBuilder, match: re.Match) -> dict[str, Any]:
    """Open the division a heading line matched by _DIVISION starts, with the title run on to it if any."""
    return body.division(DIVISIONS[match.group('kind')], match.group('head'), heading=match.group('title'),
                         token=match.group('num').strip('΄'))


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
    chars = sorted(chars, key=lambda c: c['x0'])
    # Words are set apart by 1.5pt or more, or by less in tightly set lines (titles, names in the signatures):
    # 1pt more than the usual gap between the letters of the line
    gaps = sorted(b['x0'] - a['x1'] for a, b in zip(chars, chars[1:]) if a['text'] != ' ' and b['text'] != ' ')
    limit = min(1.5, gaps[len(gaps) // 2] + 1.0) if gaps else 1.5
    parts: list[str] = []
    previous = None
    for char in chars:
        if previous is not None and char['x0'] - previous['x1'] > limit and char['text'] != ' ':
            parts.append(' ')
        parts.append(char['text'])
        previous = char
    text = ' '.join(''.join(parts).split()).translate(_GREEK)
    return _MIXED.sub(lambda word: word.group(0).translate(_LOOKALIKES), text)


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
            if sum(1 for c in page.chars if c['text'].startswith('(cid:') or '\u00c0' <= c['text'] <= '\u02ff'
                   or '\u0400' <= c['text'] <= '\u05ff') > len(page.chars) / 10:
                # A facsimile (a treaty as signed) in fonts without their characters' codes, or the back cover of older
                # issues in a font read as Latin-1: the text is garbled
                continue
            body = [line for line in found if line['top'] > header_bottom + 1
                    and Counter(round(c['size'], 1) for c in line['chars']).most_common(1)[0][0] >= 8.5]
            # Pages set in one column (the signatures, some annexes) are read across
            crosses = [_crosses(line['chars'], gutter) for line in body]
            # Judged on the text above the order to publish: the signatures below it are set in columns of their own
            closing = next((i for i, line in enumerate(body) if _CLOSING.match(_text(line['chars']))), len(body))
            judged = crosses[:closing] or crosses
            single = bool(judged) and sum(judged) > len(judged) * 0.25
            # So are the lines of a paragraph set across a page whose signatures are set in columns: the lines
            # crossing the gutter, and those between two of them
            across = [any(crosses[max(0, i - 2):i + 1]) and any(crosses[i:i + 3]) for i in range(len(body))]
            columns: list[list[_Line]] = [[], []]
            for i, line in enumerate(body):
                chars = [c for c in line['chars'] if c['text'].strip()]
                if not chars:
                    continue
                size = Counter(round(c['size'], 1) for c in chars).most_common(1)[0][0]
                bold = 'Bold' in Counter(c['fontname'] for c in chars).most_common(1)[0][0]
                for column in (0, 1):
                    if single or across[i]:
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
                division = next((k for k in range(end - 1, max(toc, end - 8), -1) if _DIVISION.match(lines[k].text)),
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
        # The last article heading met while quoting, in a quoted text (a treaty) numbering its own articles
        quoted: Optional[int] = None
        heading = heading_bold = False
        # Within the text an article numbered in words holds (a code, a treaty): its lines are that article's text
        embedded = set_in = False

        def flush_paragraph() -> None:
            if not paragraph:
                return
            text = join_lines(paragraph)
            paragraph.clear()
            target = annex if annex is not None else (article['children'] if article else None)
            if target is None:
                return
            if embedded:
                target.add(text)
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
            # An amendment changes another act, which its instruction names
            if action and _REFERENCE.search(instruction):
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

        def next_article(start: int) -> Optional[re.Match]:
            """The next article heading from line ``start`` on."""
            return next((match for line in lines[start:] if line.x0 - line.left > 10
                         for match in [_ARTICLE.match(line.text)] if match), None)

        for index, line in enumerate(lines):
            text = line.text
            indent = line.x0 - line.left
            if quoting:
                # The next article in sequence ends a quotation left open by a misprint, unless it is the next
                # article of a quoted text that numbers its own from 1, as a treaty does
                match = _ARTICLE.match(text)
                token = ORDINALS.get(match.group('num'), match.group('num')) if match else None
                following = article and article['token'].isdigit() and token == str(int(article['token']) + 1) \
                    and not (quoted and token == str(quoted + 1))
                if not following:
                    if token and token.isdigit() and (quoted or token == '1'):
                        quoted = int(token)
                    paragraph.append(text)
                    quoting = max(quoting + text.count('«') - text.count('»'), 0)
                    continue
                quoting, quoted = 0, None
                # The division opening the next article, quoted along with the rest
                start = next((k for k in range(len(paragraph) - 1, max(len(paragraph) - 6, -1), -1)
                              if _DIVISION.match(paragraph[k])), None)
                if start is not None and all(t == t.upper() for t in paragraph[start + 1:]):
                    titles = paragraph[start:]
                    del paragraph[start:]
                    flush_article()
                    division = _open_division(body, _DIVISION.match(titles[0]))
                    for title in titles[1:]:
                        division['heading'] = f"{division['heading']} {title}" if division['heading'] else title
            if closing:
                closing.append(text)
                continue
            if _CLOSING.match(text) and (article is not None or body.articles):
                flush_article()
                closing.append(text)
                continue
            # An article numbered in words that holds a text numbering its articles in figures (a code, a treaty),
            # from the first of them or the divisions above it
            match = _ARTICLE.match(text)
            numbered = match is not None and indent > 10 and match.group('num')[0].isdigit()
            # An article heading is set in, but for the next article on a page set across with no margin to go by
            next_in_turn = match is not None and article is not None and article['token'].isdigit() \
                and ORDINALS.get(match.group('num'), match.group('num')) == str(int(article['token']) + 1)
            heads = match is not None and (indent > 10 or next_in_turn)
            if article is not None and article['words'] and not embedded and indent > 10 and (
                    numbered or (_DIVISION.match(text) and (following := next_article(index + 1)) is not None
                                 and following.group('num')[0].isdigit())):
                flush_paragraph()
                embedded = True
            if embedded and not (heads and not match.group('num')[0].isdigit()):
                # Its headings (set in further) make a paragraph of their own
                if paragraph and ((indent > 10) != set_in or indent > 4 and paragraph[-1].rstrip().endswith(
                        ('.', ':', '·', ';', '»'))):
                    flush_paragraph()
                paragraph.append(text)
                set_in = indent > 10
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
                division = _open_division(body, match)
                continue
            match = _ARTICLE.match(text)
            if heads:
                flush_article()
                embedded = False
                number = match.group('num')
                article = {'num': text, 'heading': None, 'children': ChildrenBuilder(),
                           'token': ORDINALS.get(number, number).strip('΄'), 'words': not number[0].isdigit()}
                heading = True
                heading_bold = line.bold
                division = None
                continue
            if division is not None and article is None:
                division['heading'] = f"{division['heading']} {text}" if division.get('heading') else text
                continue
            if article is None:
                continue
            # The article's heading is set in further than its paragraphs
            short = line.x1 < line.right - 15 and not text.endswith(('.', ':', '·', ';', ','))
            # Where an article's number and heading are set in bold, its text starts at the first line in roman,
            # though set in as far (an article set in the middle of a page of its own)
            roman = article['heading'] and heading_bold and not line.bold
            # A centred heading stops short of the right edge; the first line of a paragraph runs to it, set in as
            # far as a heading where the text is set across the page (2026)
            full = line.x1 > line.right - 3 and indent < 20 and not line.bold
            if heading and (indent > 11 or line.bold or (short and not article['heading'])) and not roman and not full \
                    and not _PARAGRAPH.match(text) and not _POINT.match(text):
                article['heading'] = f"{article['heading']} {text}" if article['heading'] else text
                heading_bold = heading_bold and line.bold
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
