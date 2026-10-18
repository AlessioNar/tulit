"""
Parser for Danish legislation in the LexDania XML schema (Retsinformation).

- ``TitelGruppe/Titel`` gives the preface; the royal formula (``Hymne``) of
  an act or the introduction (``Indledning``) of a consolidation gives the
  enacting formula;
- ``Afsnit`` and ``Kapitel`` become parts and chapters, a titled
  ``ParagrafGruppe`` an unnumbered division;
- each ``Paragraf`` (§) becomes an article; its subsections (``Stk``) become
  par_1, par_2, ... (the first, unlabelled Stk is stk. 1), with numbered
  lists (``Indentatio``) folded into their subsection;
- annexes (``Bilag``) become annexes, and the entry-into-force provisions
  of amending acts that consolidations reproduce (``Ikraft``) become
  attachments (att_N);
- an amending act's §§ (``AendringCentreretParagraf``) become articles whose
  numbered amendments (``AendringsNummer``) carry the instruction, its action
  and the new text;
- footnotes (``Nota``) are left out of the text.
"""
import re
from typing import Any, Optional

from lxml import etree

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder, element_text, eid_token

BLOCK_TAGS = ('Linea', 'Exitus', 'Explicatus', 'Indentatio', 'Index', 'Stk', 'Rubrica',
              'TekstGruppe', 'Tabel', 'TR', 'TD', 'Row', 'Cell')
SKIP_TAGS = ('Nota',)

DIVISIONS = {'Afsnit': 'part', 'Kapitel': 'chapter', 'Afdeling': 'section'}

# Amending verbs, checked in order
ACTIONS = tuple((re.compile(pattern), action) for pattern, action in (
    (r'\bophæves\b', 'repeal'), (r'\budgår\b', 'delete'), (r'\b(ny)?affattes\b', 'replace'),
    (r'\bændres\b.*\btil\b', 'replace'), (r'\berstattes\b', 'replace'), (r'\bindsættes\b', 'insert'),
    (r'\btilføjes\b', 'add'), (r'\bbliver\b.*\b(stk|nr|§)', 'renumber'),
))
_AMENDED_ACT = re.compile(r'(?:lov|lovbekendtgørelse|bekendtgørelse)\s+nr\.\s*\d+\s+af\s+\d{1,2}\.\s*\w+\s+\d{4}',
                          re.IGNORECASE)


def amendment_action(instruction: str) -> str:
    """'§ 13, stk. 1-3, ophæves.' -> 'repeal', '§ 7 affattes således:' -> 'replace'."""
    lowered = instruction.lower()
    for pattern, action in ACTIONS:
        if pattern.search(lowered):
            return action
    return 'amend'


def _text(element: Optional[etree._Element], skip: tuple = ()) -> str:
    if element is None:
        return ''
    return element_text(element, BLOCK_TAGS, SKIP_TAGS + skip)


def _label(element: etree._Element) -> Optional[str]:
    label = element.find('Explicatus')
    text = _text(label)
    return text.rstrip('.').strip() or None


