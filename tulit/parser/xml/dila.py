"""
Parser for French legislation in the XML of the DILA open data (JORF and LEGI).

The Direction de l'information légale et administrative publishes the
Journal officiel (JORF: texts as published) and Légifrance's consolidated
legislation (LEGI) as XML, one file per text version, text structure,
section and article:

- ``TEXTE_VERSION`` gives the title (TITREFULL) as preface, the visas
  ('Le Premier ministre, ... Vu ...; ... Décrète :') as formula, citations
  and preamble final, and the signatures (SIGNATAIRES) as conclusions;
- ``TEXTELR`` (the text's structure) and ``SECTION_TA`` give the divisions
  (Livre, Partie, Titre, Chapitre, Section, Sous-section) and their
  articles; sections named 'Annexe' become annexes;
- each ``ARTICLE`` becomes an article; its paragraphs ('I. –') become
  par_N, and where there are none each alinéa becomes a child, with points
  ('1°', 'a)') and quoted text («...») folded in. Amending alinéas carry a
  structured ``amendment``.

For LEGI, ``date`` picks the articles and sections in force on that date.
The parser reads a folder holding the files of one text (any layout).
"""
import glob
import os
import re
import unicodedata
from typing import Any, Optional

from lxml import etree

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder

OPEN_END = '2999-01-01'
_DIVISION = re.compile(r'^(?P<kind>Livre|Partie|Titre|Sous-titre|Chapitre|Sous-chapitre|Section|Sous-section|'
                       r'Paragraphe|Sous-paragraphe)\b\s*(?P<num>[^:–-]*?)\s*(?:[:–-]\s*(?P<heading>.*))?$',
                       re.IGNORECASE)
# 'PREMIÈRE PARTIE : ...' (lois de finances, de financement de la sécurité sociale)
_ORDINAL_DIVISION = re.compile(r'^(?P<num>\w+?)\s+(?P<kind>partie|livre|titre)\b\s*(?:[:–-]\s*(?P<heading>.*))?$',
                               re.IGNORECASE)
ORDINALS = {'premiere': 1, 'premier': 1, 'deuxieme': 2, 'seconde': 2, 'second': 2, 'troisieme': 3, 'quatrieme': 4,
            'cinquieme': 5, 'sixieme': 6, 'septieme': 7, 'huitieme': 8, 'neuvieme': 9, 'dixieme': 10}
# The closing formula, printed in the last article of a law
_CLOSING_FORMULA = re.compile(r"^La présente (loi|ordonnance)( organique)?\b.*\bexécutée comme loi de l.[ÉE]tat\.?$")
_PARAGRAPH = re.compile(r'^(?P<num>[IVXLC]+|\d+)\s*\.\s*(?:[-–—]\s*)?(?=\S)')
_POINT = re.compile(r'^(\d+°|[a-z]\)|\d+\)|[-–•])\s?')
DIVISIONS = {'livre': 'part', 'partie': 'part', 'titre': 'title', 'sous-titre': 'title', 'chapitre': 'chapter',
             'sous-chapitre': 'chapter', 'section': 'section', 'sous-section': 'subsection',
             'paragraphe': 'subsection', 'sous-paragraphe': 'subsection'}
RANKS = {'livre': 0, 'partie': 0, 'titre': 1, 'sous-titre': 2, 'chapitre': 3, 'sous-chapitre': 4, 'section': 5,
         'sous-section': 6, 'paragraphe': 7, 'sous-paragraphe': 8}

# Amending phrases, checked in order
ACTIONS = (
    (r'\b(est|sont) abrogée?s?\b', 'delete'),
    (r'\b(est|sont) insérée?s?\b|\bil est inséré\b', 'insert'),
    (r'\b(est|sont) (complétée?s?|ajoutée?s?)\b|\bil est ajouté\b', 'add'),
    (r'\b(est|sont) remplacée?s?\b|\b(est|sont) ainsi rédigée?s?\b', 'replace'),
    (r'\b(est|sont) ainsi modifiée?s?\b|\b(est|sont) modifiée?s?\b', 'amend'),
)
_ACT = re.compile(r"(?:^(?:Le|La|L')\s*|\b(?:du|de la|de l'|des)\s+)((?:code|loi|ordonnance|décret|arrêté)\b"
                  r"[^,;:]*?)(?=\s+(?:est|sont|il est)\b|[,;:]|$)", re.IGNORECASE)


