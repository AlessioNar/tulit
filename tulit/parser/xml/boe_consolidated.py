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
import unicodedata
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
# 'Uno. Se modifica el artículo 5...': the amendments of an amending provision
_ORDINAL = re.compile(r'^((?:Uno|Dos|Tres|Cuatro|Cinco|Seis|Siete|Ocho|Nueve|Diez|Once|Doce|Trece|Catorce|Quince|'
                      r'Dieci\w+|Veinte|Veinti\w+|(?:Treinta|Cuarenta|Cincuenta|Sesenta|Setenta|Ochenta|Noventa)'
                      r'(?: y \w+)?|Cien(?:to \w+(?: y \w+)?)?))\.\s')
_AMENDING = re.compile(r'^Modificaci[oó]n (?:de (?:la |las |los |el )?|del )(.+?)(?:,| para | en materia |$)')
_ACTIONS = (('suprim', 'delete'), ('derog', 'delete'), ('sin contenido', 'delete'), ('renumera', 'renumber'),
            ('añad', 'insert'), ('introduc', 'insert'), ('inclu', 'insert'), ('incorpor', 'insert'),
            ('adiciona', 'insert'), ('sustitu', 'substitute'), ('modific', 'replace'), ('redact', 'replace'),
            ('redacción', 'replace'))
