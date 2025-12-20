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

    def test_parse_calls_orchestrator_and_sets_valid(self):
        p = LuxembourgAKNParser()
        # use a temp filename (no file IO needed for this test)
        dummy_file = 'dummy.xml'

        # Patch the AKNParseOrchestrator class in the luxembourg module
        with patch('tulit.parser.xml.akomantoso.luxembourg.AKNParseOrchestrator') as MockOrch:
            mock_inst = MagicMock()
            MockOrch.return_value = mock_inst

            returned = p.parse(dummy_file)

            # parse should return self
            self.assertIs(returned, p)

            # valid flag should be set True (skip validation)
            self.assertTrue(p.valid)

            # orchestrator should have been constructed with parser and context
            MockOrch.assert_called()
            # execute_standard_workflow should have been invoked (allow any args)
            self.assertTrue(mock_inst.execute_standard_workflow.called)


if __name__ == '__main__':
    unittest.main()
