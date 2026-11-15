"""
legalJSON to Akoma Ntoso 3.0.

The document becomes an ``<act>``: the metadata becomes its FRBR
identification, the preface its long title, the preamble its formula,
citations, recitals and final formula, the divisions and articles its body
(nested as in ``structure``), the conclusions its closing text and
signatures, and each annex an attachment of its own. Structured amendments
become ``<mod>`` elements quoting their new text (``quotedText`` or
``quotedStructure``), listed as textual modifications in the metadata.

The output validates against the Akoma Ntoso 3.0 schema bundled with tulit
(``tulit/parser/xml/assets/akomantoso30.xsd``)::

    >>> from tulit.exporters import to_akn
    >>> xml = to_akn(tulit.fetch('32024R0903'))
"""
import datetime
import re
from pathlib import Path
from typing import Any, Optional

from lxml import etree

AKN = 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0'
TULIT = 'https://github.com/AlessioNar/tulit'
SCHEMA = Path(__file__).resolve().parent.parent / 'parser' / 'xml' / 'assets' / 'akomantoso30.xsd'

# legalJSON division types that are Akoma Ntoso hierarchy elements; others become <hcontainer name=type>
HIERARCHY = {'book', 'part', 'title', 'chapter', 'section', 'subsection', 'division', 'subtitle'}
# legalJSON amendment actions and the Akoma Ntoso textual modification types
MODIFICATIONS = {'replace': 'substitution', 'substitute': 'substitution', 'amend': 'substitution',
                 'insert': 'insertion', 'add': 'insertion', 'delete': 'repeal', 'repeal': 'repeal',
                 'renumber': 'renumbering'}
_XML_INVALID = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]')
_DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
_URI = re.compile(r'^[a-zA-Z][a-zA-Z0-9+.-]*:[^\s]+$|^/[^\s]*$')
_UNSAFE = re.compile(r'[^A-Za-z0-9_.~-]+')


def _clean(text: Any) -> str:
    """Text that XML can hold."""
    return _XML_INVALID.sub('', str(text)) if text is not None else ''


def _segment(text: str) -> str:
    """A URI segment: unsafe characters become '-'."""
    return _UNSAFE.sub('-', text).strip('-') or 'x'


def work_number(doc_meta: dict) -> str:
    """
    The act's number in its Akoma Ntoso URIs: its published number, CELEX
    number or identifier, else the path of its ELI or source address.
    """
    for key in ('number', 'celex', 'identifier'):
        if doc_meta.get(key):
            return _segment(str(doc_meta[key]))
    eli = str(doc_meta.get('eli') or '')
    if '/eli/' in eli:
        return _segment(eli.split('/eli/', 1)[1].rstrip('/').replace('/', '-'))
    source = str(doc_meta.get('source') or '').split('?')[0].rstrip('/')
    if source.startswith('http'):
        return _segment(re.sub(r'\.(xml|html?|pdf|json)$', '', source.rsplit('/', 1)[-1]))
    return 'act'


class _Builder:
    """Builds one Akoma Ntoso document; keeps eIds unique across it."""

    def __init__(self) -> None:
        self.ids: set[str] = set()
        self.mods: list[tuple[str, dict]] = []
        self.references: list[tuple[str, str]] = []

    def el(self, parent: Optional[etree._Element], tag: str, text: Optional[str] = None,
           **attrs: Optional[str]) -> etree._Element:
        attributes = {k.rstrip('_'): v for k, v in attrs.items() if v is not None}
        if 'eId' in attributes:
            attributes['eId'] = self.eid(attributes['eId'])
        element = (etree.SubElement(parent, f'{{{AKN}}}{tag}', attributes) if parent is not None
                   else etree.Element(f'{{{AKN}}}{tag}', attributes, nsmap={None: AKN, 'tulit': TULIT}))
        if text:
            element.text = _clean(text)
        return element

    def eid(self, value: str) -> str:
        """A unique eId: no spaces, and '_2', '_3'... added to repeats."""
        value = re.sub(r'\s+', '_', _clean(value)) or 'x'
        if value[0].isdigit() or value[0] in '-.':
            value = f'x{value}'
        unique, n = value, 1
        while unique in self.ids:
            n += 1
            unique = f'{value}_{n}'
        self.ids.add(unique)
        return unique


