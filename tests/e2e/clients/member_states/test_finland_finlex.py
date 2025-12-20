"""
End-to-end tests for Finland Finlex client downloads.
Tests the complete download pipeline from external APIs to local storage.
"""

import pytest
import os
from pathlib import Path
import json
import time


@pytest.mark.e2e
@pytest.mark.client_download
class TestFinlandFinlexClient:
    """Test suite for Finland Finlex client download functionality."""

    @pytest.mark.slow
    def test_finland_finlex_download(self, db_paths):
        """Test downloading from Finland Finlex."""
        sources_dir = db_paths['sources'] / 'member_states' / 'finland' / 'finlex'
        logs_dir = db_paths['logs']

        from tulit.client.state.finlex import FinlexClient
        client = FinlexClient(str(sources_dir), str(logs_dir))

        try:
            result = client.download(year='2024', number='123', fmt='xml')
        except Exception as e:
            pytest.skip(f"Finlex API unavailable: {e}")

        assert result is not None, "Download failed"
        assert Path(result).exists(), f"Downloaded file not found: {result}"

        # Check file content
        content = Path(result).read_text()
        assert len(content) > 100, "Downloaded file seems too small"
        assert '<akomaNtoso' in content, "File doesn't contain Akoma Ntoso XML"