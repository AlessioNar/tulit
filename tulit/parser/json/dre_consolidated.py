"""
Parser for consolidated Portuguese legislation from the Diário da República (Legislação Consolidada).

``PortugalConsolidatedClient`` saves an act, as in force on a date, as one
JSON document: the act's details (``diploma``) and its fragments in
document order, each with a type (``TipoFragmentoId``), a depth (``Nivel``),
a title ('Artigo 5.º', 'Capítulo II'), a heading (``Epigrafe``), its text
and the state of its version (in force, repealed, suspended):

- the designation, date and name or summary of the act give the preface;
  the text of the act itself (the root fragment) its preamble: the
  enacting clause ('... decreta o seguinte:') is the formula, the
  paragraphs above it the recitals;
- Livro, Parte, Título, Subtítulo, Capítulo, Secção, Subsecção, Divisão
  and Subdivisão become divisions, nested by their depth;
- each Artigo (or Base) becomes an article with its heading; numbered
  paragraphs ('1 - ...', '1. ...') become par_N with their points ('a)
  ...') folded in; an article repealed on the date reads '(Revogado.)';
- an act approved in an annex (a code: 'Anexo - CÓDIGO DO TRABALHO') is a
  division of type 'annex', whose articles have eIds of the form
  ``anx_1__art_5``, so they do not clash with the approving act's; text
  above its first article (the code's own preamble) adds to the recitals;
- an annex without articles (a table, a map) becomes an annex;
- the signatures become the conclusions; editorial notes are left out.
"""
import html
import json
import re
from typing import Any, Optional

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder

# TipoFragmentoId of the fragments that are not divisions
ARTICLE, SIGNATURE, ANNEX, ROOT = 11, 7, 14, 15
# Division types by TipoFragmentoId, and by the first word of their title
DIVISION_TYPES = {12: 'book', 4: 'part', 13: 'title', 5: 'subtitle', 1: 'chapter', 8: 'section', 3: 'subsection',
                  9: 'division', 6: 'subdivision'}
DIVISION_WORDS = {'livro': 'book', 'parte': 'part', 'título': 'title', 'subtítulo': 'subtitle', 'capítulo': 'chapter',
                  'subcapítulo': 'subchapter', 'secção': 'section', 'subsecção': 'subsection', 'divisão': 'division',
                  'subdivisão': 'subdivision'}
EID_PREFIXES = {'book': 'bok', 'part': 'prt', 'title': 'tit', 'subtitle': 'stt', 'chapter': 'cpt',
                'subchapter': 'scp', 'section': 'sct', 'subsection': 'sbs', 'division': 'dvs',
                'subdivision': 'sdv', 'annex': 'anx'}
REPEALED = 4
MONTHS = ('janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro',
          'outubro', 'novembro', 'dezembro')

_PARAGRAPH = re.compile(r'^(?P<num>\d+(?:\.º)?(?:-[A-Z]+)?)\s*(?:-|\.|–|—)\s+')
_POINT = re.compile(r'^(?:[a-z]{1,2}\)|[ivxlc]+\)|\d+\.\d+(?:\.\d+)*\.?)\s')
_DESIGNATION = re.compile(r'^(?:Lei|Decreto|Portaria|Resolução|Despacho|Declaração|Aviso|Regulamento)\b.*\bn\.[ºo]\s',
                          re.IGNORECASE)
_DATE_LINE = re.compile(r'^de \d{1,2} de \w+$', re.IGNORECASE)
_NUMBER = re.compile(r'(?P<number>\d+)(?:\.?[ºo])?(?:-(?P<letter>[A-Z]+))?', re.IGNORECASE)


def text_lines(text: Optional[str]) -> list[str]:
    """The lines of a fragment's text, without markup ('<br/>' ends a line, links keep their text)."""
    if not text:
        return []
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    # A link whose opening tag lost its '>' ('title="...Europeia!�2011/96/CE</a>') ends at the broken character
    text = re.sub(r'<a\s[^<>]*?(?:>|�)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^<>]+>', '', text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f�]', ' ', html.unescape(text))
    lines = (' '.join(line.split()) for line in text.split('\n'))
    return [line for line in lines if line]


def inline_text(text: Optional[str]) -> Optional[str]:
    """A title or heading on one line, without markup."""
    return ' '.join(text_lines(text)) or None


