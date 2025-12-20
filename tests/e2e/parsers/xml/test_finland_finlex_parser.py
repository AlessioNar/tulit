"""
End-to-end tests for Finland Finlex AKN parser.
Tests the complete parsing pipeline from downloaded Finlex files to parsed JSON output.
Uses files downloaded by Finland Finlex client e2e tests as fixtures.
"""

import pytest
import os
import json
from pathlib import Path
import logging


@pytest.mark.e2e
@pytest.mark.parser
class TestFinlandFinlexParser:
    """Test suite for Finland Finlex AKN parser functionality."""

    @pytest.mark.slow
    def test_finland_finlex_parsing(self, db_paths):
        """Test parsing Finland Finlex XML documents."""
        sources_dir = db_paths['sources'] / 'member_states' / 'finland' / 'finlex'
        results_dir = db_paths['results'] / 'member_states' / 'finland'
        logs_dir = db_paths['logs']

        # Find downloaded XML files
        xml_files = list(sources_dir.glob('*.xml'))
        if not xml_files:
            pytest.skip("No Finland Finlex XML files found - run Finland Finlex client e2e tests first")

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
        assert len(parser.articles) > 0, f"Articles should not be empty for legal documents: {xml_file}"

        # Validate LegalJSON structure - articles and their children
        for article in parser.articles:
            assert 'eId' in article, f"Article missing eId: {article}"
            assert 'num' in article, f"Article missing num: {article}"
            assert 'children' in article, f"Article missing children: {article}"
            assert isinstance(article['children'], list), f"Article children should be a list: {article}"
            
            # Validate article children structure
            for child in article['children']:
                assert 'eId' in child, f"Article child missing eId: {child}"
                assert 'text' in child, f"Article child missing text: {child}"
                assert isinstance(child['text'], str), f"Article child text should be string: {child}"
                assert len(child['text'].strip()) > 0, f"Article child text should not be empty: {child}"
            
            # Optional fields
            if 'heading' in article:
                assert isinstance(article['heading'], (str, type(None))), f"Article heading should be string or None: {article}"

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