class LexDaniaParser(Parser):
    """Parses a Retsinformation LexDania XML document into legalJSON."""

    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, Optional[str]] = {}

    def parse(self, file: str, **options) -> 'LexDaniaParser':
        try:
            self.root = etree.parse(file).getroot()
        except (OSError, etree.XMLSyntaxError) as e:
            raise FileLoadError(f"Cannot read LexDania document {file}: {e}") from e

        meta = self.root.find('Meta')
        self.meta = {child.tag: (child.text or '').strip() or None
                     for child in (meta if meta is not None else []) if isinstance(child.tag, str)}

        self.get_preface()
        self.formula = (_text(self.root.find('.//DokumentIndhold/Hymne'))
                        or _text(self.root.find('.//DokumentIndhold/Indledning')) or None)
        body = BodyBuilder()
        content = self.root.find('DokumentIndhold')
        if content is not None:
            self._walk(content, body)
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        self._read_annexes()
        self._read_conclusions()
        return self

    def get_preface(self) -> Optional[str]:
        title = self.root.find('.//TitelGruppe/Titel')
        self.preface = _text(title) or self.meta.get('DocumentTitle')
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _walk(self, element: etree._Element, body: BodyBuilder) -> None:
        for child in element:
            if not isinstance(child.tag, str):
                continue
            if child.tag in DIVISIONS:
                label, heading = _label(child), _text(child.find('Rubrica')) or None
                if label or heading:  # some consolidations wrap the body in an empty Afsnit
                    body.division(DIVISIONS[child.tag], label, heading=heading,
                                  token=child.get('localId') or eid_token(label))
                self._walk(child, body)
            elif child.tag == 'ParagrafGruppe':
                rubrica = child.find('Rubrica')
                if rubrica is not None and _text(rubrica):
                    body.division('group', None, heading=_text(rubrica))
                self._walk(child, body)
            elif child.tag in ('Paragraf', 'IkraftCentreretParagraf'):
                self._read_article(child, body)
            elif child.tag == 'AendringCentreretParagraf':
                self._read_amending_article(child, body)
            elif child.tag in ('Bog', 'Del'):
                self._walk(child, body)

    def _read_article(self, paragraph: etree._Element, body: BodyBuilder) -> None:
        children = ChildrenBuilder()
        subsections = paragraph.findall('Stk')
        for position, stk in enumerate(subsections, start=1):
            label = _label(stk)
            number = eid_token(label) if label else (str(position) if position == 1 else None)
            # The published label ('Stk. 2.') stays in the text, as paragraph
            # numbers do in the other parsers
            children.add(_text(stk), number=number)
        if not subsections:
            for block in paragraph:
                if isinstance(block.tag, str) and block.tag not in ('Explicatus', 'Rubrica', 'Nota'):
                    text = _text(block)
                    if text:
                        children.add(text)
        body.article(_label(paragraph), _text(paragraph.find('Rubrica')) or None,
                     children.children, token=paragraph.get('localId'))

    def _read_amending_article(self, paragraph: etree._Element, body: BodyBuilder) -> None:
        """An amending §: its introduction naming the amended act, then one child per numbered amendment."""
        children = ChildrenBuilder()
        intro = _text(paragraph.find('Exitus'))
        amended = _AMENDED_ACT.search(intro)
        if intro:
            children.add(intro)
        for item in paragraph.findall('AendringsNummer'):
            label = _label(item)
            instruction = ' '.join(_text(d) for d in item.iter('AendringDefinition'))
            quoted = [{'kind': 'text', 'text': text} for text in
                      (_text(new) for new in item.iter('AendringNyTekst')) if text]
            child = children.add(_text(item), number=eid_token(label) if label else None)
            child['amendment'] = {
                'action': amendment_action(instruction),
                'instruction': instruction or _text(item),
                'amended_act': amended.group(0) if amended else None,
                'quoted': quoted,
            }
        body.article(_label(paragraph), None, children.children, token=paragraph.get('localId'))

    def _read_annexes(self) -> None:
        self.annexes = []
        for position, annex in enumerate(self.root.findall('.//Bilag'), start=1):
            children = ChildrenBuilder()
            content = annex.find('BilagIndhold')
            for block in (content.iter('Exitus') if content is not None else []):
                if block.getparent().tag == 'Exitus':
                    continue
                text = _text(block)
                if text:
                    children.add(text)
            self.annexes.append({
                'eId': f"anx_{annex.get('localId') or position}",
                'num': _label(annex),
                'heading': _text(annex.find('Rubrica')) or None,
                'children': children.children,
            })
        for position, block in enumerate(self.root.findall('.//DokumentIndhold/Ikraft'), start=1):
            intro = block.find('Exitus')
            children = ChildrenBuilder()
            for paragraph in block.findall('IkraftCentreretParagraf'):
                number = _label(paragraph)
                for stk in paragraph.findall('Stk') or [paragraph]:
                    text = _text(stk) if stk is not paragraph else _text(stk, skip=('Explicatus',))
                    children.add(' '.join(filter(None, [number, text])))
            self.annexes.append({
                'eId': f'att_{position}',
                'num': None,
                'heading': _text(intro) or None,
                'children': children.children,
            })

    def _read_conclusions(self) -> None:
        signatories = [s.text.strip() for s in self.root.findall('Meta/Signature') if s.text and s.text.strip()]
        place = self.meta.get('PlaceOfSignature')
        date = self.meta.get('DiesSigni')
        signature_block = _text(self.root.find('UnderskriftGruppe'))
        if not (signatories or place or signature_block):
            self.conclusions = None
            return
        self.conclusions = {
            'conclusion_text': signature_block,
            'signature': {
                'place': place,
                'date': date,
                'signatory': signatories[0] if signatories else None,
                'title': None,
            },
        }
        if len(signatories) > 1:
            self.conclusions['signature']['signatories'] = signatories