def _identification(b: _Builder, meta: etree._Element, doc_meta: dict, component: Optional[str] = None) -> None:
    """FRBR Work, Expression and Manifestation from the legalJSON metadata."""
    country = (doc_meta.get('jurisdiction') or 'eu').lower()
    language = doc_meta.get('language') or 'und'
    work_date = next((doc_meta[k] for k in ('date_document', 'date_publication', 'version_date')
                      if doc_meta.get(k) and _DATE.match(str(doc_meta[k]))), None)
    version_date = doc_meta.get('version_date') if _DATE.match(str(doc_meta.get('version_date') or '')) else None
    number = work_number(doc_meta)
    work = f"/akn/{country}/act/{work_date or 'unknown'}/{_segment(str(number))}"
    expression = f"{work}/{language}@{version_date or ''}"
    manifestation = f"{expression}/!{component or 'main'}.xml"
    this = f'/!{component}' if component else '/!main'

    identification = b.el(meta, 'identification', source='#tulit')
    frbr = b.el(identification, 'FRBRWork')
    b.el(frbr, 'FRBRthis', value=work + this)
    b.el(frbr, 'FRBRuri', value=work)
    if doc_meta.get('eli') and _URI.match(doc_meta['eli']):
        b.el(frbr, 'FRBRalias', value=doc_meta['eli'], name='ELI')
    if doc_meta.get('celex'):
        b.el(frbr, 'FRBRalias', value=doc_meta['celex'], name='CELEX')
    b.el(frbr, 'FRBRdate', date=work_date or '0001-01-01', name='adoption' if work_date else 'unknown')
    b.el(frbr, 'FRBRauthor', href='#author')
    b.el(frbr, 'FRBRcountry', value=country)
    if number:
        b.el(frbr, 'FRBRnumber', value=_clean(number))

    frbr = b.el(identification, 'FRBRExpression')
    b.el(frbr, 'FRBRthis', value=expression + this)
    b.el(frbr, 'FRBRuri', value=expression)
    b.el(frbr, 'FRBRdate', date=version_date or work_date or '0001-01-01',
         name=doc_meta.get('version') or 'version')
    b.el(frbr, 'FRBRauthor', href='#author')
    b.el(frbr, 'FRBRlanguage', language=language)

    frbr = b.el(identification, 'FRBRManifestation')
    b.el(frbr, 'FRBRthis', value=manifestation)
    b.el(frbr, 'FRBRuri', value=manifestation)
    b.el(frbr, 'FRBRdate', date=datetime.date.today().isoformat(), name='transform')
    b.el(frbr, 'FRBRauthor', href='#tulit')


def _references(b: _Builder, meta: etree._Element, doc_meta: dict) -> etree._Element:
    references = b.el(meta, 'references', source='#tulit')
    b.el(references, 'TLCOrganization', eId='tulit', href='/ontology/organization/tulit', showAs='tulit')
    country = (doc_meta.get('jurisdiction') or 'eu').lower()
    b.el(references, 'TLCOrganization', eId='author', href=f'/ontology/organization/{country}/legislator',
         showAs='Legislator')
    return references


def _cited_acts(b: _Builder, references: etree._Element) -> None:
    """References for the amended acts cited (not linked) by textual modifications."""
    for eid, citation in b.references:
        references.append(etree.Element(f'{{{AKN}}}TLCReference', eId=eid, name='amendedAct',
                                        href=f'/ontology/act/{_segment(citation)[:80]}', showAs=citation))
    b.references = []


def _proprietary(b: _Builder, meta: etree._Element, doc_meta: dict) -> None:
    """The legalJSON metadata that FRBR does not hold, kept as is."""
    proprietary = b.el(meta, 'proprietary', source='#tulit')
    holder = etree.SubElement(proprietary, f'{{{TULIT}}}meta')
    for key, value in doc_meta.items():
        if value is None or isinstance(value, (dict,)):
            continue
        for item in (value if isinstance(value, list) else [value]):
            field = etree.SubElement(holder, f'{{{TULIT}}}field', name=key)
            field.text = _clean(item)


def _blocks(b: _Builder, parent: etree._Element, child: dict, eid: Optional[str] = None) -> None:
    """The text of a legalJSON child as paragraphs, a table, or an amendment."""
    amendment = child.get('amendment')
    if amendment:
        _mod(b, b.el(parent, 'p'), child, amendment, eid)
        return
    table = child.get('table')
    rows = [row for row in (table or {}).get('rows') or [] if any(cell for cell in row)]
    if child.get('text') and not rows:
        b.el(parent, 'p', child.get('text'))
    if rows:
        element = b.el(parent, 'table', eId=f'{eid}__table_1' if eid else b.eid('table'))
        if table.get('caption'):
            b.el(element, 'caption', table['caption'])
        for row in rows:
            tr = b.el(element, 'tr')
            for cell in row:
                b.el(b.el(tr, 'td'), 'p', cell)
        for note in table.get('notes') or []:
            b.el(parent, 'p', note if isinstance(note, str) else note.get('text'), class_='note')
    if not len(parent):
        b.el(parent, 'p')


