"""
End-to-end tests for France Legifrance client.
Tests the complete download pipeline from Legifrance API to local storage.
"""

import pytest
import os
import json
from pathlib import Path
import logging


@pytest.mark.e2e
@pytest.mark.client
class TestFranceLegifranceClient:
    """Test suite for France Legifrance client functionality."""

    @pytest.mark.slow
    def test_france_legifrance_download(self, db_paths):
        """Test downloading documents from France Legifrance."""
        sources_dir = db_paths['sources'] / 'member_states' / 'france' / 'legifrance'
        results_dir = db_paths['results'] / 'member_states' / 'france'
        logs_dir = db_paths['logs']

        # Check if Legifrance credentials are available
        client_id = os.environ.get('LEGIFRANCE_CLIENT_ID')
        client_secret = os.environ.get('LEGIFRANCE_CLIENT_SECRET')

        if not client_id or not client_secret:
            pytest.skip("Legifrance API credentials not available (set LEGIFRANCE_CLIENT_ID and LEGIFRANCE_CLIENT_SECRET)")

        try:
            from tulit.client.state.legifrance import LegifranceClient
            client = LegifranceClient(
                client_id=client_id,
                client_secret=client_secret,
                download_dir=str(sources_dir),
                log_dir=str(logs_dir)
            )

            # Test download with a sample CELEX number
            # Using a known French document CELEX number
            celex_number = "32019L0904"  # Example EU directive that should have French version

            # Download the document
            client.download(celex_number)

            # Verify download results
            expected_file = sources_dir / f"{celex_number}.xml"
            assert expected_file.exists(), f"Downloaded file not found: {expected_file}"

            # Verify file has content
            assert expected_file.stat().st_size > 0, f"Downloaded file is empty: {expected_file}"

        except Exception as e:
            # If API is unavailable, skip the test
            if "connection" in str(e).lower() or "timeout" in str(e).lower() or "unavailable" in str(e).lower():
                pytest.skip(f"France Legifrance API unavailable: {e}")
            else:
                raise