def number_token(identification: Optional[str]) -> Optional[str]:
    """'5.º' -> '5', '10.º-A' -> '10a', '374-B' -> '374b', 'único' -> 'unico', 'IV' -> 'IV'."""
    value = (identification or '').strip()
    if not value:
        return None
    match = _NUMBER.match(value)
    if match:
        return match.group('number') + (match.group('letter') or '').lower()
    if value.lower() in ('único', 'única'):
        return 'unico'
    match = re.fullmatch(r'([IVXLCDM]+)(?:-([A-Z]))?', value)
    return match.group(1) + (match.group(2) or '') if match else None


class _Body(BodyBuilder):
    """BodyBuilder with eId prefixes for the Portuguese divisions, and articles of an annexed act."""

    def division(self, type_: str, num: Optional[str] = None, heading: Optional[str] = None,
                 token: Optional[str] = None, rank: Optional[float] = None) -> dict[str, Any]:
        rank = 0 if rank is None else rank
        while self._stack and self._stack[-1][0] >= rank:
            self._stack.pop()
        parent = self.current_division
        prefix = EID_PREFIXES.get(type_, 'div')
        self._counts[prefix] = self._counts.get(prefix, 0) + 1
        eid = self._unique(f'{prefix}_{token or self._counts[prefix]}')
        chapter = {'eId': eid, 'type': type_, 'num': num, 'heading': heading,
                   'parent': parent['eId'] if parent else None}
        node = {'eId': eid, 'type': type_, 'num': num, 'children': []}
        container = self._stack[-1][1]['children'] if self._stack else self.structure
        container.append(node)
        self.chapters.append(chapter)
        self._stack.append((rank, node, chapter))
        return chapter

    def article(self, num: Optional[str], heading: Optional[str], children: list[dict[str, Any]],
                token: Optional[str] = None, prefix: str = '') -> dict[str, Any]:
        self._counts['art'] = self._counts.get('art', 0) + 1
        eid = self._unique(f"{prefix}art_{token or self._counts['art']}")
        parent = self.current_division
        article = {'eId': eid, 'num': num, 'heading': heading, 'children': children,
                   'parent': parent['eId'] if parent else None}
        container = self._stack[-1][1]['children'] if self._stack else self.structure
        container.append({'eId': eid, 'type': 'article'})
        self.articles.append(article)
        return article


def _date_words(iso: Optional[str]) -> Optional[str]:
    """'1995-03-15T00:00:00Z' -> '15 de março'."""
    match = re.match(r'^(\d{4})-(\d{2})-(\d{2})', iso or '')
    if not match or match.group(1) == '1900':
        return None
    return f'{int(match.group(3))} de {MONTHS[int(match.group(2)) - 1]}'