def _mod(b: _Builder, p: etree._Element, child: dict, amendment: dict, eid: Optional[str]) -> None:
    """
    An amendment as a <mod>: the paragraph's whole text, its quoted new text
    marked where it stands (quotedText), quoted structures after it. The
    legalJSON action and instruction are kept as tulit attributes.
    """
    mod = b.el(p, 'mod', eId=f'{eid}__mod_1' if eid else 'mod')
    mod.set(f'{{{TULIT}}}action', amendment.get('action') or '')
    mod.set(f'{{{TULIT}}}instruction', _clean(amendment.get('instruction')))
    text = _clean(child.get('text') or amendment.get('instruction') or '')
    last: Optional[etree._Element] = None
    cursor = 0

    def put(segment: str) -> None:
        if not segment:
            return
        if last is None:
            mod.text = (mod.text or '') + segment
        else:
            last.tail = (last.tail or '') + segment

    for quoted in amendment.get('quoted') or []:
        if quoted.get('kind') == 'structure':
            continue
        quote = _clean(quoted.get('text'))
        at = text.find(quote, cursor) if quote else -1
        if at < 0:
            continue
        put(text[cursor:at])
        last = b.el(mod, 'quotedText', quote)
        cursor = at + len(quote)
    put(text[cursor:])
    for quoted in amendment.get('quoted') or []:
        if quoted.get('kind') == 'structure':
            structure = b.el(mod, 'quotedStructure')
            structure.set(f'{{{TULIT}}}appended', 'true')
            for item in quoted.get('children') or []:
                _blocks(b, structure, {'text': item.get('text'), 'table': item.get('table')})
            if not len(structure):
                b.el(structure, 'p')
        elif _clean(quoted.get('text')) and _clean(quoted.get('text')) not in text:
            b.el(mod, 'quotedText', quoted.get('text')).set(f'{{{TULIT}}}appended', 'true')
    b.mods.append((mod.get('eId'), amendment))


def _article(b: _Builder, parent: etree._Element, article: dict) -> None:
    element = b.el(parent, 'article', eId=article.get('eId') or 'art')
    eid = element.get('eId')
    if article.get('num'):
        b.el(element, 'num', article['num'])
    if article.get('heading'):
        b.el(element, 'heading', article['heading'])
    children = article.get('children') or []
    if not children:
        b.el(element, 'content')
        b.el(element[-1], 'p')
    for child in children:
        paragraph = b.el(element, 'paragraph', eId=f"{eid}__{_paragraph_eid(child.get('eId'))}")
        _blocks(b, b.el(paragraph, 'content'), child, paragraph.get('eId'))


def _paragraph_eid(eid: Optional[str]) -> str:
    """legalJSON paragraph eIds in the Akoma Ntoso naming convention: par_2 -> para_2."""
    return re.sub(r'^par_', 'para_', eid or 'unp')


def _division(b: _Builder, parent: etree._Element, division: dict) -> etree._Element:
    kind = division.get('type') or 'division'
    tag = kind if kind in HIERARCHY else 'hcontainer'
    element = b.el(parent, tag, eId=division.get('eId') or kind, name=kind if tag == 'hcontainer' else None)
    if division.get('num'):
        b.el(element, 'num', division['num'])
    if division.get('heading'):
        b.el(element, 'heading', division['heading'])
    return element


def _body(b: _Builder, act: etree._Element, doc: dict) -> None:
    body = b.el(act, 'body')
    chapters = {c.get('eId'): c for c in doc.get('chapters') or [] if isinstance(c, dict)}
    articles = [a for a in doc.get('articles') or [] if isinstance(a, dict)]
    by_eid = {}
    for article in articles:
        by_eid.setdefault(article.get('eId'), []).append(article)
    placed_divisions: dict[str, etree._Element] = {}
    placed_articles: set[int] = set()

    def place(node: dict, parent: etree._Element) -> None:
        if node.get('type') == 'article':
            for article in by_eid.get(node.get('eId'), []):
                if id(article) not in placed_articles:
                    placed_articles.add(id(article))
                    _article(b, parent, article)
                    return
            return
        division = chapters.get(node.get('eId')) or node
        element = _division(b, parent, division)
        placed_divisions[node.get('eId')] = element
        for child in node.get('children') or []:
            place(child, element)

    for node in doc.get('structure') or []:
        place(node, body)

    # Divisions and articles the skeleton does not reach go under their parent, in document order
    def parent_of(item: dict) -> etree._Element:
        eid = item.get('parent')
        if eid and eid not in placed_divisions and eid in chapters:
            placed_divisions[eid] = _division(b, parent_of(chapters[eid]), chapters[eid])
        return placed_divisions.get(eid, body)

    for eid, division in chapters.items():
        if eid not in placed_divisions:
            placed_divisions[eid] = _division(b, parent_of(division), division)
    for article in articles:
        if id(article) not in placed_articles:
            placed_articles.add(id(article))
            _article(b, parent_of(article), article)
    if not len(body):
        b.el(b.el(body, 'hcontainer', eId='body', name='body'), 'content')
        b.el(body[0][0], 'p')


