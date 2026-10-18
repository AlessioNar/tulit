"""
Parser for Czech legislation from e-Sbírka (the Collection of Laws), in JSON.

e-Sbírka serves every version (znění) of an act as a list of fragments, each
with a type (``kodTypuFragmentu``), a depth (``hloubka``), an address
(``staleUrl``, e.g. '/sb/2019/110/2025-08-01#par_18-odst_2') and its text as
XHTML. ``EsbirkaClient`` saves them, with the act's metadata, as one JSON
document:

- the prefix fragments give the preface ('Zákon ze dne 12. března 2019 o
  zpracování osobních údajů') and the enacting formula; a preamble
  (Preambule, or prefixes above the formula) gives the recitals;
- divisions keep their nesting: část becomes a part, hlava a title, díl a
  chapter, oddíl a section and pododdíl a subsection, with the heading below
  them (Nadpis_pod);
- each paragraph (§) or article (Čl.) becomes an article, a heading above
  it (Nadpis_nad) its heading; its subsections (odstavec) become par_N with
  letters and points folded in;
- each point of an amending article is a child with a structured
  ``amendment`` whose quoted text is the citation block (Block_Citace);
- the text of a communication without §§ is one unnumbered article;
- each annex (příloha) becomes an annex, its parts, paragraphs and table
  rows its children; an annex that is the act itself (the Charter of 2/1993
  Sb.) is read as the body;
- footnotes are left out and the signatures give the conclusions.
"""
import json
import re
from typing import Any, Optional

from lxml import html

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder

DIVISIONS = {
    'Cast': 'part',
    'Hlava': 'title',
    'Dil': 'chapter',
    'Oddil': 'section',
    'Pododdil': 'subsection',
}
ARTICLES = ('Paragraf', 'Clanek')
SKIPPED = ('PPC', 'Virtual_Document', 'Virtual_Prefix', 'Virtual_Norma', 'Virtual_Novela', 'Virtual_Postfix',
           'Virtual_PPC', 'Block_Prechodne_Ustanoveni_Nov', 'Block_Prechodne_Ustanoveni', 'Block_Zrusovaci_Ustanoveni',
           'Block_Ucinnostni_Ustanoveni')
SUPERSCRIPT = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')
_SUBSECTION = re.compile(r'-odst_(\d+[a-z]?)$')

# Amending verbs, checked in order
ACTIONS = (
    ('zrušuj', 'delete'), ('zrušuje', 'delete'), ('nahrazuj', 'replace'), ('nahrazuje', 'replace'),
    ('vkládá', 'insert'), ('vkládají', 'insert'), ('doplňuj', 'add'), ('doplňuje', 'add'),
    (' zní:', 'replace'), (' znějí:', 'replace'), ('označuj', 'renumber'),
)


def amendment_action(instruction: str) -> Optional[str]:
    """'V § 68 odstavec 5 zní:' -> 'replace'; 'V § 82 se odstavec 2 zrušuje.' -> 'delete'."""
    lowered = instruction.lower()
    for verb, action in ACTIONS:
        if verb in lowered:
            return action
    return None


def _markup(markup: Optional[str]) -> Optional[html.HtmlElement]:
    if not markup or not markup.strip():
        return None
    root = html.fragment_fromstring(markup, create_parent='div')
    for sup in root.iter('sup'):
        sup.text = (sup.text or '').translate(SUPERSCRIPT)
    for block in root.iter('td', 'th', 'tr', 'p', 'div', 'li', 'br'):
        # Table cells and lines are separate words
        block.tail = ' ' + (block.tail or '')
    return root


def fragment_text(markup: Optional[str]) -> str:
    """Plain text of a fragment's XHTML, superscripts kept ('Unie¹)')."""
    root = _markup(markup)
    return ' '.join(root.text_content().split()) if root is not None else ''


def table_rows(markup: Optional[str]) -> list[str]:
    """The rows of a table fragment as texts."""
    root = _markup(markup)
    rows = root.xpath('.//tr[not(.//tr)]') if root is not None else []
    return [text for text in (' '.join(row.text_content().split()) for row in rows) if text]