class DREConsolidatedParser(Parser):
    """Parses a consolidated act of the Diário da República (JSON saved by PortugalConsolidatedClient)."""

    def __init__(self) -> None:
        super().__init__()
        self.in_force: Optional[bool] = None

    def parse(self, file: str, **options) -> 'DREConsolidatedParser':
        try:
            with open(file, encoding='utf-8') as f:
                document = json.load(f)
            fragments = document['fragments']
            diploma = document.get('diploma') or {}
        except (OSError, ValueError, KeyError, TypeError) as e:
            raise FileLoadError(f"Cannot read Diário da República consolidated act {file}: {e}") from e
        self.preface = self._preface(diploma)
        self._read([f for f in fragments if not f.get('IsHidden')])
        return self

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    @staticmethod
    def _preface(diploma: dict[str, Any]) -> Optional[str]:
        """'Decreto-Lei n.º 48/95, de 15 de março - Código Penal - CP'."""
        fragment = diploma.get('DiplomaFrag') or {}
        legis = diploma.get('DiplomaLegis') or {}
        title = inline_text(fragment.get('ConteudoTitle') or legis.get('ConteudoTitle')) or ''
        date = _date_words(legis.get('DataPublicacao') or (diploma.get('DiarioRepublica') or {}).get('DataPublicacao'))
        if title and date:
            title = f'{title}, de {date}'
        name = inline_text(fragment.get('Designacao') or legis.get('Sumario')) or ''
        return ' - '.join(part for part in (title, name) if part) or None

    def _read(self, fragments: list[dict[str, Any]]) -> None:
        body = _Body()
        signatures: list[str] = []
        root_repealed = False
        prefix = ''
        articles_in_scope = 0
        self.recitals, self.annexes = [], []
        annexes = 0

        def recital(text: str) -> None:
            self.recitals.append({'eId': f'rct_{len(self.recitals) + 1}', 'text': text})

        for fragment in fragments:
            version = fragment.get('FragmentoVersao') or {}
            position = fragment.get('ConsolidacaoFragmento') or {}
            kind = version.get('TipoFragmentoId')
            title = inline_text(version.get('Tituo') or position.get('Name')) or ''
            heading = inline_text(version.get('Epigrafe') or position.get('Epigrafe'))
            lines = text_lines(version.get('Texto'))
            level = fragment.get('Nivel') or 0
            repealed = version.get('VersaoEstadoId') == REPEALED
            word = title.split()[0].lower() if title else ''

            if kind == ROOT:
                root_repealed = repealed
                self._preamble(lines)
                continue
            if kind == SIGNATURE or word == 'assinatura':
                signatures.extend(lines)
                continue
            if kind == ARTICLE or word in ('artigo', 'base'):
                children = ChildrenBuilder()
                if repealed and not root_repealed:
                    children.add('(Revogado.)')
                else:
                    self._paragraphs(children, lines)
                body.article(title or None, heading, children.children,
                             token=number_token(version.get('Identificacao') or title.partition(' ')[2]),
                             prefix=prefix)
                articles_in_scope += 1
                continue
            if kind == ANNEX or word == 'anexo':
                if fragment.get('HasFilhos'):
                    if body.articles:
                        # An act approved in an annex (a code): its articles get the annex's eId as prefix
                        annexes += 1
                        num = title if word == 'anexo' else None
                        division = body.division('annex', num, heading or (title if num is None else None),
                                                 token=str(annexes), rank=level)
                        prefix = f"{division['eId']}__"
                        articles_in_scope = 0
                    else:
                        # A group of articles at the top of the act ('Princípios fundamentais')
                        body.division('part', None, heading or title, rank=level)
                    for line in lines:
                        if articles_in_scope == 0:
                            recital(line)
                    continue
                annexes += 1
                children = ChildrenBuilder()
                for line in lines:
                    children.add(line)
                if children.children:
                    self.annexes.append({'eId': f'anx_{annexes}', 'num': title or None, 'heading': heading,
                                         'children': children.children})
                continue
            type_ = DIVISION_TYPES.get(kind) or DIVISION_WORDS.get(word)
            if lines and not fragment.get('HasFilhos') and articles_in_scope == 0:
                # Text above the first article of an annexed code: its preamble ('I - Introdução')
                recital(f'{title} - {heading}' if heading else title)
                for line in lines:
                    recital(line)
                continue
            if type_ is None and lines:
                annexes += 1
                children = ChildrenBuilder()
                for line in lines:
                    children.add(line)
                self.annexes.append({'eId': f'anx_{annexes}', 'num': title or None, 'heading': heading,
                                     'children': children.children})
                continue
            if word in DIVISION_WORDS or number_token(title):
                num = title
            else:
                # A group named, not numbered ('Disposições finais e transitórias')
                num, heading = None, heading or title or None
            body.division(type_ or 'division', num, heading,
                          token=number_token(version.get('Identificacao')) if num else None, rank=level)
            for line in lines:
                # Text of a division (rare): keep it with the recitals before the first article
                if articles_in_scope == 0:
                    recital(line)

        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        self.in_force = not root_repealed
        if signatures:
            self.conclusions = {'conclusion_text': ' '.join(signatures[:-1]) or None, 'signature': signatures[-1]}

    def _preamble(self, lines: list[str]) -> None:
        """The act's own text: its designation and date, the preamble and the enacting clause."""
        lines = list(lines)
        while lines and (_DESIGNATION.match(lines[0]) and len(lines[0]) < 80 or _DATE_LINE.match(lines[0])
                         or lines[0].lower().startswith('sumário:')):
            lines.pop(0)
        if lines and lines[-1].endswith(':'):
            formula = lines.pop()
            if lines and lines[-1].rstrip(':').lower() == 'assim':
                formula = f'{lines.pop()} {formula}'
            self.formula = formula
        for line in lines:
            self.recitals.append({'eId': f'rct_{len(self.recitals) + 1}', 'text': line})

    @staticmethod
    def _paragraphs(children: ChildrenBuilder, lines: list[str]) -> None:
        for line in lines:
            match = _PARAGRAPH.match(line)
            if match:
                children.add(line, number=match.group('num'), token=number_token(match.group('num')))
            elif children.children and (_POINT.match(line) or children.children[-1]['text'].endswith(':')):
                children.extend(line)
            else:
                children.add(line)
