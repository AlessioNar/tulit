"""
End-to-end tests for EU Cellar client downloads.
Tests the complete download pipeline from external APIs to local storage.
"""

import pytest
import os
from pathlib import Path
import json
import time


@pytest.mark.e2e
@pytest.mark.client_download
class TestEUCellarClient:
    """Test suite for EU Cellar client download functionality."""

    @pytest.mark.slow
    def test_eu_cellar_download(self, db_paths):
        """Test downloading from EU Cellar."""
        sources_dir = db_paths['sources'] / 'eu' / 'eurlex' / 'formex'
        logs_dir = db_paths['logs']

        from tulit.client.eu.cellar import CellarClient
        client = CellarClient(str(sources_dir), str(logs_dir))

        try:
            result = client.download(celex='32024R0903', format='fmx4')
        except Exception as e:
            pytest.skip(f"Cellar API unavailable: {e}")

        assert result is not None, "Download failed"
        assert len(result) > 0, "No files downloaded"
        for file_path in result:
            path_obj = Path(file_path)
            assert path_obj.exists(), f"Downloaded path not found: {file_path}"
            if path_obj.is_file():
                content = path_obj.read_text()
                assert len(content) > 100, f"Downloaded file {path_obj.name} seems too small"
                assert '<?xml' in content, f"File {path_obj.name} doesn't contain XML"
            elif path_obj.is_dir():
                # Check for XML files in the directory
                xml_files = list(path_obj.glob('*.xml'))
                assert len(xml_files) > 0, f"No XML files found in extracted directory {path_obj}"
                for xml_file in xml_files:
                    content = xml_file.read_text()
                    assert len(content) > 100, f"Downloaded file {xml_file.name} seems too small"
                    assert '<?xml' in content, f"File {xml_file.name} doesn't contain XML"