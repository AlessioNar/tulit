import tempfile
import os
import unittest
from lxml import etree

from tulit.parser.xml.akomantoso import (
    detect_akn_format,
    create_akn_parser,
    register_akn_parsers,
    AkomaNtosoParser,
    AKN4EUParser,
    GermanLegalDocMLParser,
    LuxembourgAKNParser,
)
from tulit.parser.exceptions import ParserError

from tulit.parser.xml.akomantoso.extractors import (
    AKNArticleExtractor,
    AKNContentProcessor,
)


class TestAkomaNtosoUtilsAndExtractors(unittest.TestCase):
    def write_xml(self, content: bytes) -> str:
        fh = tempfile.NamedTemporaryFile(delete=False, suffix='.xml')
        try:
            fh.write(content)
            fh.flush()
            return fh.name
        finally:
            fh.close()

    def test_detect_formats(self):
        # standard akn
        xml = b"<akomaNtoso xmlns='http://docs.oasis-open.org/legaldocml/ns/akn/3.0'/>"
        path = self.write_xml(xml)
        try:
            self.assertEqual(detect_akn_format(path), 'akn')
        finally:
            os.unlink(path)

        # german
        xml = b"<akomaNtoso xmlns='http://Inhaltsdaten.LegalDocML.de/1.8.2/'/>"
        path = self.write_xml(xml)
        try:
            self.assertEqual(detect_akn_format(path), 'german')
        finally:
            os.unlink(path)

        # luxembourg (CSD13)
        xml = b"<akomaNtoso xmlns='http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD13'/>"
        path = self.write_xml(xml)
        try:
            self.assertEqual(detect_akn_format(path), 'luxembourg')
        finally:
            os.unlink(path)

        # akn4eu via xml:id
        xml = b"<akomaNtoso xml:id='x1' xmlns='http://docs.oasis-open.org/legaldocml/ns/akn/3.0'/>"
        path = self.write_xml(xml)
        try:
            self.assertEqual(detect_akn_format(path), 'akn4eu')
        finally:
            os.unlink(path)

    def test_create_parser_by_format_and_errors(self):
        p = create_akn_parser(format='akn')
        self.assertIsInstance(p, AkomaNtosoParser)
        p = create_akn_parser(format='akn4eu')
        self.assertIsInstance(p, AKN4EUParser)
        p = create_akn_parser(format='german')
        self.assertIsInstance(p, GermanLegalDocMLParser)
        p = create_akn_parser(format='luxembourg')
        self.assertIsInstance(p, LuxembourgAKNParser)

        with self.assertRaises(ValueError):
            create_akn_parser()

        # registering again raises ParserError because parsers already registered
        with self.assertRaises(ParserError):
            register_akn_parsers()

    def test_extract_eid_variants(self):
        # AKN4EU xml:id extraction
        elem = etree.Element('article')
        elem.set('{http://www.w3.org/XML/1998/namespace}id', 'xml_1')
        p = AKN4EUParser()
        self.assertEqual(p.extract_eId(elem), 'xml_1')
        # fallback index
        self.assertEqual(p.extract_eId(etree.Element('a'), index=5), 'art_5')

        # Akoma standard eId extraction
        a = AkomaNtosoParser()
        e = etree.Element('article')
        e.set('eId', 'eid_1')
        self.assertEqual(a.extract_eId(e), 'eid_1')
        self.assertEqual(a.extract_eId(etree.Element('a'), index=2), 'art_2')

    def test_article_extractor(self):
        ns = {'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0'}
        extractor = AKNArticleExtractor(ns)
        # build sample article
        article = etree.fromstring("""
        <article eId='art_1' xmlns='http://docs.oasis-open.org/legaldocml/ns/akn/3.0'>
          <num>1</num>
          <heading>Title</heading>
          <paragraph eId='par_1'><p>Text A</p></paragraph>
          <paragraph eId='par_2'><p>Text B</p></paragraph>
        </article>
        """)
        meta = extractor.extract_article_metadata(article)
        self.assertEqual(meta['eId'], 'art_1')
        self.assertIn('1', meta['num'])
        # extract paragraphs by eId
        elems = extractor.extract_paragraphs_by_eid(article)
        self.assertTrue(any('par_1' in e['eId'] or e['eId']=='par_1' for e in elems))

    def test_content_processor_lists_and_tables(self):
        ns = {'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0'}
        proc = AKNContentProcessor(ns)
        # list items
        parent = etree.fromstring("""
        <root xmlns='http://docs.oasis-open.org/legaldocml/ns/akn/3.0'>
          <item eId='it_1'><p>One</p></item>
          <item eId='it_2'><p>Two</p></item>
        </root>
        """)
        items = proc.extract_list_items(parent)
        self.assertEqual(len(items), 2)

        # table
        table = etree.fromstring("""
        <table eId='t1' xmlns='http://docs.oasis-open.org/legaldocml/ns/akn/3.0'>
          <tr><td>R1C1</td><td>R1C2</td></tr>
          <tr><td>R2C1</td></tr>
        </table>
        """)
        tbl = proc.extract_table_content(table)
        self.assertEqual(tbl['eId'], 't1')
        self.assertEqual(len(tbl['rows']), 2)


if __name__ == '__main__':
    unittest.main()
