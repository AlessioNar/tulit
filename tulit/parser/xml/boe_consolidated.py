"""
Parser for Spanish legislation from the BOE consolidated-legislation API.

The API returns an act as blocks (``bloque``): the preamble, headings
(títulos, capítulos, secciones), provisions (articles and additional,
transitional, repealing and final provisions) and the signature. Every
block keeps each of its versions (``version``) with the date it applies
from (``fecha_vigencia``) and the act that introduced it (``id_norma``), so
one document yields:

- the consolidated text on any date: per block, the latest version applying
  on or before that date;
- the original text: per block, the version introduced by the act itself
  (blocks added later by other acts are left out).

Editorial notes on amendments (``blockquote``) and footnotes are left out.
"""
import datetime
import os
import re
from typing import Any, Optional

from lxml import etree

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder, element_text

TEXT_FILE = 'texto.xml'
METADATA_FILE = 'metadatos.xml'

HEADINGS = {'libro': 'part', 'titulo': 'title', 'capitulo': 'chapter', 'seccion': 'section',
            'subseccion': 'subsection'}
SKIP_CLASSES = ('nota_pie', 'nota_pie_2', 'siempreSeVe')
_NUMBERED = re.compile(r'^(\d+(?:\s?(?:bis|ter|quater))?)\.\s')
_PREAMBLE_HEADING = re.compile(r'^(PREÁMBULO|EXPOSICIÓN DE MOTIVOS)$', re.IGNORECASE)


def _text(element: etree._Element) -> str:
    return element_text(element, ('p', 'blockquote', 'table', 'tr', 'td'), ('blockquote',))


