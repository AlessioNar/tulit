"""
Parser for Maltese legislation in the PDF of legislation.mt.

Legislation Malta publishes consolidated laws (Chapters, 'CAP. 586') and
Acts as passed as PDF. Both print the heading of each article as a side
note in the margin, in a smaller font, on alternate sides of the page:

- the title ('DATA PROTECTION ACT', 'ACT No. XII of 2018') gives the
  preface, the long title ('AN ACT to ...') the recitals and the enacting
  clause ('BE IT ENACTED ...') the formula; the arrangement of the Act (its
  table of contents) is left out;
- PART and TITLE headings become divisions, with the line below as heading;
- each article ('3. (1) In this Act ...') becomes an article whose heading
  is its side note; sub-articles '(1)' become par_N, with paragraphs '(a)'
  and provisos folded in; amendment notes in the margin ('Amended by: ...')
  are left out;
- schedules become annexes.

Needs the ``pdf`` extra.
"""
import re
from typing import Any, Optional

from tulit.parser.parser import Parser
from tulit.parser.pdf.layout import Line, join_lines, read_lines
from tulit.parser.structure import BodyBuilder, ChildrenBuilder

_HEADER = re.compile(r'(\[(CAP|KAP)\.\s*\d+|^VERŻJONI ELETTRONIKA$|^A\s?\d+$|^B\s?\d+$|^\d+$)')
# The full stop is sometimes missing before a first sub-article ('27 (1) ...')
_ARTICLE = re.compile(r'^(?P<num>\d+[A-Z]*)(?:\.\s+|\s+(?=\(1\)\s))(?P<rest>\S.*)$')
_SUBARTICLE = re.compile(r'^\((?P<num>\d+[A-Za-z]*)\)\s')
_DIVISION = re.compile(r'^(?P<kind>PART|SUB-PART|TITLE|SUB-TITLE|TAQSIMA|SUB-TAQSIMA|TITOLU)\s+'
                       r'(?P<num>[IVXLC]+[A-Z]?|\d+)$')
_SCHEDULE = re.compile(r'^(?:[A-Z\-]+\s+)?(SCHEDULE|SKEDA)(?:\s+[IVXLC\d]+)?$')
_NOTE_SKIP = re.compile(r'^(Amended by|Added by|Substituted by|Renumbered by|Deleted by|Cap\.|L\.N\.|'
                        r'Act [IVXLC]+|[IVXLC]+\.\s*\d{4}|\d{4}\.\d+)')
DIVISIONS = {'PART': 'part', 'SUB-PART': 'title', 'TITLE': 'title', 'SUB-TITLE': 'chapter',
             'TAQSIMA': 'part', 'SUB-TAQSIMA': 'title', 'TITOLU': 'title'}


class MaltaPDFParser(Parser):
    """Parses a Maltese Chapter or Act (legislation.mt PDF) into legalJSON."""

    def parse(self, file: str, **options) -> 'MaltaPDFParser':
        body, notes, _ = read_lines(file, notes=True)
        self.notes = [note for note in notes if not _HEADER.search(note.text)]
        lines = [line for line in body if not _HEADER.search(line.text)]
        start = self._read_front(lines)
        self._read_body(lines[start:])
        return self

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _read_front(self, lines: list[Line]) -> int:
        """Title, long title and enacting clause; returns where the body starts."""
        arrangement = next((i for i, line in enumerate(lines)
                            if line.text.upper() in ('ARRANGEMENT OF THE ACT', 'TAQSIM TAL-ATT')), None)
        first_page = lines[arrangement].page + 1 if arrangement is not None else 0
        start = next((i for i, line in enumerate(lines)
                      if line.page >= first_page and (_DIVISION.match(line.text)
                                                       or re.match(r'^1\.\s+\S', line.text))), len(lines))
        front = lines[:arrangement if arrangement is not None else start]
        texts = [line.text for line in front]
        chapter = next((i for i, text in enumerate(texts) if re.match(r'^(CHAPTER|KAPITOLU)\s+\d+', text)), None)
        act = next((i for i, text in enumerate(texts) if re.match(r'^(ACT\s+No\.|ATT\s+Nru)', text)), None)
        long_title = next((i for i, text in enumerate(texts) if re.match(r'^(AN ACT|ATT biex)\b', text)), None)
        enacting = next((i for i, text in enumerate(texts) if text.startswith(('BE IT ENACTED', 'IKUN MAGĦMUL'))), None)
        if chapter is not None:
            # The title, in capitals, may run over several lines
            title = []
            for text in texts[chapter + 1:long_title]:
                if not text.isupper():
                    break
                title.append(text)
            self.preface = ' '.join(title) or None
        elif act is not None:
            self.preface = texts[act]
        if long_title is not None:
            end = next((i for i in range(long_title + 1, len(texts))
                        if texts[i].endswith('.') is False and re.match(r'^\d|^ACT|^BE IT', texts[i])),
                       enacting if enacting is not None else len(texts))
            title = []
            for text in texts[long_title:end]:
                title.append(text)
                if text.endswith('.'):
                    break
            self.recitals = [{'eId': 'rct_1', 'text': join_lines(title)}]
        if enacting is not None:
            self.formula = join_lines(texts[enacting:])
        return start

    def _heading(self, line: Line) -> Optional[str]:
        """The side note beside an article's first line."""
        block: list[str] = []
        last_top = None
        for note in self.notes:
            if note.page != line.page or note.top < line.top - 4:
                continue
            if last_top is None and note.top > line.top + 6:
                break
            if last_top is not None and note.top - last_top > 14:
                break
            if _NOTE_SKIP.match(note.text):
                break
            block.append(note.text)
            last_top = note.top
        return join_lines(block) or None

    def _read_body(self, lines: list[Line]) -> None:
        body = BodyBuilder()
        article: Optional[dict[str, Any]] = None
        annex: Optional[ChildrenBuilder] = None
        division: Optional[dict[str, Any]] = None
        paragraph: list[str] = []

        def flush_paragraph() -> None:
            if not paragraph:
                return
            text = join_lines(paragraph)
            paragraph.clear()
            target = annex if annex is not None else (article['children'] if article else None)
            if target is None:
                return
            match = _SUBARTICLE.match(text)
            if match:
                target.add(text, number=match.group('num'))
            elif target.children and annex is None:
                target.extend(text)
            else:
                target.add(text)

        def flush_article() -> None:
            nonlocal article
            flush_paragraph()
            if article is not None:
                body.article(article['num'], article['heading'], article['children'].children,
                             token=article['token'])
            article = None

        for line in lines:
            text = line.text
            if _SCHEDULE.match(text):
                flush_article()
                annex = ChildrenBuilder()
                self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': text, 'heading': None,
                                     'children': annex.children})
                continue
            if annex is not None:
                if _SUBARTICLE.match(text) or text[:1].isupper() and paragraph and paragraph[-1].endswith(('.', ':')):
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
                article = {'num': f"{match.group('num')}.", 'heading': self._heading(line),
                           'token': match.group('num'), 'children': ChildrenBuilder()}
                division = None
                paragraph.append(match.group('rest'))
                continue
            if division is not None and article is None:
                division['heading'] = f"{division['heading']} {text}" if division.get('heading') else text
                continue
            if article is None:
                continue
            if _SUBARTICLE.match(text):
                flush_paragraph()
            paragraph.append(text)
        flush_article()
        flush_paragraph()
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
