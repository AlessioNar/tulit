"""
legalJSON to a LEOS .leg package.

A .leg package is a zip of Akoma Ntoso documents, the exchange format of
LEOS (the European Commission's Legislation Editing Open Software) and of
AKN4EU:

- ``main.xml``, the entry point: a ``<documentCollection>`` whose collection
  body references the act;
- the act, in a file of its own (``ACT-<number>-<language>.xml``), whose
  attachments reference the annexes;
- each annex, in a file of its own (``ANNEX-<n>-<number>-<language>.xml``),
  as a ``<doc name="ANNEX">``.

    >>> from tulit.exporters import to_leg
    >>> Path('act.leg').write_bytes(to_leg(tulit.fetch('32024R0903')))
"""
import io
import zipfile

from lxml import etree

from tulit.exporters.akn import (_Builder, _annexes, _identification, _references, annex_tree, serialize,
                                 to_akn_tree, work_number)


def leg_files(doc: dict) -> dict[str, bytes]:
    """The files of the .leg package of a legalJSON document, by name in the package."""
    meta = doc.get('meta') or {}
    number = work_number(meta)
    language = meta.get('language') or 'und'
    act_file = f'ACT-{number}-{language}.xml'
    annex_files = [f'ANNEX-{n}-{number}-{language}.xml' for n in range(1, len(_annexes(doc)) + 1)]

    files = {'main.xml': serialize(_collection(doc, act_file)),
             act_file: serialize(to_akn_tree(doc, annex_files or None))}
    for n, name in enumerate(annex_files, 1):
        files[name] = serialize(annex_tree(doc, n, name='ANNEX'))
    return files


def to_leg(doc: dict) -> bytes:
    """A legalJSON document as a .leg package (zip bytes)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as package:
        for name, content in leg_files(doc).items():
            package.writestr(name, content)
    return buffer.getvalue()


def _collection(doc: dict, act_file: str) -> etree._ElementTree:
    """main.xml: the collection that holds the act."""
    b = _Builder()
    meta = doc.get('meta') or {}
    root = b.el(None, 'akomaNtoso')
    collection = b.el(root, 'documentCollection', name='act')
    head = b.el(collection, 'meta')
    _identification(b, head, meta, component='collection')
    _references(b, head, meta)
    if doc.get('preface'):
        b.el(b.el(b.el(b.el(collection, 'coverPage'), 'longTitle'), 'p'), 'docTitle', doc['preface'])
    body = b.el(collection, 'collectionBody')
    component = b.el(body, 'component', eId='cmp_1')
    b.el(component, 'documentRef', eId='cmp_1__ref', href=act_file, showAs=doc.get('preface') or 'act')
    return etree.ElementTree(root)
