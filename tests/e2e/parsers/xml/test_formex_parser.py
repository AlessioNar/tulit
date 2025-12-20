"""
End-to-end tests for FORMEX XML parser.
Tests the complete parsing pipeline from downloaded FORMEX files to parsed JSON output.
Uses files downloaded by EU Cellar client e2e tests as fixtures.
"""

import pytest
import os
import json
from pathlib import Path
import logging


@pytest.mark.e2e
@pytest.mark.parser
class TestFormexParser:
    """Test suite for FORMEX XML parser functionality."""

    @pytest.mark.slow
    def test_formex_parsing(self, db_paths):
        """Test parsing FORMEX XML documents."""
        sources_dir = db_paths['sources'] / 'eu' / 'eurlex' / 'formex'
        results_dir = db_paths['results'] / 'eu' / 'formex'
        logs_dir = db_paths['logs']

        # Find downloaded FORMEX files
        formex_files = []
        if sources_dir.exists():
            for subdir in sources_dir.iterdir():
                if subdir.is_dir():
                    for doc_dir in subdir.iterdir():
                        if doc_dir.is_dir() and doc_dir.name.startswith('DOC_'):
                            formex_files.extend(list(doc_dir.glob('*.fmx.xml')))

        if not formex_files:
            pytest.skip("No FORMEX files found - run EU Cellar client e2e tests first")

        # Test parsing the first available file
        formex_file = formex_files[0]
        subdir_name = formex_file.parent.parent.name
        expected_output = results_dir / f"{subdir_name}_{formex_file.stem}.json"

        from tulit.parser.xml.formex import Formex4Parser
        parser = Formex4Parser()

        # Parse the file
        parser.parse(str(formex_file))

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