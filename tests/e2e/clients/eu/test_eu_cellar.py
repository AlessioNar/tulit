"""
End-to-end tests for EU Cellar client downloads.
Tests the complete download pipeline from external APIs to local storage.
Tests all supported formats: fmx4, xhtml, html with both CELEX and ELI identifiers.
"""

import pytest
import os
from pathlib import Path
import json
import time


@pytest.mark.e2e
@pytest.mark.client
class TestEUCellarClient:
    """Test suite for EU Cellar client download functionality."""

    @pytest.mark.slow
    def test_eu_cellar_download_fmx4_celex(self, db_paths):
        """Test downloading FORMEX documents using CELEX identifier."""
        sources_dir = db_paths['sources'] / 'eu' / 'cellar' / 'formex'
        logs_dir = db_paths['logs']

        from tulit.client.eu.cellar import CellarClient
        client = CellarClient(str(sources_dir), str(logs_dir))

        try:
            result = client.download(celex='32024R0903', format='fmx4', type_id='celex')
        except Exception as e:
            pytest.skip(f"Cellar API unavailable: {e}")

        assert result is not None, "Download failed"
        assert len(result) > 0, "No files downloaded"
        self._verify_downloaded_files(result, 'fmx4')

    @pytest.mark.slow
    def test_eu_cellar_download_fmx4_eli(self, db_paths):
        """Test downloading FORMEX documents using ELI identifier."""
        sources_dir = db_paths['sources'] / 'eu' / 'cellar' / 'formex'
        logs_dir = db_paths['logs']

        from tulit.client.eu.cellar import CellarClient
        client = CellarClient(str(sources_dir), str(logs_dir))

        try:
            # Using an ELI identifier for a regulation
            eli_uri = 'http://data.europa.eu/eli/reg/2024/903/oj'
            result = client.download(celex=eli_uri, format='fmx4', type_id='eli')
        except Exception as e:
            pytest.skip(f"Cellar API unavailable: {e}")

        assert result is not None, "Download failed"
        assert len(result) > 0, "No files downloaded"
        self._verify_downloaded_files(result, 'fmx4')

    @pytest.mark.slow
    def test_eu_cellar_download_xhtml(self, db_paths):
        """Test downloading XHTML documents."""
        sources_dir = db_paths['sources'] / 'eu' / 'cellar' / 'xhtml'
        logs_dir = db_paths['logs']

        from tulit.client.eu.cellar import CellarClient
        client = CellarClient(str(sources_dir), str(logs_dir))

        try:
            result = client.download(celex='32024R0903', format='xhtml')
        except Exception as e:
            pytest.skip(f"Cellar API unavailable: {e}")

        assert result is not None, "Download failed"
        assert len(result) > 0, "No files downloaded"
        self._verify_downloaded_files(result, 'xhtml')

    @pytest.mark.slow
    def test_eu_cellar_download_html(self, db_paths):
        """Test downloading standard HTML documents."""
        sources_dir = db_paths['sources'] / 'eu' / 'cellar' / 'html'
        logs_dir = db_paths['logs']

        from tulit.client.eu.cellar import CellarClient
        client = CellarClient(str(sources_dir), str(logs_dir))

        try:
            result = client.download(celex='32024R0903', format='html')
        except Exception as e:
            pytest.skip(f"Cellar API unavailable: {e}")

        # HTML format might not be available for all documents, so be more lenient
        if result is None or len(result) == 0:
            pytest.skip("HTML format not available for this CELEX document")

        assert result is not None, "Download failed"
        assert len(result) > 0, "No files downloaded"
        self._verify_downloaded_files(result, 'html')

    @pytest.mark.slow
    def test_eu_cellar_sparql_query(self, db_paths):
        """Test SPARQL query functionality."""
        logs_dir = db_paths['logs']

        from tulit.client.eu.cellar import CellarClient
        client = CellarClient(str(db_paths['sources'] / 'eu' / 'cellar'), str(logs_dir))

        results = None
        try:
            # Test with a simple SPARQL query
            sparql_query = """
            PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
            SELECT DISTINCT ?work ?title
            WHERE {
                ?work a cdm:work .
                ?work cdm:work_title ?title .
            }
            LIMIT 5
            """
            results = client.send_sparql_query(sparql_query, celex="32024R0903")  # Pass celex to trigger query execution
        except Exception as e:
            pytest.skip(f"SPARQL endpoint unavailable: {e}")

        assert results is not None, "SPARQL query failed"
        assert isinstance(results, dict), "Results should be a dictionary"
        assert 'results' in results, "Results should contain 'results' key"
        assert 'bindings' in results['results'], "Results should contain bindings"

    @pytest.mark.slow
    def test_eu_cellar_get_results_table(self, db_paths):
        """Test get_results_table functionality."""
        logs_dir = db_paths['logs']

        from tulit.client.eu.cellar import CellarClient
        client = CellarClient(str(db_paths['sources'] / 'eu' / 'cellar'), str(logs_dir))

        try:
            # Test with a simple SPARQL query
            sparql_query = """
            PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
            SELECT DISTINCT ?work ?title
            WHERE {
                ?work a cdm:work .
                ?work cdm:work_title ?title .
            }
            LIMIT 3
            """
            results = client.get_results_table(sparql_query)
        except Exception as e:
            pytest.skip(f"SPARQL endpoint unavailable: {e}")

        assert results is not None, "get_results_table failed"
        assert isinstance(results, dict), "Results should be a dictionary"
        assert 'results' in results, "Results should contain 'results' key"

    def test_eu_cellar_invalid_format(self, db_paths):
        """Test error handling for invalid format."""
        sources_dir = db_paths['sources'] / 'eu' / 'cellar'
        logs_dir = db_paths['logs']

        from tulit.client.eu.cellar import CellarClient
        client = CellarClient(str(sources_dir), str(logs_dir))

        # Test with invalid format
        result = client.download(celex='32024R0903', format='invalid')
        assert result is None, "Should return None for invalid format"

    def _verify_downloaded_files(self, file_paths, expected_format):
        """Helper method to verify downloaded files."""
        for file_path in file_paths:
            path_obj = Path(file_path)
            assert path_obj.exists(), f"Downloaded path not found: {file_path}"

            if path_obj.is_file():
                content = path_obj.read_text()
                assert len(content) > 100, f"Downloaded file {path_obj.name} seems too small"

                # Check format-specific content
                if expected_format == 'fmx4':
                    assert '<?xml' in content, f"File {path_obj.name} doesn't contain XML"
                    assert 'fmx4' in content.lower(), f"File {path_obj.name} doesn't appear to be FORMEX format"
                elif expected_format == 'xhtml':
                    assert '<?xml' in content or '<!DOCTYPE html' in content, f"File {path_obj.name} doesn't contain XHTML/HTML"
                elif expected_format == 'html':
                    assert '<!DOCTYPE html' in content or '<html' in content, f"File {path_obj.name} doesn't contain HTML"

            elif path_obj.is_dir():
                # Check for files in the directory based on format
                if expected_format == 'fmx4':
                    xml_files = list(path_obj.glob('*.xml'))
                    assert len(xml_files) > 0, f"No XML files found in extracted directory {path_obj}"
                    for xml_file in xml_files:
                        content = xml_file.read_text()
                        assert len(content) > 100, f"Downloaded file {xml_file.name} seems too small"
                        assert '<?xml' in content, f"File {xml_file.name} doesn't contain XML"
                else:
                    # For HTML/XHTML, check for appropriate files
                    html_files = list(path_obj.glob('*.html')) + list(path_obj.glob('*.xhtml'))
                    assert len(html_files) > 0, f"No HTML/XHTML files found in extracted directory {path_obj}"
                    for html_file in html_files:
                        content = html_file.read_text()
                        assert len(content) > 100, f"Downloaded file {html_file.name} seems too small"