def _items(values: Any) -> list[dict]:
    return [v if isinstance(v, dict) else {'text': v} for v in values or [] if v]


def _preamble(b: _Builder, act: etree._Element, preamble: dict) -> None:
    if not any(preamble.get(k) for k in ('formula', 'citations', 'recitals_intro', 'recitals', 'final')):
        return
    element = b.el(act, 'preamble')
    if preamble.get('formula'):
        b.el(b.el(element, 'formula', name='enactingFormula'), 'p', preamble['formula'])
    citations = _items(preamble.get('citations'))
    if citations:
        container = b.el(element, 'citations')
        for n, citation in enumerate(citations, 1):
            b.el(b.el(container, 'citation', eId=citation.get('eId') or f'cit_{n}'), 'p', citation.get('text'))
    recitals = _items(preamble.get('recitals'))
    if recitals or preamble.get('recitals_intro'):
        container = b.el(element, 'recitals')
        if preamble.get('recitals_intro'):
            b.el(b.el(container, 'intro'), 'p', preamble['recitals_intro'])
        for n, recital in enumerate(recitals, 1):
            item = b.el(container, 'recital', eId=recital.get('eId') or f'rct_{n}')
            if recital.get('num'):
                b.el(item, 'num', recital['num'])
            b.el(item, 'p', recital.get('text'))
        if not recitals:
            b.el(b.el(container, 'recital', eId='rct_1'), 'p')
    if preamble.get('final'):
        b.el(element, 'block', preamble['final'], name='preamble.final')


def _conclusions(b: _Builder, act: etree._Element, conclusions: Any) -> None:
    if not conclusions:
        return
    if not isinstance(conclusions, dict):
        conclusions = {'text': conclusions}
    lines: list[tuple[str, str]] = []
    signatures: list[str] = []

    def collect(key: str, value: Any) -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                collect(k, v)
        elif isinstance(value, list):
            for v in value:
                collect(key, v)
        elif value not in (None, ''):
            (signatures if 'signat' in key.lower() else lines).append((key, str(value)))

    for key, value in conclusions.items():
        if 'signat' in key.lower():
            for item in (value if isinstance(value, list) else [value]):
                if isinstance(item, list):
                    signatures.append(' '.join(str(i) for i in item if i))
                elif isinstance(item, dict):
                    signatures.append(' '.join(str(v) for v in item.values() if v))
                elif item:
                    signatures.append(str(item))
        else:
            collect(key, value)
    if not lines and not signatures:
        return
    element = b.el(act, 'conclusions')
    for key, text in lines:
        b.el(element, 'p', text, class_=_segment(key))
    if signatures:
        container = b.el(element, 'container', name='signature')
        for text in signatures:
            b.el(b.el(container, 'p'), 'signature', text)


def _annex_doc(b: _Builder, parent: Optional[etree._Element], doc: dict, n: int, annex: dict,
               name: str = 'annex') -> etree._Element:
    """An annex as an Akoma Ntoso <doc>: its number and title in the preface, its children in the main body."""
    eid = b.eid(annex.get('eId') or f'anx_{n}')
    document = b.el(parent, 'doc', name=name)
    meta = b.el(document, 'meta')
    _identification(b, meta, doc.get('meta') or {}, component=f'annex_{n}')
    if annex.get('num') or annex.get('heading'):
        p = b.el(b.el(document, 'preface'), 'p')
        if annex.get('num'):
            b.el(p, 'docNumber', annex['num']).tail = ' ' if annex.get('heading') else None
        if annex.get('heading'):
            b.el(p, 'docTitle', annex['heading'])
    body = b.el(document, 'mainBody', eId=eid)
    for child in annex.get('children') or []:
        paragraph = b.el(body, 'paragraph', eId=f"{eid}__{_paragraph_eid(child.get('eId'))}")
        _blocks(b, b.el(paragraph, 'content'), child, paragraph.get('eId'))
    if not len(body):
        b.el(body, 'p')
    references = _references(b, meta, doc.get('meta') or {})
    _analysis(b, meta, references)
    _cited_acts(b, references)
    return document


