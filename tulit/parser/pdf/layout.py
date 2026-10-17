"""
Text lines of a PDF with their position and font size, for the PDF parsers.

Reading PDFs needs the optional ``pdf`` extra (``pip install tulit[pdf]``),
which installs pdfplumber.
"""
import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Optional

from tulit.parser.exceptions import FileLoadError


@dataclass
class Line:
    """One line of text on a page."""
    page: int
    text: str
    x0: float
    x1: float
    top: float
    size: float
    bold: bool = False
    width: float = 0.0
    """Width of the text frame: the page, or the column on pages set in two columns."""
    column: int = 0
    """0 for the page or its left column, 1 for the right column."""


def _pdfplumber():
    try:
        import pdfplumber
    except ImportError as e:
        raise ImportError("Reading PDF documents needs the 'pdf' extra: pip install 'tulit[pdf]'") from e
    return pdfplumber


def _lines(page, number: int) -> list[Line]:
    lines = []
    # A tight character tolerance keeps the spaces of narrowly set text
    for found in page.extract_text_lines(return_chars=True, x_tolerance=1.5):
        text = ' '.join(found['text'].split())
        if not text:
            continue
        chars = found.get('chars') or [{}]
        sizes = Counter(round(c.get('size', 0), 1) for c in chars)
        fonts = Counter(c.get('fontname', '') for c in chars)
        lines.append(Line(page=number, text=text, x0=found['x0'], x1=found['x1'], top=found['top'],
                          size=sizes.most_common(1)[0][0], bold='Bold' in fonts.most_common(1)[0][0],
                          width=float(page.width)))
    return lines


def _column(lines: list[Line]) -> tuple[float, float]:
    """Left and right edges of the body text: edges shared by several lines (headers and odd lines aside)."""
    lefts = Counter(round(line.x0) for line in lines)
    rights = Counter(round(line.x1) for line in lines)
    shared_left = [x for x, count in lefts.items() if count >= 3]
    shared_right = [x for x, count in rights.items() if count >= 3]
    return (float(min(shared_left)) if shared_left else min(line.x0 for line in lines),
            float(max(shared_right)) if shared_right else max(line.x1 for line in lines))


def _two_columns(page, width: float) -> bool:
    """Whether a page is set in two columns: next to no characters in the gutter down its middle."""
    chars = [c for c in page.chars if c.get('text', '').strip()]
    if len(chars) < 500:
        return False
    middle = width / 2
    in_gutter = sum(1 for c in chars if c['x0'] < middle + 3 and c['x1'] > middle - 3)
    return in_gutter < len(chars) * 0.003


def _page_lines(page, number: int, width: float) -> list[Line]:
    if not _two_columns(page, width):
        return _lines(page, number)
    left = _lines(page.crop((0, 0, width / 2, page.height)), number)
    right = _lines(page.crop((width / 2, 0, width, page.height)), number)
    # Positions are kept relative to the column
    for line in left:
        line.width = width / 2
    for line in right:
        line.x0, line.x1, line.width, line.column = line.x0 - width / 2, line.x1 - width / 2, width / 2, 1
    return left + right


def read_lines(path: str, notes: bool = False) -> tuple[list[Line], list[Line], float]:
    """
    The lines of a PDF, page by page; pages in two columns are read column by column.

    With ``notes``, characters noticeably smaller than the body text (side
    notes in the margin) are read apart from it. Returns (body lines, note
    lines, page width).
    """
    pdfplumber = _pdfplumber()
    try:
        pdf = pdfplumber.open(path)
    except Exception as e:  # pdfplumber raises several unrelated types for unreadable files
        raise FileLoadError(f"Cannot read PDF {path}: {e}") from e
    with pdf:
        width = float(pdf.pages[0].width) if pdf.pages else 0.0
        if not notes:
            return [line for n, page in enumerate(pdf.pages) for line in _page_lines(page, n, width)], [], width
        sizes = Counter(round(c['size'], 1) for page in pdf.pages for c in page.chars)
        if not sizes:
            return [], [], width
        body_size = sizes.most_common(1)[0][0]
        threshold = body_size * 0.9
        body, side = [], []
        for n, page in enumerate(pdf.pages):
            large = _lines(page.filter(lambda o: o.get('object_type') != 'char' or o['size'] >= threshold), n)
            small = _lines(page.filter(lambda o: o.get('object_type') != 'char' or o['size'] < threshold), n)
            if len(large) < 5:
                # A page set in the small size (e.g. a schedule) holds no side notes
                body.extend(sorted(large + small, key=lambda line: (line.top, line.x0)))
                continue
            # Small text inside the body column (e.g. a schedule) is body text; beside it, a side note
            left, right = _column(large)
            notes_here = [line for line in small if line.x1 <= left + 2 or line.x0 >= right - 2]
            body.extend(sorted(large + [line for line in small if line not in notes_here],
                               key=lambda line: (line.top, line.x0)))
            side.extend(notes_here)
        return body, side, width


_BROKEN_WORD = re.compile(r'[^\W\d_]-$')


def join_lines(texts: Iterable[str]) -> str:
    """
    Join wrapped lines into one paragraph.

    A word broken at the line end ('na-' + 'cional') is mended; a hyphen
    after a space ('aplica -' + 'se') is kept and joined without a space.
    """
    joined = ''
    for text in texts:
        text = text.strip()
        if not text:
            continue
        if not joined:
            joined = text
        elif _BROKEN_WORD.search(joined) and text[:1].islower():
            joined = joined[:-1] + text
        elif joined.endswith(' -') or joined.endswith('-') and text[:1].islower():
            joined = joined + text
        else:
            joined = f'{joined} {text}'
    return joined


def centred(line: Line, width: float, tolerance: float = 20.0, margin: float = 0.0) -> bool:
    """Whether a line is centred in its frame (and, given the body margin, set in from it)."""
    if margin and line.x0 < margin + 15:
        return False
    frame = line.width or width
    return abs((line.x0 + line.x1) / 2 - frame / 2) <= tolerance


def body_margin(lines: list[Line], page: Optional[int] = None) -> float:
    """The most common left edge of the lines (of one page), i.e. the body text margin."""
    edges = Counter(round(line.x0) for line in lines if page is None or line.page == page)
    return float(edges.most_common(1)[0][0]) if edges else 0.0


def frames(lines: list[Line]) -> dict[tuple[int, int], tuple[float, float]]:
    """Left and right edges of the body text in each page column, from edges shared by several lines."""
    grouped: dict[tuple[int, int], list[Line]] = {}
    for line in lines:
        grouped.setdefault((line.page, line.column), []).append(line)
    result = {}
    for key, group in grouped.items():
        lefts = Counter(round(line.x0) for line in group)
        rights = Counter(round(line.x1) for line in group)
        left = lefts.most_common(1)[0][0]
        shared = [x for x, count in rights.items() if count >= 2]
        result[key] = (float(left), float(max(shared) if shared else max(line.x1 for line in group)))
    return result
