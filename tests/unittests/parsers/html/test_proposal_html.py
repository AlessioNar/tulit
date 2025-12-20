import unittest
import os
from tulit.parsers.html.cellar.proposal import ProposalHTMLParser
import json
from pathlib import Path

from tests.conftest import locate_data_dir

DATA_DIR = locate_data_dir(__file__) / "sources" / "eu" / "eurlex" / "commission_proposals"
file_path_com6 = str(DATA_DIR / "COM(2025)6.html")
file_path_com43 = str(DATA_DIR / "COM(2025)43.html")
file_path_com1 = str(DATA_DIR / "COM(2025)1.html")


class TestProposalHTMLParser(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None  # Allow full diff if needed
        self.parser = ProposalHTMLParser()
        
        # Ensure test file exists
        if not os.path.exists(file_path_com6):
            raise FileNotFoundError(f"Test file not found at {file_path_com6}")
    
    def test_get_root(self):
        """Test parsing and root element retrieval from the proposal HTML file."""
        self.parser.get_root(file_path_com6)
        self.assertIsNotNone(self.parser.root, "Root element should not be None")
    
    def test_get_metadata(self):
        """Test extracting metadata from the proposal."""
        self.parser.get_root(file_path_com6)
        self.parser.get_metadata()
        
        expected_metadata = {
            'institution': 'EUROPEAN COMMISSION',
            'emission_date': 'Brussels, 13.1.2025',
            'com_reference': 'COM(2025) 6 final',
            'interinstitutional_reference': '2025/0002(NLE)',
            'status': 'Proposal for a',
            'document_type': 'COUNCIL DECISION',
            'title': 'on the position to be taken on behalf of the European Union in the sixty-eighth session of the Commission on Narcotic Drugs on the scheduling of substances under the Single Convention on Narcotic Drugs of 1961, as amended by the 1972 Protocol, and the Convention on Psychotropic Substances of 1971'
        }
        
        self.assertEqual(self.parser.metadata, expected_metadata, "Metadata should match expected values")
    
    def test_get_metadata_com43(self):
        """Test extracting metadata from COM(2025)43."""
        self.parser.get_root(file_path_com43)
        self.parser.get_metadata()
        
        self.assertEqual(self.parser.metadata['institution'], 'EUROPEAN COMMISSION')
        self.assertEqual(self.parser.metadata['com_reference'], 'COM(2025) 43 final')
        self.assertEqual(self.parser.metadata['interinstitutional_reference'], '2025/0024(NLE)')
        self.assertEqual(self.parser.metadata['status'], 'Proposal for a')
        self.assertEqual(self.parser.metadata['document_type'], 'COUNCIL DECISION')
    
    def test_get_preface(self):
        """Test extracting the preface (combination of status, type, and title)."""
        self.parser.get_root(file_path_com6)
        self.parser.get_preface()
        
        expected_preface = "Proposal for a COUNCIL DECISION on the position to be taken on behalf of the European Union in the sixty-eighth session of the Commission on Narcotic Drugs on the scheduling of substances under the Single Convention on Narcotic Drugs of 1961, as amended by the 1972 Protocol, and the Convention on Psychotropic Substances of 1971"
        
        self.assertEqual(self.parser.preface, expected_preface, "Preface should match expected value")
    
    def test_get_explanatory_memorandum(self):
        """Test extracting the explanatory memorandum sections."""
        self.parser.get_root(file_path_com6)
        self.parser.get_explanatory_memorandum()
        
        # Check title
        self.assertEqual(self.parser.explanatory_memorandum['title'], 'EXPLANATORY MEMORANDUM')
        
        # Check that sections were extracted
        self.assertIn('sections', self.parser.explanatory_memorandum)
        sections = self.parser.explanatory_memorandum['sections']
        self.assertGreater(len(sections), 0, "Should have extracted at least one section")
        
        # Check first section structure
        first_section = sections[0]
        self.assertEqual(first_section['level'], 1)
        self.assertIn('heading', first_section)
        self.assertIn('content', first_section)
    
    def test_full_parse_com6(self):
        """Test full parsing of COM(2025)6."""
        result = self.parser.parse(file_path_com6)
        
        self.assertIsNotNone(result)
        self.assertIsNotNone(self.parser.root)
        self.assertIsNotNone(self.parser.metadata)
        self.assertIsNotNone(self.parser.preface)
        self.assertIsNotNone(self.parser.explanatory_memorandum)
        
        # Verify metadata
        self.assertEqual(self.parser.metadata['com_reference'], 'COM(2025) 6 final')
        
        # Verify explanatory memorandum has sections
        self.assertGreater(len(self.parser.explanatory_memorandum.get('sections', [])), 0)
    
    def test_full_parse_com43(self):
        """Test full parsing of COM(2025)43."""
        parser2 = ProposalHTMLParser()
        result = parser2.parse(file_path_com43)
        
        self.assertIsNotNone(result)
        self.assertEqual(parser2.metadata['com_reference'], 'COM(2025) 43 final')
        self.assertGreater(len(parser2.explanatory_memorandum.get('sections', [])), 0)
    
    def test_full_parse_com1(self):
        """Test full parsing of COM(2025)1."""
        parser3 = ProposalHTMLParser()
        result = parser3.parse(file_path_com1)
        
        self.assertIsNotNone(result)
        self.assertEqual(parser3.metadata['com_reference'], 'COM(2025) 1 final')
        self.assertEqual(parser3.metadata['document_type'], 'DECISION OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL')
        self.assertGreater(len(parser3.explanatory_memorandum.get('sections', [])), 0)
    
    def test_section_hierarchy(self):
        """Test that the section hierarchy is correctly parsed."""
        self.parser.get_root(file_path_com43)
        self.parser.get_explanatory_memorandum()
        
        sections = self.parser.explanatory_memorandum['sections']
        
        # Find a section with subsections
        section_with_subsections = None
        for section in sections:
            if section.get('content') and any(isinstance(item, dict) and item.get('level') == 2 for item in section['content']):
                section_with_subsections = section
                break
        
        if section_with_subsections:
            # Verify level 2 subsection exists
            level2_items = [item for item in section_with_subsections['content'] if isinstance(item, dict) and item.get('level') == 2]
            self.assertGreater(len(level2_items), 0, "Should have at least one level 2 subsection")
            
            # Verify level 2 subsection has heading
            self.assertIn('heading', level2_items[0])
    
    def test_export_to_json(self):
        """Test that the parsed data can be exported to JSON."""
        self.parser.parse(file_path_com6)
        
        # Get serializable dict
        parser_dict = self.parser.__dict__
        serializable_dict = {k: v for k, v in parser_dict.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))}
        
        # Try to convert to JSON
        json_str = json.dumps(serializable_dict, ensure_ascii=False, indent=4)
        self.assertIsNotNone(json_str)
        self.assertGreater(len(json_str), 0)
        
        # Verify it can be loaded back
        loaded = json.loads(json_str)
        self.assertEqual(loaded['metadata']['com_reference'], 'COM(2025) 6 final')


# Run the tests
if __name__ == "__main__":
    unittest.main()
