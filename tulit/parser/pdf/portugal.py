"""
Parser for Portuguese acts in the PDF of the Diário da República.

The Diário da República publishes each act as a PDF extract of the issue,
with page headers ('Diário da República, 1.ª série', 'N.º 151 ... Pág. 3')
and a footer ('www.dre.pt'):

- the act designation and date ('Lei n.º 58/2019', 'de 8 de agosto') give
  the preface; the summary and long title, and the preamble of a
  decree-law, give the recitals; the enacting clause ('A Assembleia da
  República decreta ... o seguinte:') the formula;
- TÍTULO, CAPÍTULO, SECÇÃO and SUBSECÇÃO headings become divisions;
- each 'Artigo N.º' becomes an article, the centred line below it its
  heading; numbered paragraphs ('1 — ...') become par_N, with points
  ('a) ...') folded into them; a new paragraph starts on an indented line;
- text quoted by an amendment («...») stays inside the amending article,
  and the amending paragraph carries a structured ``amendment``;
- approval, promulgation and signatures become the conclusions, and the
  annexes (ANEXO, MAPA) the annexes.

Needs the ``pdf`` extra.
"""
import re
from collections import Counter
from typing import Any, Optional

from tulit.parser.parser import Parser
from tulit.parser.pdf.layout import Line, frames, join_lines, read_lines
from tulit.parser.structure import BodyBuilder, ChildrenBuilder

_HEADER = re.compile(r'^(Diário da República, \d\.ª série|N\.º \d+.*Pág\. \d+|www\.dre\.pt|\d{6,})$|'
                     r'DIÁRIO DA REPÚBLICA|^SÉRIE-[AB]\b|^N\.[oº] \d+ — \d+ de \w+ de \d{4}|^\d+ DIÁRIO|'
                     r'DA REPÚBLICA — I+ SÉRIE')
_DESIGNATION = re.compile(r'^(Lei|Lei Orgânica|Lei Constitucional|Decreto-Lei|Decreto Legislativo Regional|'
                          r'Decreto Regulamentar|Decreto|Portaria|Resolução|Despacho|Declaração de Retificação)'
                          r'(?: n\.[ºo] [\w\-/]+)?$')
_DATE = re.compile(r'^de \d{1,2} de \w+$', re.IGNORECASE)
_ARTICLE = re.compile(r'^«?Artigo (?P<num>\d+\.[ºo](?:-[A-Z])?|único)$')
_DIVISION = re.compile(r'^(?P<kind>TÍTULO|CAPÍTULO|SECÇÃO|SUBSECÇÃO|PARTE|LIVRO)\s+(?P<num>[IVXLC]+|[ÚU]NIC[OA])$')
_PARAGRAPH = re.compile(r'^(?P<num>\d+(?:-[A-Z])?) — ')
_POINT = re.compile(r'^([a-z]{1,2}|[ivxl]+)\) ')
_CLOSING = re.compile(r'^(Aprovad[oa] em|Promulgad[oa] em|Referendad[oa] em|Visto e aprovado|Publique-se\.?$)')
_ANNEX = re.compile(r'^(ANEXO|MAPA)(\s+[IVXLC\d]+)?$')
DIVISIONS = {'LIVRO': 'part', 'PARTE': 'part', 'TÍTULO': 'title', 'CAPÍTULO': 'chapter',
             'SECÇÃO': 'section', 'SUBSECÇÃO': 'subsection'}

# Amending phrases, checked in order
ACTIONS = (
    ('é revogad', 'delete'), ('são revogad', 'delete'), ('passa a ter a seguinte redação', 'replace'),
    ('passam a ter a seguinte redação', 'replace'), ('é aditad', 'add'), ('são aditad', 'add'),
    ('é substituíd', 'replace'), ('é alterad', 'amend'), ('são alterad', 'amend'),
)


def amendment_action(text: str) -> Optional[str]:
    """'O artigo 5.º ... passa a ter a seguinte redação:' -> 'replace'; '... é revogado' -> 'delete'."""
    lowered = text.lower()
    for phrase, action in ACTIONS:
        if phrase in lowered:
            return action
    return None


