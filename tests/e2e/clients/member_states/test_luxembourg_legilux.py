"""
End-to-end tests for Luxembourg Legilux client downloads.
Tests the complete download pipeline from external APIs to local storage.
"""

import pytest
import os
from pathlib import Path
import json
import time


@pytest.mark.e2e
@pytest.mark.client_download
class TestLuxembourgLegiluxClient:
    """Test suite for Luxembourg Legilux client download functionality."""

    @pytest.mark.slow
    def test_luxembourg_legilux_download(self, db_paths):
        """Test downloading from Luxembourg Legilux."""
        sources_dir = db_paths['sources'] / 'member_states' / 'luxembourg' / 'legilux'
        logs_dir = db_paths['logs']

        from tulit.client.state.legilux import LegiluxClient
        client = LegiluxClient(str(sources_dir), str(logs_dir))

        try:
            result = client.download(eli='http://data.legilux.public.lu/eli/etat/leg/loi/2006/07/31/n2/jo')
        except Exception as e:
            pytest.skip(f"Legilux API unavailable: {e}")

        assert result is not None, "Download failed"
        assert len(result) > 0, "No files downloaded"
        for file_path in result:
            assert Path(file_path).exists(), f"Downloaded file not found: {file_path}"
            content = Path(file_path).read_text()
            assert len(content) > 100, f"Downloaded file {Path(file_path).name} seems too small"
            assert '<?xml' in content, f"File {Path(file_path).name} doesn't contain XML"