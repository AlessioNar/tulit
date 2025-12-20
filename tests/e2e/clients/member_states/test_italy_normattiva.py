"""
End-to-end tests for Italy Normattiva client downloads.
Tests the complete download pipeline from external APIs to local storage.
"""

import pytest
import os
from pathlib import Path
import json
import time


@pytest.mark.e2e
@pytest.mark.client_download
class TestItalyNormattivaClient:
    """Test suite for Italy Normattiva client download functionality."""

    @pytest.mark.slow
    def test_italy_normattiva_download(self, db_paths):
        """Test downloading from Italy Normattiva."""
        sources_dir = db_paths['sources'] / 'member_states' / 'italy' / 'normattiva'
        logs_dir = db_paths['logs']

        from tulit.client.state.normattiva import NormattivaClient
        client = NormattivaClient(str(sources_dir), str(logs_dir))

        try:
            result = client.download(dataGU='20241231', codiceRedaz='24G00229', dataVigenza='20251020', fmt='xml')
        except Exception as e:
            pytest.skip(f"Normattiva API unavailable: {e}")

        assert result is not None, "Download failed"
        assert len(result) > 0, "No files downloaded"
        for file_path in result:
            assert Path(file_path).exists(), f"Downloaded file not found: {file_path}"
            content = Path(file_path).read_text()
            assert len(content) > 100, f"Downloaded file {Path(file_path).name} seems too small"
            assert '<?xml' in content, f"File {Path(file_path).name} doesn't contain XML"