class DiarioRepublicaParser(Parser):
    """Parses a Portuguese act (Diário da República PDF) into legalJSON."""

    def __init__(self, number: Optional[str] = None) -> None:
        """``number``: the act's number ('7/2004'), to find it in an extract holding several acts."""
        super().__init__()
        self.number = number

    def parse(self, file: str, **options) -> 'DiarioRepublicaParser':
        lines, _, width = read_lines(file)
        lines = [line for line in lines if not _HEADER.search(line.text)]
        lines = self._own_lines(lines)
        self.width = width
        self.frames = frames(lines)
        start = self._read_front(lines)
        self._read_body(lines[start:])
        return self

    def _own_lines(self, lines: list[Line]) -> list[Line]:
        """The lines of the act itself, when the extract also holds the end or start of other acts."""
        designations = [i for i, line in enumerate(lines) if _DESIGNATION.match(line.text)]
        if not designations:
            return lines
        start = designations[0]
        if self.number:
            start = next((i for i in designations if lines[i].text.endswith(f' {self.number}')), start)
        following = [i for i in designations if i > start]
        end = following[0] if following else len(lines)
        # The issuing body of the next act ('MINISTÉRIO DA ECONOMIA') precedes its designation
        while end > start + 1 and end < len(lines) and lines[end - 1].text.isupper() and lines[end - 1].bold:
            end -= 1
        return lines[start:end]

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _centred(self, line: Line, tolerance: float = 20.0) -> bool:
        """Whether a line is centred in its column and set in from its margin."""
        left, right = self.frames.get((line.page, line.column), (0.0, self.width))
        return (line.x0 > left + 15 and line.x1 < right - 5
                and abs((line.x0 + line.x1) / 2 - (left + right) / 2) <= tolerance)

    def _new_paragraph(self, line: Line, previous: Optional[str] = None) -> bool:
        """An indented line after the end of a sentence starts a paragraph (a deeper hanging indent does not)."""
        left, _ = self.frames.get((line.page, line.column), (0.0, self.width))
        if previous is not None and not previous.rstrip().endswith(('.', ';', ':', '»', '»;', '».')):
            return False
        return line.x0 > left + 8 and not self._centred(line, 8)

    def _read_front(self, lines: list[Line]) -> int:
        """Designation, date, summary, long title, preamble and enacting clause; returns where the body starts."""
        first = next((i for i, line in enumerate(lines) if _ARTICLE.match(line.text) or _DIVISION.match(line.text)),
                     len(lines))
        designation = 0 if lines and _DESIGNATION.match(lines[0].text) else None
        start = 0
        if designation is not None:
            title = [lines[designation].text]
            if designation + 1 < first and _DATE.match(lines[designation + 1].text):
                title.append(lines[designation + 1].text)
            self.preface = ' '.join(title)
            start = designation + len(title)
        paragraphs: list[list[str]] = []
        style = None
        body_size = Counter(line.size for line in lines).most_common(1)[0][0] if lines else 0
        for line in lines[start:first]:
            # The summary, the long title and the preamble differ in size and weight
            new_style = (line.size, line.bold)
            indented = line.size == body_size and not line.bold and self._new_paragraph(line)
            if not paragraphs or new_style != style or indented:
                paragraphs.append([line.text])
            else:
                paragraphs[-1].append(line.text)
            style = new_style
        texts = [join_lines(paragraph) for paragraph in paragraphs]
        enacting = next((i for i in range(len(texts) - 1, -1, -1)
                         if re.search(r'\b(decreta|aprova|determina|manda)\b.*o seguinte:?$', texts[i])), None)
        if enacting is not None:
            self.formula = texts[enacting]
            texts = texts[:enacting]
        self.recitals = [{'eId': f'rct_{n}', 'text': text} for n, text in enumerate(texts, start=1) if text]
        return first

    def _read_body(self, lines: list[Line]) -> None:
        body = BodyBuilder()
        article: Optional[dict[str, Any]] = None
        paragraph: list[str] = []
        division: Optional[dict[str, Any]] = None
        closing: list[str] = []
        annex: Optional[dict[str, Any]] = None
        quoting = 0
        expect_heading = False

        def flush_paragraph() -> None:
            if not paragraph:
                return
            text = join_lines(paragraph)
            paragraph.clear()
            target = annex['children'] if annex is not None else (article['children'] if article else None)
            if target is None:
                return
            if annex is None and quoting_paragraph['inside']:
                current = target.children[-1] if target.children else None
                if current is not None and current.get('amendment') is not None:
                    current['amendment']['quoted'].append({'kind': 'text', 'text': text.strip('«»')})
                target.extend(text)
                return
            if _POINT.match(text) and target.children:
                # Points (alíneas) belong to the paragraph above
                target.extend(text)
                return
            match = _PARAGRAPH.match(text)
            child = target.add(text, number=match.group('num') if match else None)
            action = amendment_action(text) if annex is None else None
            if action:
                child['amendment'] = {'action': action, 'instruction': text, 'amended_act': None, 'quoted': []}

        quoting_paragraph = {'inside': False}

        def flush_article() -> None:
            nonlocal article
            flush_paragraph()
            if article is not None:
                body.article(article['num'], article['heading'], article['children'].children,
                             token=article['token'])
            article = None

        previous: Optional[str] = None
        for line in lines:
            text = line.text
            last, previous = previous, text
            if quoting:
                flush_needed = self._new_paragraph(line, last) or _ARTICLE.match(text.lstrip('«'))
                if flush_needed:
                    flush_paragraph()
                quoting_paragraph['inside'] = True
                paragraph.append(text)
                quoting += text.count('«') - text.count('»')
                if quoting <= 0:
                    quoting = 0
                    flush_paragraph()
                    quoting_paragraph['inside'] = False
                continue
            if text.startswith('«') and article is not None and annex is None:
                # Text quoted by an amendment, possibly over several lines
                flush_paragraph()
                quoting = max(text.count('«') - text.count('»'), 0)
                quoting_paragraph['inside'] = True
                paragraph.append(text)
                if not quoting:
                    flush_paragraph()
                    quoting_paragraph['inside'] = False
                continue
            if annex is None and (closing or (_CLOSING.match(text) and article is not None)):
                if not _ANNEX.match(text):
                    closing.append(text)
                    continue
            if _ANNEX.match(text) and (article is not None or closing):
                flush_article()
                annex = {'num': text, 'heading': None, 'children': ChildrenBuilder()}
                self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': text, 'heading': None,
                                     'children': annex['children'].children})
                continue
            if annex is not None:
                if self.annexes[-1]['heading'] is None and self._centred(line) and not annex['children'].children:
                    self.annexes[-1]['heading'] = text
                    continue
                if self._new_paragraph(line, last) or self._centred(line):
                    flush_paragraph()
                paragraph.append(text)
                continue
            match = _DIVISION.match(text)
            if match:
                flush_article()
                division = body.division(DIVISIONS[match.group('kind')], text, token=match.group('num'))
                continue
            match = _ARTICLE.match(text)
            if match:
                flush_article()
                number = match.group('num')
                article = {'num': text, 'heading': None, 'children': ChildrenBuilder(),
                           'token': '1' if number == 'único' else re.sub(r'\.[ºo]', '', number)}
                expect_heading = True
                division = None
                continue
            if division is not None and article is None and (self._centred(line) or line.bold):
                division['heading'] = f"{division['heading']} {text}" if division.get('heading') else text
                continue
            if article is None:
                continue
            if expect_heading and self._centred(line) and not _PARAGRAPH.match(text):
                article['heading'] = f"{article['heading']} {text}" if article['heading'] else text
                continue
            expect_heading = False
            if self._new_paragraph(line, last) or _PARAGRAPH.match(text):
                flush_paragraph()
            paragraph.append(text)
        flush_article()
        flush_paragraph()
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        if closing:
            self.conclusions = {'conclusion_text': ' '.join(closing[:-1]) or None, 'signature': closing[-1]}