# 'Madrid, 5 de diciembre de 2018.', 'Dado en Madrid, el 21 de diciembre de 2007.', 'Dado el 14 de octubre de 2026.'
_PLACE_DATE = re.compile(r'^(?:Dado (?:en )?)?(?:([^,]+), )?(?:(?:el|a) )?(\d{1,2} de \w+ de \d{4})\.?$')
_SINGLE = re.compile(r'^(Se|El|La|Los|Las)\s')
_PREAMBLE_HEADING = re.compile(r'^(PREÁMBULO|EXPOSICIÓN DE MOTIVOS)$', re.IGNORECASE)
_DIVISION = re.compile(r'^(libro|t[ií]tulo|cap[ií]tulo|secci[oó]n|subsecci[oó]n|§)', re.IGNORECASE)
_SUFFIX = r'(?:\s+(?:bis|ter|qu[aá]ter|quinquies|sexies|septies|octies|nonies|decies))?'
# 'Artículo 340 quater', 'Art 1', 'Art. 1863 bis' (the Civil Code abbreviates its block titles)
_ARTICLE = re.compile(r'^Art(?:ículo|\.)?\s+(\d+' + _SUFFIX + r')\.?$')
# 'Artículos 617 a 622', 'Arts 307 al 313': articles repealed together in one block
_ARTICLES = re.compile(r'^Art(?:ículo)?s?\.?\s+(\d+' + _SUFFIX + r')\s+(?:a|al|y)\s+(\d+' + _SUFFIX + r')\.?$',
                       re.IGNORECASE)


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
        self.start = ''

    def parse(self, file: str, **options) -> 'BOEConsolidatedParser':
        folder = file if os.path.isdir(file) else os.path.dirname(file)
        text_file = os.path.join(folder, TEXT_FILE) if os.path.isdir(file) else file
        try:
            self.root = etree.parse(text_file).getroot()
        except (OSError, etree.XMLSyntaxError) as e:
            raise FileLoadError(f"Cannot read BOE document {text_file}: {e}") from e
        metadata_file = os.path.join(folder, METADATA_FILE)
        if self.root.tag == 'documento':
            # The act as published in the gazette (diario_boe/xml.php): one flat text
            meta = self.root.find('metadatos')
            self.metadata = {c.tag: (c.text or '').strip() or None for c in meta if isinstance(c.tag, str)} \
                if meta is not None else {}
            self.root = _gazette_blocks(self.root, self.metadata)
        elif os.path.exists(metadata_file):
            meta = etree.parse(metadata_file).getroot().find('.//metadatos')
            if meta is not None:
                self.metadata = {c.tag: (c.text or '').strip() or None for c in meta if isinstance(c.tag, str)}
        self.act_id = self.metadata.get('identificador') or self._guess_act_id()
        own_dates = [v.get('fecha_vigencia') or '' for v in self.root.iter('version')
                     if v.get('id_norma') == self.act_id]
        self.start = min(own_dates) if own_dates else ''

        self.get_preface()
        body = BodyBuilder()
        for block in self.root.iter('bloque'):
            version = self._select(block)
            if version is None:
                continue
            kind = block.get('tipo')
            first = version.find('p')
            if kind in ('encabezado', 'precepto') and first is not None and first.get('class') == 'anexo_num':
                self._read_annex(list(self._paragraphs(version)))
            elif kind == 'preambulo':
                self._read_preamble(version)
            elif kind == 'encabezado':
                self._read_heading(block, version, body)
            elif kind == 'precepto' and _is_heading(version):
                # Some headings are filed as provisions ('Sección segunda', 'TÍTULO X')
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
            if own:
                return own[0]
            # A block first published by a correction of errors applying from the start
            first = min(versions, key=lambda v: v.get('fecha_vigencia') or '', default=None)
            return first if first is not None and (first.get('fecha_vigencia') or '') <= self.start else None
        if (block.get('fecha_caducidad') or '99999999') <= self.date:
            return None  # the block was repealed or replaced by then
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
        if not in_preamble:
            # No 'PREÁMBULO' heading: the royal formula ends with 'Sabed: ...'; decrees have none
            end = next((n for n, text in enumerate(formula) if re.match(r'^sabed\b', text, re.IGNORECASE)), -1)
            formula, recitals = formula[:end + 1], formula[end + 1:]
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
                elif not _DIVISION.match(text):  # 'Disposiciones generales', 'REGLAMENTO DE DESARROLLO ...'
                    number, heading = None, text
                else:  # 'Sección 1.ª Disposiciones generales' in a single paragraph
                    match = re.match(r'^(\S+\s+\S+)\s+(.*)$', text)
                    number, heading = (match.group(1).rstrip('.:'), match.group(2)) if match else (text, None)
        if kind is None:
            return
        title = number or ''
        token = (re.search(r'\b([0-9]+|[IVXLCDM]+)\b', title) or [None, None])[1]
        body.division(kind, number, heading=heading, token=token)

    def _read_annex(self, paragraphs: list[tuple[str, str]]) -> None:
        number = heading = None
        children = ChildrenBuilder()
        for cls, text in paragraphs:
            if cls == 'anexo_num':
                number = text
            elif cls == 'anexo_tit' and heading is None and not children.children:
                heading = text
            else:
                children.add(text)
        self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': number, 'heading': heading,
                             'children': children.children})

    def _read_provision(self, block: etree._Element, version: etree._Element, body: BodyBuilder) -> None:
        num = (block.get('titulo') or '').strip() or None
        token = None
        article_match = _ARTICLE.match(num or '')
        articles_match = _ARTICLES.match(num or '')
        if article_match:
            token = _token(article_match.group(1))
            num = f'Artículo {article_match.group(1)}'
        elif articles_match:
            token = f'{_token(articles_match.group(1))}-{_token(articles_match.group(2))}'
            num = f'Artículos {articles_match.group(1)} a {articles_match.group(2)}'
        heading, children = None, ChildrenBuilder()
        depth = 0  # open quotation marks: text an amending provision inserts
        for cls, text in self._paragraphs(version):
            if cls == 'articulo' and heading is None and not children.children:
                heading = _strip_number(text, num, block.get('titulo'))
                continue
            match = _NUMBERED.match(text) or _ORDINAL.match(text)
            if (depth > 0 or text.startswith('«')) and children.children:
                children.extend(text)
            elif match and cls.startswith('parrafo'):
                number = match.group(1).replace(' ', '').lower()
                children.add(text, number=number, token=None if number[0].isdigit() else number)
            elif children.children and (cls.startswith('sangrado') or cls.startswith('parrafo')):
                children.extend(text)
            else:
                children.add(text)
            depth = max(0, depth + text.count('«') - text.count('»'))
        _mark_amendments(heading, children.children)
        if token is None:
            token = block.get('id')
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
            place_date = _PLACE_DATE.match(text) if not cls.startswith('firma') else None
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


def _strip_number(text: str, *nums: Optional[str]) -> Optional[str]:
    """'Artículo 3. Datos de las personas fallecidas.' -> 'Datos de las personas fallecidas'."""
    for num in nums:
        num = (num or '').strip()
        if num and text.startswith(num):
            text = text[len(num):]
            break
    else:
        match = re.match(r'^Art(?:ículo|\.)?s?\s+\d+(?:\s+(?:a|al|y)\s+\d+)?' + _SUFFIX + r'(?=[.\s]|$)', text)
        if match:
            text = text[match.end():]
    return text.strip(' .') or None


def _token(number: str) -> str:
    """'340 quáter' -> '340-quater'."""
    return number.replace('á', 'a').replace(' ', '-')


