"""
LEOS .leg packages.

A .leg package is a zip of Akoma Ntoso documents: ``main.xml`` holds a
``<documentCollection>`` whose collection body references the act's file,
and the act references each annex's file from its attachments. The parser
puts the annexes back in place in the act and reads it as Akoma Ntoso.
"""
import os
import tempfile
import zipfile

from lxml import etree

from tulit.parser.exceptions import FileLoadError
from tulit.parser.xml.akomantoso.base import AkomaNtosoParser

AKN = {'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0'}
_SAFE = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True)


def read_leg(path: str) -> etree._Element:
    """The act of a .leg package as one Akoma Ntoso document, its annexes attached inline."""
    try:
        package = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as e:
        raise FileLoadError(f"{path} is not a .leg package: {e}") from e
    with package:
        names = set(package.namelist())

        def read(name: str) -> etree._Element:
            if name not in names:
                raise FileLoadError(f"The .leg package {path} has no {name}")
            return etree.fromstring(package.read(name), _SAFE)

        main = read('main.xml')
        reference = main.find('.//akn:collectionBody//akn:documentRef', AKN)
        if reference is None or not reference.get('href'):
            raise FileLoadError(f"main.xml of {path} references no document")
        act = read(reference.get('href'))
        for annex in act.findall('.//akn:attachments/akn:attachment/akn:documentRef', AKN):
            if annex.get('href') in names:
                document = next((c for c in read(annex.get('href')) if isinstance(c.tag, str)), None)
                if document is not None:
                    annex.getparent().replace(annex, document)
        return act


class LegParser(AkomaNtosoParser):
    """Parses a LEOS .leg package (a zip of Akoma Ntoso documents) to legalJSON."""

    def parse(self, file: str, **options) -> 'LegParser':
        act = read_leg(file)
        handle, merged = tempfile.mkstemp(suffix='.xml', prefix='tulit-leg-')
        try:
            with os.fdopen(handle, 'wb') as f:
                f.write(etree.tostring(act, xml_declaration=True, encoding='UTF-8'))
            return super().parse(merged, **options)
        finally:
            os.unlink(merged)
