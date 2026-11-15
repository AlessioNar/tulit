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
- subsections that amend another Act ('... is amended—', 'by the
  substitution of ...') carry a structured ``amendment`` with the quoted text;
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
_PLAIN_SECTION = re.compile(r'^(\d+[A-Z]*)\.\s*(?:—\s*)?')
_SECTION_NUMBER = re.compile(r'^\d+[A-Z]*\.\s*(?:—\s*)?')
# Amending provisions: 'Section 2 of the Principal Act is amended— (a) by the substitution of ...',
# 'The following section is inserted after section 6 of the Act of 1988:', 'Section 9 ... is repealed.'
_INSTRUCTION = re.compile(
    r'\b(?:is|are) (?:hereby )?(amended|repealed|inserted|substituted|deleted)\b'
    r'|\bby the (substitution|insertion|deletion|addition)\b', re.IGNORECASE)
_ACTIONS = {
    'amended': 'amend', 'repealed': 'repeal', 'inserted': 'insert', 'substituted': 'substitute',
    'deleted': 'delete', 'substitution': 'substitute', 'insertion': 'insert', 'deletion': 'delete',
    'addition': 'add',
}
_AMENDED_ACT = re.compile(r"(Principal Act|Act of \d{4}"
                          r"|[A-Z][\w(),'’-]*(?:\s+(?:[A-Z(][\w(),'’-]*|of|and|for|the|on|in|to))*?\s+Act,?\s+\d{4})")
_QUOTED = re.compile(r'“([^“”]*)”')


def _amendment(text: str) -> Optional[dict[str, Any]]:
    """The amendment an instruction makes, from the text before its first quotation."""
    instruction = text.split('“', 1)[0]
    match = _INSTRUCTION.search(instruction)
    if match is None:
        return None
    # The act is named before the verb, after 'Section 8 of the' when a provision is named
    named = instruction[:match.start()]
    named = re.split(r'\bof the\s+', named, maxsplit=1)[-1]
    named = re.sub(r'^The\s+', '', named.strip())
    act = _AMENDED_ACT.search(named)
    return {
        'action': _ACTIONS[(match.group(1) or match.group(2)).lower()],
        'instruction': instruction.strip(),
        'amended_act': act.group(1) if act else None,
        'quoted': [{'kind': 'text', 'text': quoted.strip()} for quoted in _QUOTED.findall(text)
                   if quoted.strip()],
    }


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
    # Revised Acts occasionally carry an escaped entity as text ('&amp;nbsp;')
    return ' '.join(element_text(element, BLOCK_TAGS, SKIP_TAGS).replace('&nbsp;', ' ').split())


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
            if not body.articles:
                self._read_plain_sections(content, body)
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
        start = next((i for i, line in enumerate(lines) if line.lower().startswith('an act ')), None)
        if start is None:
            return
        # The date of passing ('[24th May, 2018]') follows the long title
        long_title = [line for line in lines[start:] if not re.fullmatch(r'\[[^\]]*\d{4}\s*\]', line)]
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

    def _read_plain_sections(self, content: etree._Element, body: BodyBuilder) -> None:
        """
        Acts of the 1920s have no ``sect`` elements: their sections are paragraphs
        opening with the section number ('1. The Constitution set forth ...').
        A paragraph before the first section is the preamble.
        """
        number, children = None, ChildrenBuilder()
        for block in content:
            if not isinstance(block.tag, str) or block.tag in SKIP_TAGS:
                continue
            text = _text(block)
            if not text:
                continue
            match = _PLAIN_SECTION.match(text)
            if match:
                if number is not None:
                    body.article(f'Section {number}', None, children.children, token=number)
                number, children = match.group(1), ChildrenBuilder()
                children.add(text[match.end():])
            elif number is not None:
                children.extend(text)
            elif self.formula is None:
                self.formula = text
            else:
                self.formula = f'{self.formula} {text}'
        if number is not None:
            body.article(f'Section {number}', None, children.children, token=number)

    def _read_section(self, section: etree._Element, body: BodyBuilder) -> None:
        number = (section.findtext('number') or '').strip().rstrip('.')
        if not number:
            # Sections inserted into Revised Acts may lack a number element: id="SEC32K"
            match = re.fullmatch(r'SEC(\d+[A-Z]*)', section.get('id') or '')
            number = match.group(1) if match else ''
        children = ChildrenBuilder()
        for block in section:
            if not isinstance(block.tag, str) or block.tag in ('number', 'title') + SKIP_TAGS:
                continue
            text = _text(block)
            if not text:
                continue
            if not children.children:
                text = _SECTION_NUMBER.sub('', text, count=1) if text.startswith(f'{number}.') else text
                if not text:
                    continue
            match = _SUBSECTION.match(text)
            # Inside a quotation the subsections are those of the amended Act
            quoting = bool(children.children) and \
                children.children[-1]['text'].count('“') > children.children[-1]['text'].count('”')
            if match and not quoting:
                children.add(text, number=match.group(1))
            elif children.children:
                children.extend(text)
            else:
                children.add(text)
        for child in children.children:
            child['amendment'] = _amendment(child['text'])
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