def _anchor(fragment: dict[str, Any]) -> str:
    url = fragment.get('staleUrl') or ''
    return url.split('#', 1)[1] if '#' in url else ''


def _token(anchor: str) -> Optional[str]:
    """'cast_1-hlava_2-dil_1' -> '1', 'par_39b' -> '39b'."""
    last = anchor.rsplit('-', 1)[-1]
    return last.split('_', 1)[1] if '_' in last else None


class EsbirkaParser(Parser):
    """Parses an act from e-Sbírka (fragments JSON saved by EsbirkaClient) into legalJSON."""

    def parse(self, file: str, **options) -> 'EsbirkaParser':
        try:
            with open(file, encoding='utf-8') as f:
                document = json.load(f)
            fragments = document['fragments']
        except (OSError, ValueError, KeyError, TypeError) as e:
            raise FileLoadError(f"Cannot read e-Sbírka document {file}: {e}") from e
        self.metadata = document.get('metadata') or {}
        self._read(fragments)
        return self

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _read(self, fragments: list[dict[str, Any]]) -> None:
        body = BodyBuilder()
        title_parts: list[str] = []
        signatures: list[str] = []
        division: Optional[dict[str, Any]] = None
        heading: Optional[str] = None
        article: Optional[dict[str, Any]] = None
        annex: Optional[dict[str, Any]] = None
        loose = ChildrenBuilder()
        head: Optional[str] = None
        quote_depth: Optional[int] = None
        has_title = any(f.get('kodTypuFragmentu') == 'Prefix_Title' for f in fragments)
        self.annexes, self.recitals = [], []

        def recital(text: str) -> None:
            self.recitals.append({'eId': f'rct_{len(self.recitals) + 1}', 'text': text})

        def flush() -> None:
            nonlocal article
            if article is not None:
                body.article(article['num'], article['heading'], article['children'].children,
                             token=article['token'])
            article = None

        for fragment in fragments:
            kind = fragment.get('kodTypuFragmentu') or ''
            depth = int(fragment.get('hloubka') or 0)
            text = fragment_text(fragment.get('xhtml'))
            anchor = _anchor(fragment)

            if quote_depth is not None:
                if depth > quote_depth:
                    if text and article is not None and article['children'].children:
                        current = article['children'].children[-1]
                        if current.get('amendment') is not None:
                            current['amendment']['quoted'].append({'kind': 'text', 'text': text.strip('„“')})
                        article['children'].extend(text)
                    continue
                quote_depth = None

            if kind == 'Block_Priloha_Norma':
                # An annex that is the act itself (the Charter promulgated by a resolution): read as the body
                annex = None
                continue
            if kind.startswith('Block_Priloha'):
                # An annex: everything up to the next one, its parts and tables included
                flush()
                annex = {'eId': f'anx_{len(self.annexes) + 1}', 'num': None, 'heading': None,
                         'children': ChildrenBuilder()}
                self.annexes.append(annex)
                continue
            if annex is not None:
                if kind not in SKIPPED:
                    self._read_annex(annex, fragment, kind, text)
                continue
            if kind in SKIPPED or (not text and kind != 'Block_Citace'):
                continue
            if kind in ('Prefix_Type', 'Prefix_Author', 'Prefix_Date', 'Prefix_Title', 'Prefix_Number'):
                # 'SDĚLENÍ' 'Ministerstva zahraničních věcí' 'ze dne ...' 'o sjednání ...'
                if kind != 'Prefix_Number':
                    title_parts.append(text)
                continue
            if kind in ('Prefix', 'Preambule'):
                if (text.endswith(':') or re.search(r'\busnesl', text)) and (kind == 'Prefix' or self.formula is None):
                    # The enacting formula; a preamble is above it
                    if self.formula:
                        recital(self.formula)
                    self.formula = text
                elif kind == 'Prefix' and not has_title and not self.recitals and self.formula is None \
                        and len(text) < 150 and not text.endswith('.'):
                    # The title of an act without a title fragment (Ústava České republiky), or its date again
                    if text not in title_parts:
                        title_parts.append(text)
                elif text.upper() != 'PREAMBULE':
                    recital(text)
                continue
            if kind == 'Postfix_Head':
                # 'Ministr:' above the name of who signs
                head = text
                continue
            if kind == 'Postfix':
                signatures.append(f'{head} {text}' if head else text)
                head = None
                continue
            if kind in DIVISIONS:
                flush()
                division = body.division(DIVISIONS[kind], text, token=_token(anchor), rank=depth)
                heading = None
                continue
            if kind == 'Nadpis_pod':
                if article is not None and not article['children'].children:
                    article['heading'] = f"{article['heading']} {text}" if article['heading'] else text
                elif division is not None and article is None:
                    division['heading'] = f"{division['heading']} {text}" if division.get('heading') else text
                continue
            if kind == 'Nadpis_nad':
                flush()
                heading = f'{heading} {text}' if heading else text
                continue
            if kind in ARTICLES:
                flush()
                article = {'num': text, 'heading': heading, 'token': _token(anchor),
                           'anchor': anchor, 'children': ChildrenBuilder(), 'amended_act': None}
                heading, division = None, None
                continue
            if article is None:
                if not body.articles and kind != 'Block_Citace':
                    loose.add(text)
                continue
            self._read_content(article, kind, text, anchor)
            if kind == 'Block_Citace':
                quote_depth = depth
        flush()
        if not body.articles and loose.children:
            # A communication (sdělení) or notice without §§: its text is one article
            body.article(None, None, loose.children)
        for annex in self.annexes:
            annex['children'] = annex['children'].children

        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        self.preface = ' '.join(title_parts) or self.metadata.get('uplnaCitace') or None
        if signatures:
            self.conclusions = {'conclusion_text': None, 'signature': ', '.join(signatures)}

    @staticmethod
    def _read_annex(annex: dict[str, Any], fragment: dict[str, Any], kind: str, text: str) -> None:
        children: ChildrenBuilder = annex['children']
        if kind == 'Hlavicka_priloha':
            # 'Příloha č. 1 k nařízení vlády č. 361/2007 Sb.'
            annex['num'] = text or None
        elif kind in ('Nadpis_nad', 'Nadpis') and annex['heading'] is None and not children.children:
            annex['heading'] = text or None
        elif kind == 'Tabulka':
            for row in table_rows(fragment.get('xhtml')):
                children.add(row)
        elif text:
            children.add(text)

    @staticmethod
    def _read_content(article: dict[str, Any], kind: str, text: str, anchor: str) -> None:
        children: ChildrenBuilder = article['children']
        if kind == 'Block_Citace':
            return
        point = re.fullmatch(re.escape(article['anchor']) + r'-bod_(\d+[a-z]?)', anchor)
        if kind == 'Bod_Dd' and point and article['amended_act'] is not None:
            # A point of an amending article
            child = children.add(text, number=point.group(1), token=point.group(1))
            child['amendment'] = {'action': amendment_action(text), 'instruction': text,
                                  'amended_act': article['amended_act'], 'quoted': []}
            return
        if kind == 'Odstavec_Dc' and anchor == article['anchor'] or _SUBSECTION.search(anchor) \
                and kind == 'Odstavec_Dc' and anchor.startswith(article['anchor'] + '-odst_'):
            number = _SUBSECTION.search(anchor)
            if number:
                label = f'({number.group(1)})'
                children.add(text if text.startswith(label) else f'{label} {text}',
                             number=number.group(1), token=number.group(1))
            else:
                children.add(text)
                if not article['amended_act'] and re.search(r'\bse mění (takto|následovně)', text):
                    match = re.match(r'^(.*?)(?:,\s*ve znění\b.*)?\s+se mění\b', text)
                    article['amended_act'] = match.group(1) if match else text
            return
        children.extend(text)
