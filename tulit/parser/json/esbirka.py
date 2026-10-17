"""
Parser for Czech legislation from e-Sbírka (the Collection of Laws), in JSON.

e-Sbírka serves every version (znění) of an act as a list of fragments, each
with a type (``kodTypuFragmentu``), a depth (``hloubka``), an address
(``staleUrl``, e.g. '/sb/2019/110/2025-08-01#par_18-odst_2') and its text as
XHTML. ``EsbirkaClient`` saves them, with the act's metadata, as one JSON
document:

- the prefix fragments give the preface ('Zákon ze dne 12. března 2019 o
  zpracování osobních údajů') and the enacting formula;
- divisions keep their nesting: část becomes a part, hlava a title, díl a
  chapter, oddíl a section and pododdíl a subsection, with the heading below
  them (Nadpis_pod);
- each paragraph (§) or article (Čl.) becomes an article, a heading above
  it (Nadpis_nad) its heading; its subsections (odstavec) become par_N with
  letters and points folded in;
- each point of an amending article is a child with a structured
  ``amendment`` whose quoted text is the citation block (Block_Citace);
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


def fragment_text(markup: Optional[str]) -> str:
    """Plain text of a fragment's XHTML, superscripts kept ('Unie¹)')."""
    if not markup or not markup.strip():
        return ''
    root = html.fragment_fromstring(markup, create_parent='div')
    for sup in root.iter('sup'):
        sup.text = (sup.text or '').translate(SUPERSCRIPT)
    return ' '.join(root.text_content().split())


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
        quote_depth: Optional[int] = None

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

            if kind in SKIPPED or (not text and kind != 'Block_Citace'):
                continue
            if kind in ('Prefix_Type', 'Prefix_Date', 'Prefix_Title', 'Prefix_Number'):
                if kind != 'Prefix_Number':
                    title_parts.append(text)
                continue
            if kind == 'Prefix':
                self.formula = text
                continue
            if kind == 'Postfix':
                signatures.append(text)
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
                continue
            self._read_content(article, kind, text, anchor)
            if kind == 'Block_Citace':
                quote_depth = depth
        flush()

        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        self.preface = ' '.join(title_parts) or self.metadata.get('uplnaCitace') or None
        if signatures:
            self.conclusions = {'conclusion_text': None, 'signature': ', '.join(signatures)}

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
