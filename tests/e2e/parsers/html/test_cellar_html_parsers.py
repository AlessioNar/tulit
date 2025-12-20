"""
End-to-end tests for Cellar HTML parsers.
Tests the complete parsing pipeline from downloaded Cellar HTML files to parsed JSON output.
Uses files downloaded by EU Cellar client e2e tests as fixtures.
"""

import pytest
import os
import json
from pathlib import Path
import logging


@pytest.mark.e2e
@pytest.mark.parser
class TestCellarHTMLParsers:
    """Test suite for Cellar HTML parser functionality."""

    @pytest.mark.slow
    def test_cellar_html_parsing(self, db_paths):
        """Test parsing Cellar HTML documents."""
        sources_dir = db_paths['sources'] / 'eu' / 'cellar'
        results_dir = db_paths['results'] / 'eu' / 'cellar'
        logs_dir = db_paths['logs']

        # Find downloaded HTML files
        html_files = list(sources_dir.glob('*.html'))
        if not html_files:
            pytest.skip("No Cellar HTML files found - run EU Cellar client e2e tests first")

        # Test parsing the first available file
        html_file = html_files[0]
        expected_output = results_dir / f"{html_file.stem}.json"

        from tulit.parser.html.cellar import CellarHTMLParser
        parser = CellarHTMLParser()

        # Parse the file
        result = parser.parse(str(html_file))

        # Verify parsing results
        assert result is not None, "Parsing result should not be None"
        assert isinstance(result, dict), "Parsing result should be a dictionary"

        # Cellar parser typically returns structured data
        # Save results
        expected_output.parent.mkdir(parents=True, exist_ok=True)
        with open(expected_output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # Verify output file was created
        assert expected_output.exists(), f"Output file not created: {expected_output}"

    @pytest.mark.slow
    def test_cellar_standard_html_parsing(self, db_paths):
        """Test parsing Cellar standard HTML documents."""
        sources_dir = db_paths['sources'] / 'eu' / 'cellar'
        results_dir = db_paths['results'] / 'eu' / 'cellar'
        logs_dir = db_paths['logs']

        # Find downloaded HTML files
        html_files = list(sources_dir.glob('*.html'))
        if not html_files:
            pytest.skip("No Cellar HTML files found - run EU Cellar client e2e tests first")

        # Test parsing the first available file
        html_file = html_files[0]
        expected_output = results_dir / f"{html_file.stem}_standard.json"

        from tulit.parser.html.cellar import CellarStandardHTMLParser
        parser = CellarStandardHTMLParser()

        # Parse the file
        result = parser.parse(str(html_file))

        # Verify parsing results
        assert result is not None, "Parsing result should not be None"
        assert isinstance(result, dict), "Parsing result should be a dictionary"

        # Save results
        expected_output.parent.mkdir(parents=True, exist_ok=True)
        with open(expected_output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # Verify output file was created
        assert expected_output.exists(), f"Output file not created: {expected_output}"

    @pytest.mark.slow
    def test_proposal_html_parsing(self, db_paths):
        """Test parsing proposal HTML documents."""
        sources_dir = db_paths['sources'] / 'eu' / 'cellar'
        results_dir = db_paths['results'] / 'eu' / 'cellar'
        logs_dir = db_paths['logs']

        # Find downloaded HTML files
        html_files = list(sources_dir.glob('*.html'))
        if not html_files:
            pytest.skip("No Cellar HTML files found - run EU Cellar client e2e tests first")

        # Test parsing the first available file
        html_file = html_files[0]
        expected_output = results_dir / f"{html_file.stem}_proposal.json"

        from tulit.parser.html.cellar import ProposalHTMLParser
        parser = ProposalHTMLParser()

        # Parse the file
        result = parser.parse(str(html_file))

        # Verify parsing results
        assert result is not None, "Parsing result should not be None"
        assert isinstance(result, dict), "Parsing result should be a dictionary"

        # Save results
        expected_output.parent.mkdir(parents=True, exist_ok=True)
        with open(expected_output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # Verify output file was created
        assert expected_output.exists(), f"Output file not created: {expected_output}"