class BOEConsolidatedParser(Parser):
    """
    Parses a BOE consolidated-legislation download into legalJSON.

    Parameters
    ----------
    version : str
        'consolidated' (default) or 'original'.
    date : str, optional
        ISO date of the consolidated version; defaults to today.
    """

    def __init__(self, version: str = 'consolidated', date: Optional[str] = None) -> None:
        super().__init__()
        self.version = version
        self.date = (date or datetime.date.today().isoformat()).replace('-', '')
        self.metadata: dict[str, Optional[str]] = {}
        self.act_id: Optional[str] = None

    def parse(self, file: str, **options) -> 'BOEConsolidatedParser':
        folder = file if os.path.isdir(file) else os.path.dirname(file)
        text_file = os.path.join(folder, TEXT_FILE) if os.path.isdir(file) else file
        try:
            self.root = etree.parse(text_file).getroot()
        except (OSError, etree.XMLSyntaxError) as e:
            raise FileLoadError(f"Cannot read BOE document {text_file}: {e}") from e
        metadata_file = os.path.join(folder, METADATA_FILE)
        if os.path.exists(metadata_file):
            meta = etree.parse(metadata_file).getroot().find('.//metadatos')
            if meta is not None:
                self.metadata = {c.tag: (c.text or '').strip() or None for c in meta if isinstance(c.tag, str)}
        self.act_id = self.metadata.get('identificador') or self._guess_act_id()

        self.get_preface()
        body = BodyBuilder()
        for block in self.root.iter('bloque'):
            version = self._select(block)
            if version is None:
                continue
            kind = block.get('tipo')
            if kind == 'preambulo':
                self._read_preamble(version)
            elif kind == 'encabezado':
                self._read_heading(block, version, body)
            elif kind == 'precepto':
                self._read_provision(block, version, body)
            elif kind == 'firma':
                self._read_signature(version)
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        return self

    def get_preface(self) -> Optional[str]:
        self.preface = self.metadata.get('titulo')
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _guess_act_id(self) -> Optional[str]:
        counts: dict[str, int] = {}
        for version in self.root.iter('version'):
            norm = version.get('id_norma')
            if norm:
                counts[norm] = counts.get(norm, 0) + 1
        return max(counts, key=counts.get) if counts else None

    def _select(self, block: etree._Element) -> Optional[etree._Element]:
        versions = block.findall('version')
        if self.version == 'original':
            own = [v for v in versions if v.get('id_norma') == self.act_id]
            return own[0] if own else None
        applicable = [v for v in versions if (v.get('fecha_vigencia') or '') <= self.date]
        return max(applicable, key=lambda v: v.get('fecha_vigencia') or '') if applicable else None

    @staticmethod
    def _paragraphs(version: etree._Element):
        for p in version:
            if isinstance(p.tag, str) and p.tag != 'blockquote' and p.get('class') not in SKIP_CLASSES:
                text = _text(p)
                if text:
                    yield p.get('class') or '', text

    def _read_preamble(self, version: etree._Element) -> None:
        formula, recitals, in_preamble = [], [], False
        for _, text in self._paragraphs(version):
            if not in_preamble and _PREAMBLE_HEADING.match(text):
                in_preamble = True
            elif in_preamble:
                recitals.append(text)
            else:
                formula.append(text)
        if not in_preamble and len(formula) > 4:
            # No 'PREÁMBULO' heading: keep the royal formula, the rest is the preamble
            formula, recitals = formula[:4], formula[4:]
        self.formula = ' '.join(formula) or None
        self.recitals = [{'eId': f'rct_{n}', 'text': t} for n, t in enumerate(recitals, start=1)]

    def _read_heading(self, block: etree._Element, version: etree._Element, body: BodyBuilder) -> None:
        number = heading = kind = None
        for cls, text in self._paragraphs(version):
            prefix = cls.split('_')[0]
            if prefix in HEADINGS:
                kind = kind or HEADINGS[prefix]
                if cls.endswith('_tit'):
                    heading = text
                elif cls.endswith('_num'):
                    number = text
                else:  # 'Sección 1.ª Disposiciones generales' in a single paragraph
                    match = re.match(r'^(\S+\s+\S+)\s+(.*)$', text)
                    number, heading = (match.group(1), match.group(2)) if match else (text, None)
        if kind is None:
            return
        title = block.get('titulo') or number or ''
        token = (re.search(r'\b([0-9]+|[IVXLCDM]+)\b', title) or [None, None])[1]
        body.division(kind, number or title, heading=heading, token=token)

    def _read_provision(self, block: etree._Element, version: etree._Element, body: BodyBuilder) -> None:
        num = block.get('titulo')
        heading, children = None, ChildrenBuilder()
        for cls, text in self._paragraphs(version):
            if cls == 'articulo' and heading is None and not children.children:
                heading = _strip_number(text, num)
                continue
            match = _NUMBERED.match(text)
            if match and cls.startswith('parrafo'):
                children.add(text, number=match.group(1).replace(' ', ''))
            elif children.children and (cls.startswith('sangrado') or cls.startswith('parrafo')):
                children.extend(text)
            else:
                children.add(text)
        article_match = re.match(r'^Artículo\s+(\S+(?:\s+(?:bis|ter|quater))?)$', num or '')
        token = article_match.group(1).replace(' ', '-') if article_match else block.get('id')
        if not article_match:
            # Additional, transitional, repealing and final provisions follow the
            # last title or chapter and do not belong to it
            body.close_divisions()
        body.article(num, heading, children.children, token=token)

    def _read_signature(self, version: etree._Element) -> None:
        lines = list(self._paragraphs(version))
        # Signatories: the King, then each minister's office followed by their name
        signatories: list[str] = []
        for cls, text in lines:
            if not cls.startswith('firma'):
                continue
            if signatories and signatories[-1].endswith(','):
                signatories[-1] = f'{signatories[-1]} {text}'
            else:
                signatories.append(text)
        place_date = None
        for cls, text in lines:
            place_date = (re.match(r'^(?:Dado en )?([^,]+), (?:(?:el|a) )?(\d{1,2} de \w+ de \d{4})\.?$', text)
                          if not cls.startswith('firma') else None)
            if place_date:
                break
        self.conclusions = {
            'conclusion_text': ' '.join(text for _, text in lines),
            'signature': {
                'place': place_date.group(1) if place_date else None,
                'date': place_date.group(2) if place_date else None,
                'signatory': signatories[0] if signatories else None,
                'title': None,
                'signatories': signatories,
            },
        }


def _strip_number(text: str, num: Optional[str]) -> Optional[str]:
    """'Artículo 3. Datos de las personas fallecidas.' -> 'Datos de las personas fallecidas'."""
    if num and text.startswith(num):
        text = text[len(num):]
    return text.strip(' .') or None