def _plain(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')


def amendment_action(text: str) -> Optional[str]:
    """"L'article 3 est ainsi rédigé :" -> 'replace'; "Le 2° est abrogé." -> 'delete'."""
    for pattern, action in ACTIONS:
        if re.search(pattern, text, re.IGNORECASE):
            return action
    return None


def _lines(element: Optional[etree._Element]) -> list[str]:
    """The text of a CONTENU element as lines, at line breaks, paragraphs and table rows."""
    if element is None:
        return []
    parts: list[str] = []

    def walk(node: etree._Element) -> None:
        if not isinstance(node.tag, str):
            return
        if node.tag == 'br':
            parts.append('\n')
        elif node.tag in ('td', 'th'):
            parts.append(' ')
        if node.text and node.tag != 'br':
            parts.append(node.text)
        for child in node:
            walk(child)
            if child.tail:
                parts.append(child.tail)
        if node.tag in ('p', 'div', 'tr', 'li', 'table', 'h1', 'h2', 'h3', 'h4'):
            parts.append('\n')

    walk(element)
    return [' '.join(line.split()) for line in ''.join(parts).split('\n') if line.strip()]


def _valid(link: etree._Element, date: Optional[str]) -> bool:
    """Whether a structure link is in force on ``date`` (JORF links have no dates and always are)."""
    start, end = link.get('debut') or OPEN_END, link.get('fin') or OPEN_END
    if start == OPEN_END and end == OPEN_END:
        return True
    if date is None:
        return (link.get('etat') or 'VIGUEUR').startswith('VIGUEUR') or end == OPEN_END
    return start <= date < end


class DilaParser(Parser):
    """Parses a French text (DILA JORF or LEGI XML) into legalJSON."""

    def __init__(self, date: Optional[str] = None) -> None:
        """``date``: for a consolidated (LEGI) text, the date on which the articles are to be in force."""
        super().__init__()
        self.date = date
        self.files: dict[str, etree._Element] = {}
        self._open_annex: Optional[ChildrenBuilder] = None

    def parse(self, file: str, **options) -> 'DilaParser':
        paths = [file] if os.path.isfile(file) else glob.glob(os.path.join(file, '**', '*.xml'), recursive=True)
        for path in paths:
            try:
                root = etree.parse(path).getroot()
            except (OSError, etree.XMLSyntaxError) as e:
                raise FileLoadError(f"Cannot read DILA XML {path}: {e}") from e
            identifier = root.findtext('.//META_COMMUN/ID') or root.findtext('ID')
            if identifier:
                self.files.setdefault(f'{root.tag}:{identifier}', root)
        version = next((r for k, r in self.files.items() if k.startswith('TEXTE_VERSION:')), None)
        struct = next((r for k, r in self.files.items() if k.startswith('TEXTELR:')), None)
        if version is None or struct is None:
            raise FileLoadError(f"{file} holds no DILA text (TEXTE_VERSION and TEXTELR)")
        self._read_version(version)
        self._read_structure(struct)
        return self

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _file(self, tag: str, identifier: str) -> Optional[etree._Element]:
        return self.files.get(f'{tag}:{identifier}')

    def _read_version(self, version: etree._Element) -> None:
        self.preface = (version.findtext('.//TITREFULL') or version.findtext('.//TITRE') or '').strip() or None
        visas = _lines(version.find('VISAS/CONTENU'))
        formula: list[str] = []
        citations: list[str] = []
        for line in visas:
            if re.match(r'^(Vu |Considérant|Sur le rapport|Sur la proposition|Après avis|Le Conseil d.[ÉE]tat)',
                        line) or citations:
                if re.search(r'(décrète|arrête|ordonne|adopté|promulgue la loi dont la teneur suit)\s*:?$', line,
                             re.IGNORECASE) and not line.startswith('Vu '):
                    self.preamble_final = line
                elif line.startswith('Sur ') and not citations:
                    formula.append(line)
                else:
                    citations.append(line)
            elif re.search(r'(décrète|arrête|ordonne|promulgue la loi dont la teneur suit)\s*:?$', line,
                           re.IGNORECASE):
                self.preamble_final = line
            else:
                formula.append(line)
        self.formula = ' '.join(formula) or None
        self.citations = [{'eId': f'cit_{n}', 'text': text} for n, text in enumerate(citations, start=1)]
        signatures = _lines(version.find('SIGNATAIRES/CONTENU'))
        if signatures:
            self.conclusions = {'conclusion_text': signatures[0], 'signature': ' '.join(signatures[1:]) or None}

    def _read_structure(self, struct: etree._Element) -> None:
        body = BodyBuilder()
        self._walk(struct.find('STRUCT'), body, depth=0, annex=None)
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        last = self.articles[-1]['children'] if self.articles else []
        if last and _CLOSING_FORMULA.match(last[-1]['text']):
            # 'La présente loi sera exécutée comme loi de l'Etat.' closes the act, not its last article
            formula = last.pop()['text']
            conclusions = self.conclusions or {'conclusion_text': None, 'signature': None}
            conclusions['conclusion_text'] = ' '.join(filter(None, [formula, conclusions['conclusion_text']]))
            self.conclusions = conclusions

    def _walk(self, container: Optional[etree._Element], body: BodyBuilder, depth: int,
              annex: Optional[ChildrenBuilder]) -> None:
        if container is None:
            return
        for link in container:
            if not isinstance(link.tag, str) or not _valid(link, self.date):
                continue
            if link.tag == 'LIEN_ART':
                self._article(link, body, annex)
            elif link.tag == 'LIEN_SECTION_TA':
                section = self._file('SECTION_TA', link.get('id'))
                title = ' '.join((link.text or (section.findtext('TITRE_TA') if section is not None else '') or '')
                                 .split())
                inner = section.find('STRUCTURE_TA') if section is not None else None
                if re.match(r'^Annexes?\b', title, re.IGNORECASE):
                    builder = ChildrenBuilder()
                    self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': title, 'heading': None,
                                         'children': builder.children})
                    self._walk(inner, body, depth + 1, builder)
                    continue
                if annex is not None:
                    annex.add(title)
                    self._walk(inner, body, depth + 1, annex)
                    continue
                match = _DIVISION.match(title)
                ordinal = None if match else _ORDINAL_DIVISION.match(title)
                number = ORDINALS.get(_plain(ordinal.group('num'))) if ordinal else None
                if number:
                    kind = ordinal.group('kind').lower()
                    body.division(DIVISIONS[kind], title.split(':')[0].strip(), heading=ordinal.group('heading'),
                                  token=str(number), rank=RANKS[kind])
                    self._walk(inner, body, depth + 1, None)
                    continue
                kind = match.group('kind').lower() if match else ''
                num = f"{match.group('kind')} {match.group('num')}".strip() if match else title
                heading = (match.group('heading') or None) if match else None
                body.division(DIVISIONS.get(kind, 'chapter'), num, heading=heading,
                              token=re.sub(r'\W', '', match.group('num')) or None if match else None,
                              rank=RANKS.get(kind, 9) if match else 9 + depth)
                self._walk(inner, body, depth + 1, None)

    def _article(self, link: etree._Element, body: BodyBuilder, annex: Optional[ChildrenBuilder]) -> None:
        article = self._file('ARTICLE', link.get('id'))
        lines = _lines(article.find('BLOC_TEXTUEL/CONTENU')) if article is not None else []
        number = (link.get('num') or (article.findtext('.//META_ARTICLE/NUM') if article is not None else '')
                  or '').strip()
        if annex is None and not number and lines and re.match(r'^ANNEXES?\b', lines[0], re.IGNORECASE):
            # An annex printed as an unnumbered article (loi 2025-1403, the report on the forecasts)
            self._open_annex = ChildrenBuilder()
            heading = lines[1] if len(lines) > 1 and len(lines[1]) < 400 else None
            self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': lines[0], 'heading': heading,
                                 'children': self._open_annex.children})
            lines = lines[2 if heading else 1:]
            annex = self._open_annex
        elif annex is None and not number and self._open_annex is not None:
            # ... continued in the unnumbered articles after it
            annex = self._open_annex
        elif number:
            self._open_annex = None
        if annex is not None:
            for line in lines:
                annex.add(line)
            return
        children = ChildrenBuilder()
        paragraphs = False
        quoting = 0
        last_act: Optional[str] = None
        for line in lines:
            if quoting or (line.startswith('«') and children.children):
                current = children.children[-1]
                if current.get('amendment') is not None and line.strip('«» '):
                    current['amendment']['quoted'].append({'kind': 'text', 'text': line.strip('«» ')})
                children.extend(line)
                quoting = max(quoting + line.count('«') - line.count('»'), 0)
                continue
            match = _PARAGRAPH.match(line)
            if match:
                paragraphs = True
                child = children.add(line, number=match.group('num'))
            elif children.children and (_POINT.match(line) or paragraphs):
                children.extend(line)
                quoting = max(line.count('«') - line.count('»'), 0)
                continue
            else:
                child = children.add(line)
            action = amendment_action(line)
            if action:
                found = _ACT.search(line)
                last_act = found.group(1).strip() if found else last_act
                child['amendment'] = {'action': action, 'instruction': line, 'amended_act': last_act, 'quoted': []}
            quoting = max(line.count('«') - line.count('»'), 0)
        num = f'Article {number}' if number and not number.lower().startswith('article') else (number or None)
        token = re.sub(r'[^\w-]', '-', number.replace(' ', '-')).strip('-') if number else None
        body.article(num, None, children.children, token=token or None)
