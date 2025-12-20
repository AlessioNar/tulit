"""
End-to-end tests for Luxembourg Legilux AKN parser.
Tests the complete parsing pipeline from downloaded Legilux files to parsed JSON output.
Uses files downloaded by Luxembourg Legilux client e2e tests as fixtures.
"""

import pytest
import os
import json
from pathlib import Path
import logging


@pytest.mark.e2e
@pytest.mark.parser
class TestLuxembourgLegiluxParser:
    """Test suite for Luxembourg Legilux AKN parser functionality."""

    @pytest.mark.slow
    def test_luxembourg_legilux_parsing(self, db_paths):
        """Test parsing Luxembourg Legilux XML documents."""
        sources_dir = db_paths['sources'] / 'member_states' / 'luxembourg' / 'legilux'
        results_dir = db_paths['results'] / 'member_states' / 'luxembourg'
        logs_dir = db_paths['logs']

        # Find downloaded XML files
        xml_files = list(sources_dir.glob('*.xml'))
        if not xml_files:
            pytest.skip("No Luxembourg Legilux XML files found - run Luxembourg Legilux client e2e tests first")

        # Test parsing the first available file
        xml_file = xml_files[0]
        expected_output = results_dir / f"{xml_file.stem}.json"

        from tulit.parser.xml.akomantoso import create_akn_parser
        parser = create_akn_parser(file_path=str(xml_file))

        # Parse the file
        parser.parse(str(xml_file))

        # Verify parsing results
        assert parser.preface is not None, "Preface should be extracted"
        assert parser.formula is not None, "Formula should be extracted"
        assert isinstance(parser.citations, list), "Citations should be a list"
        assert isinstance(parser.recitals, list), "Recitals should be a list"
        assert isinstance(parser.chapters, list), "Chapters should be a list"
        assert isinstance(parser.articles, list), "Articles should be a list"

        # Save results
        output_data = {
            'preface': parser.preface,
            'formula': parser.formula,
            'citations': parser.citations,
            'recitals': parser.recitals,
            'preamble_final': parser.preamble_final,
            'chapters': parser.chapters,
            'articles': parser.articles,
            'conclusions': parser.conclusions
        }

        expected_output.parent.mkdir(parents=True, exist_ok=True)
        with open(expected_output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        # Verify output file was created
        assert expected_output.exists(), f"Output file not created: {expected_output}"