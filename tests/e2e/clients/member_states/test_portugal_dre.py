"""
End-to-end tests for Portugal DRE client downloads.
Tests the complete download pipeline from external APIs to local storage.
"""

import pytest
import os
from pathlib import Path
import json
import time


@pytest.mark.e2e
@pytest.mark.client_download
class TestPortugalDREClient:
    """Test suite for Portugal DRE client download functionality."""

    @pytest.mark.slow
    def test_portugal_dre_download(self, db_paths):
        """Test downloading from Portugal DRE."""
        sources_dir = db_paths['sources'] / 'member_states' / 'portugal' / 'dre'
        logs_dir = db_paths['logs']

        from tulit.client.state.portugal import PortugalDREClient
        client = PortugalDREClient(str(sources_dir), str(logs_dir))

        try:
            result = client.download(
                document_type='legal_act',
                act_type='lei',
                number='39',
                year='2016',
                month='12',
                day='19',
                region='p',
                lang='pt',
                fmt='html'
            )
        except Exception as e:
            pytest.skip(f"Portugal DRE API unavailable: {e}")

        assert result is not None, "Download failed"
        assert Path(result).exists(), f"Downloaded file not found: {result}"

        # Check file content
        content = Path(result).read_text()
        assert len(content) > 100, f"Downloaded file seems too small"
        assert '<html' in content.lower(), "File doesn't contain HTML"