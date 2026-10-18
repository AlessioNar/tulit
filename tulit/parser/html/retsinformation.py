"""
Parser for older Danish acts in the HTML of Retsinformation.

Retsinformation publishes acts as LexDania XML, but for older acts (e.g. the
Constitution of 1953 or the Public Administration Act of 1985) the XML holds
only metadata; their text is the HTML the site's document service returns,
whose elements carry classes:

- ``TITLE`` gives the title (preface) and ``SUB-TITLE`` the royal formula;
- a ``KTITLE1`` heading ('Kapitel I.', 'Afsnit II') opens a chapter or part,
  whose heading is the following ``KTITLE2`` line;
- each ``PARAGRAPH`` block is an article: its first line (``PARAB``) starts
  with the number ('§ 1.') and is stk. 1, its ``STK`` lines ('Stk. 2.') are
  par_2, par_3, ..., with lists folded into the subsection before them;
- the place and date and the signature (``GIVET``) become the conclusions.
"""
import re
from typing import Any, Optional

from lxml import etree, html

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder, eid_token

_ARTICLE = re.compile(r'^(§\s*\d+\s*[a-z]?)\.?\s*(.*)$')
_SUBSECTION = re.compile(r'^Stk\.\s*(\d+[a-z]?)\.')


def _classes(element: etree._Element) -> set[str]:
    return set((element.get('class') or '').upper().split())


def _text(element: etree._Element) -> str:
    return ' '.join(' '.join(element.itertext()).replace('\xa0', ' ').split())


class RetsinformationHTMLParser(Parser):
    """Parses the HTML of an older act from Retsinformation into legalJSON."""

    def parse(self, file: str, **options) -> 'RetsinformationHTMLParser':
        try:
            with open(file, encoding='utf-8') as f:
                root = html.fromstring(f.read())
        except (OSError, etree.ParserError, ValueError) as e:
            raise FileLoadError(f"Cannot read Retsinformation HTML {file}: {e}") from e

        content = next(iter(root.xpath('//*[@id="INDHOLD"]')), root)
        title = next(iter(content.xpath('.//*[contains(@class, "TITLE") and not(contains(@class, "SUB"))'
                                        ' and not(contains(@class, "KTITLE"))]')), None)
        self.preface = _text(title) if title is not None else None
        formula = content.xpath('.//*[contains(concat(" ", normalize-space(@class), " "), " SUB-TITLE ")]')
        self.formula = ' '.join(_text(f) for f in formula) or None

        body = BodyBuilder()
        state: dict[str, Any] = {'division': None}
        for element in content.iter():
            if not isinstance(element.tag, str):
                continue
            classes = _classes(element)
            if 'KTITLE1' in classes:
                label = _text(element).rstrip('.')
                kind = 'part' if label.lower().startswith('afsnit') else 'chapter'
                state['division'] = body.division(kind, label, token=eid_token(label.split()[-1]) if label else None)
            elif 'KTITLE2' in classes and state['division'] is not None:
                division = state['division']
                heading = _text(element)
                division['heading'] = f"{division['heading']} {heading}" if division.get('heading') else heading
            elif 'PARAGRAPH' in classes and element.tag == 'div':
                self._read_article(element, body)
                state['division'] = None
            elif 'GIVET' in classes and element.tag == 'div':
                lines = [_text(line) for line in element.iter('p', 'pre') if _text(line)]
                self.conclusions = {'conclusion_text': ' '.join(lines), 'signature': None}
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        return self

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    @staticmethod
    def _read_article(block: etree._Element, body: BodyBuilder) -> None:
        children = ChildrenBuilder()
        num = None
        for element in block:
            if not isinstance(element.tag, str):
                continue
            text = _text(element)
            if not text:
                continue
            classes = _classes(element)
            if 'PARAB' in classes:
                match = _ARTICLE.match(text)
                if match:
                    num = ' '.join(match.group(1).split())
                    text = match.group(2)
                stk = re.match(r'^Stk\.\s*1\.\s*', text)
                children.add(text[stk.end():] if stk else text, number='1')
            elif 'STK' in classes:
                match = _SUBSECTION.match(text)
                children.add(text, number=match.group(1) if match else None)
            elif element.tag in ('ul', 'ol', 'table') and children.children:
                children.extend(text)
            else:
                children.add(text)
        body.article(num, None, children.children, token=eid_token(num))
