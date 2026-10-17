"""
Parser for the Austrian Federal Law Gazette (Bundesgesetzblatt, BGBl.) in RIS XML.

The authentic electronic BGBl. (from 2004) is published as one XML document
per gazette issue, in the same ``risdok`` format as consolidated RIS law
(namespace http://www.bka.gv.at). A gazette issue holds the law as adopted:

- the title ('5. Bundesgesetz, mit dem ...') gives the preface and the
  enacting formula ('Der Nationalrat hat beschlossen:') the formula;
- 'Artikel N' headings divide omnibus laws (Sammelgesetze). An Artikel that
  amends another act becomes an article whose children are the numbered
  amending instructions (Novellierungsanordnungen), with a structured
  ``amendment``; an Artikel that enacts a new law becomes a part holding
  its divisions (Abschnitt, ...) and paragraphs (§);
- each § becomes an article, its subsections '(1)', '(2)' children par_N;
- annexes (Anlage) become annexes and the signatures the conclusions.
"""
import re
from typing import Any, Optional

from lxml import etree

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder, element_text, eid_token
from tulit.parser.xml.ris import BLOCK_TAGS, classify_division

_SECTION = re.compile(r'^§\s*(\d+[a-z]*)\.\s*')
_SUBSECTION = re.compile(r'^\((\d+[a-z]*)\)\s*')
_INSTRUCTION = re.compile(r'^(\d+[a-z]*)\.\s')
_ARTIKEL = re.compile(r'^Artikel\s+([0-9]+[a-z]?|[IVXLC]+)$')
_ANNEX = re.compile(r'^Anlage\b')
_CITATION = re.compile(r'BGBl\.\s*(?:I{1,3}\s*)?Nr\.\s*\d+/\d{4}')
_SKIP = ('kzinhalt', 'fzinhalt', 'ausgabe', 'inhaltsvz', 'layoutdaten', 'metadaten')

# Amending verbs, checked in order
ACTIONS = (
    ('entfällt', 'delete'), ('entfallen', 'delete'), ('aufgehoben', 'delete'),
    ('eingefügt', 'insert'), ('angefügt', 'add'),
    ('ersetzt', 'replace'), ('lautet', 'replace'), ('lauten', 'replace'),
)


def amendment_action(instruction: str) -> Optional[str]:
    """'Art. 15 Abs. 7 lautet:' -> 'replace', '... wird folgender Abs. 7 angefügt:' -> 'add'."""
    lowered = instruction.lower()
    for verb, action in ACTIONS:
        if verb in lowered:
            return action
    return None


def _strip_quotes(text: str) -> str:
    return text.strip().strip('„“”"').strip()


