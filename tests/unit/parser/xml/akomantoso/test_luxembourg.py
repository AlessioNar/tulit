import unittest
from unittest.mock import patch, MagicMock
from lxml import etree
from tulit.parser.xml.akomantoso.luxembourg import LuxembourgAKNParser


class TestLuxembourgAKNParser(unittest.TestCase):
    def test_namespaces_override(self):
        p = LuxembourgAKNParser()
        # Ensure the CSD13 namespace is set
        self.assertIn('akn', p.namespaces)
        self.assertIn('scl', p.namespaces)

    def test_extract_eId_from_id_and_fallback(self):
        p = LuxembourgAKNParser()
        elem = etree.Element('article')
        elem.set('id', 'lux_123')
        self.assertEqual(p.extract_eId(elem), 'lux_123')

        # fallback when missing and index provided
        self.assertEqual(p.extract_eId(etree.Element('a'), index=7), 'art_7')

if __name__ == '__main__':
    unittest.main()
