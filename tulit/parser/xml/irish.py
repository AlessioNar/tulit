"""
Parser for Irish Acts in the XML of the Irish Statute Book and the Revised Acts.

The Irish Statute Book (Acts as enacted) and the Law Reform Commission's
Revised Acts (consolidated) share one schema:

- ``metadata/title`` gives the preface; the long title and the enacting
  formula ("Be it enacted by the Oireachtas as follows:") close the front
  matter;
- ``part`` and ``chapter`` become divisions, ``sect`` (section) articles;
  subsections '(1)', '(2)' become par_N, with paragraphs '(a)' folded into
  their subsection;
- schedules become annexes;
- footnotes (``fn``) and the editorial annotations of Revised Acts are left
  out. Characters encoded as elements (``<afada/>`` for á, ``<odq/>`` for “)
  are restored.
"""
import copy
import re
from typing import Any, Optional

from lxml import etree

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder, element_text

CHARACTERS = {
    'afada': 'á', 'efada': 'é', 'ifada': 'í', 'ofada': 'ó', 'ufada': 'ú',
    'Afada': 'Á', 'Efada': 'É', 'Ifada': 'Í', 'Ofada': 'Ó', 'Ufada': 'Ú',
    'odq': '“', 'cdq': '”', 'osq': '‘', 'csq': '’', 'emdash': '—', 'endash': '–',
    'euro': '€', 'pound': '£', 'bull': '•', 'nbsp': ' ', 'section': '§',
}
BLOCK_TAGS = ('p', 'title', 'number', 'tr', 'td', 'table')
SKIP_TAGS = ('fn', 'marker', 'graphic', 'hr1')
_SUBSECTION = re.compile(r'^\((\d+[A-Z]*)\)\s')
_SECTION_NUMBER = re.compile(r'^\d+[A-Z]*\.\s*')


def _restore_characters(root: etree._Element) -> None:
    for element in list(root.iter(*CHARACTERS)):
        character = CHARACTERS[element.tag]
        parent = element.getparent()
        if parent is None:
            continue
        text = character + (element.tail or '')
        previous = element.getprevious()
        if previous is not None:
            previous.tail = (previous.tail or '') + text
        else:
            parent.text = (parent.text or '') + text
        parent.remove(element)


def _is_annotation(element: etree._Element) -> bool:
    return element.tag == 'div' and 'annotations' in (element.get('class') or '')


def _text(element: Optional[etree._Element]) -> str:
    if element is None:
        return ''
    return element_text(element, BLOCK_TAGS, SKIP_TAGS)


def _title_lines(title: Optional[etree._Element]) -> list[str]:
    """Lines of a division title, from its paragraphs only (Revised Acts repeat them as plain text)."""
    if title is None:
        return []
    lines = [_text(p) for p in title.findall('p')]
    return [line for line in lines if line] or ([_text(title)] if _text(title) else [])


class IrishActParser(Parser):
    """Parses an Irish Act (Statute Book or Revised Acts XML) into legalJSON."""

    def parse(self, file: str, **options) -> 'IrishActParser':
        try:
            self.root = etree.parse(file).getroot()
        except (OSError, etree.XMLSyntaxError) as e:
            raise FileLoadError(f"Cannot read Irish Act {file}: {e}") from e
        self.root = copy.deepcopy(self.root)
        _restore_characters(self.root)
        for annotation in [e for e in self.root.iter('div') if _is_annotation(e)]:
            annotation.getparent().remove(annotation)

        self.get_preface()
        self._read_front_matter()
        body = BodyBuilder()
        content = self.root.find('body')
        if content is not None:
            self._walk(content, body)
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        self._read_schedules()
        return self

    def get_preface(self) -> Optional[str]:
        self.preface = self.root.findtext('metadata/title') or None
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _read_front_matter(self) -> None:
        """Long title ('An Act to ...') and enacting formula, at the end of the front matter."""
        front = self.root.find('frontmatter')
        if front is None:
            return
        lines = [_text(p) for p in front.findall('p')]
        lines = [line for line in lines if line]
        start = next((i for i, line in enumerate(lines) if line.startswith('An Act ')), None)
        if start is None:
            return
        long_title = lines[start:]
        formula = next((i for i, line in enumerate(long_title) if line.lower().startswith('be it enacted')), None)
        if formula is not None:
            self.formula = ' '.join(long_title[formula:])
            long_title = long_title[:formula]
        self.recitals = [{'eId': f'rct_{n}', 'text': text} for n, text in enumerate(long_title, start=1)]

    def _walk(self, element: etree._Element, body: BodyBuilder) -> None:
        for child in element:
            if not isinstance(child.tag, str):
                continue
            if child.tag in ('part', 'chapter'):
                lines = _title_lines(child.find('title'))
                number = lines[0] if lines else None
                heading = ' '.join(lines[1:]) or None
                match = re.search(r'\b([0-9]+[A-Z]?|[IVXLC]+)\b', number or '')
                body.division('part' if child.tag == 'part' else 'chapter', number, heading=heading,
                              token=match.group(1) if match else None)
                self._walk(child, body)
            elif child.tag == 'sect':
                self._read_section(child, body)

    def _read_section(self, section: etree._Element, body: BodyBuilder) -> None:
        number = (section.findtext('number') or '').strip().rstrip('.')
        children = ChildrenBuilder()
        for block in section:
            if not isinstance(block.tag, str) or block.tag in ('number', 'title') + SKIP_TAGS:
                continue
            text = _text(block)
            if not text:
                continue
            if not children.children:
                text = _SECTION_NUMBER.sub('', text, count=1) if text.startswith(f'{number}.') else text
            match = _SUBSECTION.match(text)
            if match:
                children.add(text, number=match.group(1))
            elif children.children:
                children.extend(text)
            else:
                children.add(text)
        title = ' '.join(_title_lines(section.find('title'))) or None
        body.article(f'Section {number}' if number else None, title, children.children,
                     token=number or None)

    def _read_schedules(self) -> None:
        self.annexes = []
        for position, schedule in enumerate(self.root.iter('schedule'), start=1):
            lines = _title_lines(schedule.find('title'))
            children = ChildrenBuilder()
            for block in schedule:
                if isinstance(block.tag, str) and block.tag != 'title' and block.tag not in SKIP_TAGS:
                    text = _text(block)
                    if text:
                        children.add(text)
            match = re.search(r'\b(\d+)\b', lines[0] if lines else '')
            self.annexes.append({
                'eId': f'anx_{match.group(1) if match else position}',
                'num': lines[0] if lines else None,
                'heading': ' '.join(lines[1:]) or None,
                'children': children.children,
            })
