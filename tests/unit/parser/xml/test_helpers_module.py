import unittest
from lxml import etree

from tulit.parser.xml.helpers import XMLNodeExtractor, XMLValidator
from tulit.parser.xml.xml import XMLParser
from tulit.parser.exceptions import FileLoadError


class FakeXMLParser(XMLParser):
    def get_preface(self):
        return None

    def get_articles(self):
        return None

    def parse(self, file):
        self._file_path = file
        return self


class TestXMLHelpersAndParser(unittest.TestCase):
    def setUp(self):
        self.extractor = XMLNodeExtractor()
        self.validator = XMLValidator()
        self.parser = FakeXMLParser()

    def test_extract_text_and_findall(self):
        xml = etree.fromstring('<root><p>one</p><p>two<span>sub</span></p></root>')
        ps = self.extractor.findall(xml, './/p')
        self.assertEqual(len(ps), 2)
        self.assertEqual(self.extractor.extract_text(ps[0]), 'one')
        texts = self.extractor.extract_text_from_all(xml, './/p')
        self.assertEqual(texts, ['one', 'twosub'])

    def test_safe_find_and_safe_find_text(self):
        xml = etree.fromstring('<root><a>hello</a></root>')
        found = self.extractor.safe_find(xml, './/a')
        self.assertIsNotNone(found)
        self.assertEqual(self.extractor.safe_find_text(xml, './/missing'), '')

    def test_remove_nodes_preserve_tail(self):
        xml = etree.fromstring('<root>pre<to_remove/>tail</root>')
        modified = self.extractor.remove_nodes(xml, './/to_remove', preserve_tail=True)
        # after removal, 'tail' should be preserved in the parent's text
        self.assertIn('tail', (modified.text or ''))

    def test_validator_no_schema(self):
        xml = etree.fromstring('<root><child/></root>')
        # No schema loaded -> validate should raise ParserConfigurationError
        from tulit.parser.exceptions import ParserConfigurationError
        with self.assertRaises(ParserConfigurationError):
            self.validator.validate(xml)
        # Loading non-existent schema should raise FileLoadError
        from tulit.parser.exceptions import FileLoadError
        with self.assertRaises(FileLoadError):
            self.validator.load_schema('nonexistent.xsd')

    def test_xmlparser_namespace_and_secure_parser(self):
        # namespaces property should sync with extractor
        self.parser.namespaces = {'akn': 'http://example.org'}
        self.assertEqual(self.parser._extractor.namespaces, {'akn': 'http://example.org'})

        parser_obj = self.parser._create_secure_parser()
        self.assertIsInstance(parser_obj, etree.XMLParser)
        # Attempting get_root without file should raise FileLoadError
        with self.assertRaises(FileLoadError):
            self.parser.get_root()

    def test_remove_nodes_prev_sibling(self):
        xml = etree.fromstring('<root><a>one</a><to_remove/>tail</root>')
        # ensure previous sibling exists
        modified = self.extractor.remove_nodes(xml, './/to_remove', preserve_tail=True)
        # previous sibling 'a' should now have tail containing 'tail'
        a = modified.find('.//a')
        self.assertIn('tail', (a.tail or ''))

    def test_validator_load_schema_and_errors(self):
        # locate the packaged schema and ensure it can be loaded
        import importlib, os
        pkg = importlib.import_module('tulit.parser')
        schema = os.path.join(os.path.dirname(pkg.__file__), 'xml', 'assets', 'xml.xsd')
        self.assertTrue(os.path.exists(schema), f"Schema not found: {schema}")
        loaded = self.validator.load_schema(schema)
        self.assertTrue(loaded, "Expected schema to load successfully")
        # validate a small document that likely does not match the schema -> expect SchemaValidationError
        from tulit.parser.exceptions import SchemaValidationError
        xml = etree.fromstring('<root><invalid/></root>')
        with self.assertRaises(SchemaValidationError):
            self.validator.validate(xml)
        # get_validation_errors returns list
        errors = self.validator.get_validation_errors()
        self.assertIsInstance(errors, list)

    def test_load_relaxng_and_unknown_type(self):
        import tempfile, os
        # create a small RelaxNG that only accepts <root/>
        rng = b"""
        <grammar xmlns='http://relaxng.org/ns/structure/1.0'>
            <start>
                <element name='root'>
                    <empty/>
                </element>
            </start>
        </grammar>
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix='.rng') as fh:
            fh.write(rng)
            rng_path = fh.name

        try:
            self.assertTrue(os.path.exists(rng_path))
            loaded = self.validator.load_schema(rng_path, schema_type='relaxng')
            self.assertTrue(loaded)

            # Validate a non-matching document -> expect SchemaValidationError
            from tulit.parser.exceptions import SchemaValidationError
            xml = etree.fromstring('<notroot/>')
            with self.assertRaises(SchemaValidationError):
                self.validator.validate(xml)
            errs = self.validator.get_validation_errors()
            # errors should be a list (may be empty depending on lib), but allow either
            self.assertIsInstance(errs, list)

            # unknown schema type should raise ParserConfigurationError
            from tulit.parser.exceptions import ParserConfigurationError
            with self.assertRaises(ParserConfigurationError):
                self.validator.load_schema(rng_path, schema_type='unknown')
        finally:
            try:
                os.unlink(rng_path)
            except Exception:
                pass


if __name__ == '__main__':
    unittest.main()
