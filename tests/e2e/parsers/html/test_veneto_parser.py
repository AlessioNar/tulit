"""
End-to-end tests for Veneto HTML parser.
Tests the complete parsing pipeline from downloaded Veneto HTML files to parsed JSON output.
Uses files downloaded by Veneto client e2e tests as fixtures.
"""

import pytest
import os
import json
from pathlib import Path
import logging


@pytest.mark.e2e
@pytest.mark.parser
class TestVenetoHTMLParser:
    """Test suite for Veneto HTML parser functionality."""

    @pytest.mark.slow
    def test_veneto_html_parsing(self, db_paths):
        """Test parsing Veneto HTML documents."""
        sources_dir = db_paths['sources'] / 'regional' / 'veneto'
        results_dir = db_paths['results'] / 'regional' / 'veneto'
        logs_dir = db_paths['logs']

        # Find downloaded HTML files
        html_files = list(sources_dir.glob('*.html'))
        if not html_files:
            pytest.skip("No Veneto HTML files found - run Veneto client e2e tests first")

        # Test parsing the first available file
        html_file = html_files[0]
        expected_output = results_dir / f"{html_file.stem}.json"

        from tulit.parser.html.veneto import VenetoHTMLParser
        parser = VenetoHTMLParser()

        # Parse the file
        result = parser.parse(str(html_file))

        # Verify parsing results
        assert result is not None, "Parsing result should not be None"
        assert isinstance(result, dict), "Parsing result should be a dictionary"

        # Veneto parser typically returns structured data
        # Save results
        expected_output.parent.mkdir(parents=True, exist_ok=True)
        with open(expected_output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # Verify output file was created
        assert expected_output.exists(), f"Output file not created: {expected_output}"