def _annexes(doc: dict) -> list[dict]:
    return [a for a in doc.get('annexes') or [] if isinstance(a, dict)]


def _attachments(b: _Builder, act: etree._Element, doc: dict, files: Optional[list[str]] = None) -> None:
    """The annexes as attachments: inline documents, or references to the files named in ``files``."""
    annexes = _annexes(doc)
    if not annexes:
        return
    container = b.el(act, 'attachments')
    for n, annex in enumerate(annexes, 1):
        attachment = b.el(container, 'attachment', eId=f'att_{n}')
        if files:
            b.el(attachment, 'documentRef', eId=f'att_{n}__ref', href=files[n - 1],
                 showAs=_clean(' '.join(filter(None, (annex.get('num'), annex.get('heading')))) or f'Annex {n}'))
        else:
            mods = b.mods
            b.mods = []
            _annex_doc(b, attachment, doc, n, annex)
            b.mods = mods


def _analysis(b: _Builder, meta: etree._Element, references: etree._Element) -> None:
    """Each <mod> as a textual modification of the act it amends, before the references."""
    if not b.mods:
        return
    analysis = etree.Element(f'{{{AKN}}}analysis', source='#tulit')
    references.addprevious(analysis)
    active = b.el(analysis, 'activeModifications')
    for n, (eid, amendment) in enumerate(b.mods, 1):
        modification = b.el(active, 'textualMod', eId=f'amod_{n}',
                            type=MODIFICATIONS.get(amendment.get('action') or 'amend', 'substitution'))
        b.el(modification, 'source', href=f'#{eid}')
        target = _clean(amendment.get('amended_act'))
        if target and _URI.match(target):
            b.el(modification, 'destination', href=target)
        elif target:
            # A citation, not a URI: a reference that shows it
            reference = b.eid(f'amended_{n}')
            b.el(modification, 'destination', href=f'#{reference}')
            b.references.append((reference, target))
        else:
            b.el(modification, 'destination', href='#unknown')


def to_akn_tree(doc: dict, annex_files: Optional[list[str]] = None) -> etree._ElementTree:
    """
    A legalJSON document as an Akoma Ntoso 3.0 element tree.

    The annexes are attached inline, or, given ``annex_files``, referenced
    by those file names (one per annex) as in a .leg package.
    """
    b = _Builder()
    doc_meta = doc.get('meta') or {}
    root = b.el(None, 'akomaNtoso')
    act = b.el(root, 'act', name=_segment(doc_meta.get('kind') or 'act'))
    meta = b.el(act, 'meta')
    _identification(b, meta, doc_meta)
    references = _references(b, meta, doc_meta)

    if doc.get('preface'):
        b.el(b.el(b.el(b.el(act, 'preface'), 'longTitle'), 'p'), 'docTitle', doc['preface'])
    _preamble(b, act, doc.get('preamble') or {})
    _body(b, act, doc)
    _conclusions(b, act, doc.get('conclusions'))
    _attachments(b, act, doc, annex_files)

    _analysis(b, meta, references)
    _cited_acts(b, references)
    _proprietary(b, meta, doc_meta)
    return etree.ElementTree(root)


def annex_tree(doc: dict, n: int, name: str = 'annex') -> etree._ElementTree:
    """Annex ``n`` (from 1) of a legalJSON document as an Akoma Ntoso document of its own."""
    b = _Builder()
    root = b.el(None, 'akomaNtoso')
    _annex_doc(b, root, doc, n, _annexes(doc)[n - 1], name)
    return etree.ElementTree(root)


def to_akn(doc: dict) -> bytes:
    """A legalJSON document as Akoma Ntoso 3.0 XML (UTF-8 bytes)."""
    return serialize(to_akn_tree(doc))


def serialize(tree: etree._ElementTree) -> bytes:
    return etree.tostring(tree, xml_declaration=True, encoding='UTF-8', pretty_print=True)


_schema: Optional[etree.XMLSchema] = None


def validate(xml: bytes) -> list[str]:
    """Errors against the Akoma Ntoso 3.0 schema; empty when the document is valid."""
    global _schema
    if _schema is None:
        _schema = etree.XMLSchema(etree.parse(str(SCHEMA)))
    tree = etree.fromstring(xml)
    if _schema.validate(tree):
        return []
    return [f'line {e.line}: {e.message}' for e in _schema.error_log]