def _is_heading(version: etree._Element) -> bool:
    classes = [p.get('class') or '' for p in version if isinstance(p.tag, str) and p.tag == 'p']
    return bool(classes) and all(c.split('_')[0] in HEADINGS for c in classes)


_SIGNATURE_LINE = re.compile(r'^(Dado en .+|Dado el .+|[A-ZÁÉÍÓÚ][\w ]+, (?:a )?\d{1,2} de \w+ de \d{4}\.?)$')


def _gazette_blocks(document: etree._Element, metadata: dict[str, Optional[str]]) -> etree._Element:
    """
    Cut the flat text of a gazette XML into the blocks of the consolidated
    format, each with one version introduced by the act itself: the preamble,
    headings, provisions (from an 'articulo' paragraph), annexes and the
    signature. Text quoted by an amending provision (between « and ») stays
    in that provision.
    """
    act = metadata.get('identificador') or ''
    date = metadata.get('fecha_vigencia') or metadata.get('fecha_publicacion') or ''
    root = etree.Element('texto')
    version: Optional[etree._Element] = None

    def start(kind: str, title: str = '') -> etree._Element:
        block = etree.SubElement(root, 'bloque', tipo=kind, titulo=title)
        return etree.SubElement(block, 'version', id_norma=act, fecha_vigencia=date)

    texto = document.find('texto')
    used: set[str] = set()
    depth = 0  # open quotation marks
    for p in list(texto if texto is not None else []):
        if not isinstance(p.tag, str):
            continue
        if p.tag == 'blockquote':
            p.tag = 'cita'  # text quoted by an amending provision, not an editorial note as in the consolidated text
        cls = p.get('class') or ''
        text = ' '.join(''.join(p.itertext()).split())
        prefix = cls.split('_')[0]
        if (depth > 0 or text.startswith('«')) and version is not None:
            pass  # quoted by the provision
        elif cls == 'articulo':
            title = text.split('.')[0].strip()
            version = start('precepto', title)
            version.getparent().set('id', _block_id(title, used))
        elif cls.startswith('firma') or _SIGNATURE_LINE.match(text):
            if version is None or version.getparent().get('tipo') != 'firma':
                version = start('firma')
        elif cls == 'anexo_num' or (cls == 'anexo' and re.match(r'^ANEXO\b', text, re.IGNORECASE)):
            p.set('class', 'anexo_num')
            version = start('encabezado', text)
        elif prefix in HEADINGS or cls == 'anexo':
            parent = version.getparent() if version is not None else None
            if not (cls.endswith('_tit') and parent is not None and parent.get('tipo') == 'encabezado'):
                version = start('encabezado', text)
        elif version is None:
            version = start('preambulo')
        version.append(p)
        depth = max(0, depth + text.count('«') - text.count('»'))
    return root


def _block_id(title: str, used: set[str]) -> str:
    """Block ids as the consolidated format has them: 'Disposición final primera' -> 'df-primera'."""
    words = unicodedata.normalize('NFKD', title.lower()).encode('ascii', 'ignore').decode().split()
    if len(words) > 2 and words[0] == 'disposicion':
        block_id = f"d{words[1][0]}-{'-'.join(words[2:])}"
    else:
        block_id = '-'.join(words[1:] if words[:1] == ['articulo'] else words) or 'precepto'
    base, n = block_id, 2
    while block_id in used:
        block_id, n = f'{base}-{n}', n + 1
    used.add(block_id)
    return block_id


def _mark_amendments(heading: Optional[str], children: list[dict[str, Any]]) -> None:
    """
    In a provision amending another act ('Modificación de la Ley ...'), each
    numbered point ('Uno. Se modifica el artículo 5, que queda redactado
    como sigue: «...»') is an amendment: the instruction, then the quoted text.
    """
    match = _AMENDING.match(heading or '')
    if not match:
        return
    for child in children:
        instruction, _, quoted = child['text'].partition('«')
        instruction = instruction.strip()
        lowered = instruction.lower()
        found = [(lowered.find(verb), action) for verb, action in _ACTIONS if verb in lowered]
        action = min(found)[1] if found else None  # the first verb
        quoted = quoted.rsplit('»', 1)[0].strip()
        # 'Uno. Se añade ...', or a single amendment quoting its text ('Se modifica el apartado 5 ...: «...»')
        if action is None or not (re.match(r'^\w+\.\s', instruction) or (quoted and _SINGLE.match(instruction))):
            continue
        child['amendment'] = {'action': action, 'instruction': instruction, 'amended_act': match.group(1).strip(),
                              'quoted': [{'kind': 'text', 'text': quoted}] if quoted else []}