class BGBlParser(Parser):
    """Parses an issue of the Austrian Federal Law Gazette (authentic RIS XML) into legalJSON."""

    def parse(self, file: str, **options) -> 'BGBlParser':
        try:
            root = etree.parse(file).getroot()
        except (OSError, etree.XMLSyntaxError) as e:
            raise FileLoadError(f"Cannot read BGBl document {file}: {e}") from e

        elements = [e for section in root.iter('{*}abschnitt') for e in section
                    if isinstance(e.tag, str) and etree.QName(e).localname not in _SKIP]
        self._read_front(elements)
        self._read_body(elements)
        return self

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _read_front(self, elements: list[etree._Element]) -> None:
        for element in elements:
            if etree.QName(element).localname == 'ueberschrift' and element.get('typ') == 'titel':
                # '5. Bundesgesetz, mit dem ...': the issue number is not part of the title
                self.preface = re.sub(r'^\d+\.\s*', '', element_text(element, BLOCK_TAGS)) or None
                break

    def _read_body(self, elements: list[etree._Element]) -> None:
        builder = BodyBuilder()
        self.annexes = []
        signatures: list[str] = []
        state: dict[str, Any] = {'article': None, 'children': None, 'heading': None,
                                 'division': None, 'amending': None, 'annex': None,
                                 'started': False, 'pending': None}

        def flush() -> None:
            if state['article'] is not None:
                num, token, heading = state['article']
                builder.article(num, heading, state['children'].children, token=token)
            state['article'] = state['children'] = None

        for position, element in enumerate(elements):
            name = etree.QName(element).localname
            typ = element.get('typ')
            if name == 'unterschrift':
                text = element_text(element, BLOCK_TAGS)
                if text:
                    signatures.append(text)
                continue
            text = element_text(element, BLOCK_TAGS)
            if not text:
                continue

            if not state['started']:
                if name == 'absatz' and typ == 'promkleinlsatz':
                    self.formula = text
                    state['started'] = True
                continue

            if state['annex'] is not None and not (name == 'ueberschrift' and _ARTIKEL.match(text)):
                annex = state['annex']
                if name == 'ueberschrift' and annex['heading'] is None and not annex['children'].children:
                    annex['heading'] = text
                else:
                    annex['children'].add(text)
                continue

            if name == 'ueberschrift' and typ in ('g1', 'g1min', 'g2'):
                artikel = _ARTIKEL.match(text) if typ == 'g1' else None
                if artikel:
                    flush()
                    self._close_annex(state)
                    if self._amends(elements[position + 1:]):
                        # The Artikel is an amending article: its instructions are the children
                        builder.close_divisions()
                        state['article'] = (text, artikel.group(1), None)
                        state['children'] = ChildrenBuilder()
                        state['amending'] = True
                        state['amended_act'] = None
                        state['division'] = None
                    else:
                        state['division'] = builder.division('part', text, token=artikel.group(1))
                        state['amending'] = False
                    continue
                if typ == 'g1' and _ANNEX.match(text):
                    flush()
                    state['annex'] = {'num': text, 'heading': None, 'children': ChildrenBuilder()}
                    continue
                division = classify_division(text) if typ == 'g1' else None
                if division and state['amending'] is not False and state['article'] is None:
                    state['amending'] = False
                if division and state['amending'] is False:
                    flush()
                    state['division'] = builder.division(division[0], text, token=division[1])
                    continue
                if state['article'] is not None and state['children'].children:
                    state['children'].extend(text)
                elif state['article'] is not None:
                    num, token, heading = state['article']
                    state['article'] = (num, token, f'{heading} {text}' if heading else text)
                elif state['division'] is not None:
                    current = state['division']
                    current['heading'] = f"{current['heading']} {text}" if current.get('heading') else text
                continue

            if name == 'ueberschrift' and typ == 'para':
                if state['amending']:
                    state['children'].extend(text)
                else:
                    flush()
                    state['pending'] = f"{state['pending']} {text}" if state['pending'] else text
                continue

            if name == 'absatz' and typ == 'promkleinlsatz' and state['article'] is None \
                    and self._amends(elements[position + 1:]):
                # An act that only amends, without Artikel headings: one amending article
                builder.close_divisions()
                state['article'] = (None, None, None)
                state['children'] = ChildrenBuilder()
                state['amending'] = True
                state['amended_act'] = None

            if name == 'absatz' and typ in ('novao1', 'novao2'):
                if state['article'] is None or not state['amending']:
                    # An act that only amends, without Artikel headings
                    flush()
                    builder.close_divisions()
                    state['article'] = (None, None, None)
                    state['children'] = ChildrenBuilder()
                state['amending'] = True
                match = _INSTRUCTION.match(text)
                child = state['children'].add(text, number=match.group(1) if match else None)
                child['amendment'] = {
                    'action': amendment_action(text),
                    'instruction': text,
                    'amended_act': state.get('amended_act'),
                    'quoted': [],
                }
                continue

            if state['amending'] and state['article'] is not None:
                children = state['children']
                if not children.children:
                    # Introductory sentence naming the amended act
                    children.add(text)
                    citation = _CITATION.search(text)
                    state['amended_act'] = citation.group(0) if citation else None
                    continue
                current = children.children[-1]
                if current.get('amendment') is not None:
                    current['amendment']['quoted'].append({'kind': 'text', 'text': _strip_quotes(text)})
                children.extend(text)
                continue

            symbol = element.find('{*}gldsym') if name == 'absatz' else None
            section = _SECTION.match(element_text(symbol, BLOCK_TAGS)) if symbol is not None else None
            if section:
                flush()
                state['article'] = (f'§ {section.group(1)}', section.group(1), state['pending'])
                state['pending'] = None
                state['children'] = ChildrenBuilder()
                state['amending'] = False
                text = element_text(element, BLOCK_TAGS, skip_tags=('gldsym',))
                if not text:
                    continue
            if state['article'] is None:
                # Content outside any § (e.g. a single-provision act)
                state['article'] = (None, None, state['pending'])
                state['pending'] = None
                state['children'] = ChildrenBuilder()
            children = state['children']
            subsection = _SUBSECTION.match(text) if name == 'absatz' else None
            if subsection:
                children.add(text, number=subsection.group(1))
            elif name == 'absatz' and (typ in ('abs', 'satz') or not children.children):
                children.add(text)
            else:
                children.extend(text)

        flush()
        self._close_annex(state)
        self.chapters, self.articles, self.structure = builder.chapters, builder.articles, builder.structure
        if signatures:
            self.conclusions = {'conclusion_text': None, 'signature': ', '.join(signatures)}

    def _close_annex(self, state: dict[str, Any]) -> None:
        annex = state.get('annex')
        if annex is None:
            return
        token = eid_token(annex['num'].replace('Anlage', '')) or str(len(self.annexes) + 1)
        self.annexes.append({'eId': f'anx_{token}', 'num': annex['num'], 'heading': annex['heading'],
                             'children': annex['children'].children})
        state['annex'] = None

    @staticmethod
    def _amends(following: list[etree._Element]) -> bool:
        """Whether an Artikel (the elements after its heading) contains amending instructions."""
        for element in following:
            name = etree.QName(element).localname
            if name == 'ueberschrift' and element.get('typ') == 'g1' and \
                    _ARTIKEL.match(element_text(element, BLOCK_TAGS)):
                return False
            if name == 'absatz' and element.get('typ') in ('novao1', 'novao2'):
                return True
            if name == 'absatz' and _SECTION.match(element_text(element, BLOCK_TAGS)):
                return False
        return False
