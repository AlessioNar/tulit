"""
End-to-end tests for Germany RIS client.
Tests the complete download pipeline from German RIS API to local storage.
Tests all document types: legislation, case_law, literature, eli with all supported formats.
"""

import pytest
import os
from pathlib import Path
import json
import time


@pytest.mark.e2e
@pytest.mark.client
class TestGermanyClient:
    """Test suite for Germany RIS client download functionality."""

    @pytest.mark.slow
    def test_germany_download_legislation_html(self, db_paths):
        """Test downloading German legislation in HTML format using real API example."""
        sources_dir = db_paths['sources'] / 'member_states' / 'germany' / 'legislation'
        logs_dir = db_paths['logs']

        from tulit.client.state.germany import GermanyClient
        client = GermanyClient(str(sources_dir), str(logs_dir))

        try:
            # Using real example from API documentation:
            # https://testphase.rechtsinformationen.bund.de/v1/legislation/eli/bund/bgbl-1/1979/s1325/2020-06-19/2/deu/2020-06-19/regelungstext-1.html
            result = client.download(
                document_type='legislation',
                format='html',
                jurisdiction='bund',
                agent='bgbl-1',
                year='1979',
                natural_identifier='s1325',
                point_in_time='2020-06-19',
                version='2',
                language='deu',
                point_in_time_manifestation='2020-06-19',
                subtype='regelungstext-1'
            )
        except Exception as e:
            pytest.skip(f"Germany RIS API unavailable: {e}")

        assert result is not None, "Download failed"
        assert os.path.exists(result), f"Downloaded file not found: {result}"

        # Verify file content
        with open(result, 'r', encoding='utf-8') as f:
            content = f.read()
            assert len(content) > 100, f"Downloaded file seems too small"
            assert '<!DOCTYPE html' in content or '<html' in content, "File doesn't contain HTML"

    @pytest.mark.slow
    def test_germany_download_legislation_xml(self, db_paths):
        """Test downloading German legislation in XML format using real API example."""
        sources_dir = db_paths['sources'] / 'member_states' / 'germany' / 'legislation'
        logs_dir = db_paths['logs']

        from tulit.client.state.germany import GermanyClient
        client = GermanyClient(str(sources_dir), str(logs_dir))

        try:
            # Using real example from API documentation:
            # https://testphase.rechtsinformationen.bund.de/v1/legislation/eli/bund/bgbl-1/1979/s1325/2020-06-19/2/deu/2020-06-19/regelungstext-1.xml
            result = client.download(
                document_type='legislation',
                format='xml',
                jurisdiction='bund',
                agent='bgbl-1',
                year='1979',
                natural_identifier='s1325',
                point_in_time='2020-06-19',
                version='2',
                language='deu',
                point_in_time_manifestation='2020-06-19',
                subtype='regelungstext-1'
            )
        except Exception as e:
            pytest.skip(f"Germany RIS API unavailable: {e}")

        assert result is not None, "Download failed"
        assert os.path.exists(result), f"Downloaded file not found: {result}"

        # Verify file content
        with open(result, 'r', encoding='utf-8') as f:
            content = f.read()
            assert len(content) > 100, f"Downloaded file seems too small"
            assert '<?xml' in content, "File doesn't contain XML"

    @pytest.mark.slow
    def test_germany_download_case_law_html(self, db_paths):
        """Test downloading German case law in HTML format using real API example."""
        sources_dir = db_paths['sources'] / 'member_states' / 'germany' / 'case_law'
        logs_dir = db_paths['logs']

        from tulit.client.state.germany import GermanyClient
        client = GermanyClient(str(sources_dir), str(logs_dir))

        try:
            # Using real example from API documentation:
            # https://testphase.rechtsinformationen.bund.de/v1/case-law/STRE201770751.html
            result = client.download(
                document_type='case_law',
                format='html',
                document_number='STRE201770751'
            )
        except Exception as e:
            pytest.skip(f"Germany RIS API unavailable: {e}")

        assert result is not None, "Download failed"
        assert os.path.exists(result), f"Downloaded file not found: {result}"

        # Verify file content
        with open(result, 'r', encoding='utf-8') as f:
            content = f.read()
            assert len(content) > 100, f"Downloaded file seems too small"
            assert '<!DOCTYPE html' in content or '<html' in content, "File doesn't contain HTML"

    @pytest.mark.slow
    def test_germany_download_case_law_xml(self, db_paths):
        """Test downloading German case law in XML format using real API example."""
        sources_dir = db_paths['sources'] / 'member_states' / 'germany' / 'case_law'
        logs_dir = db_paths['logs']

        from tulit.client.state.germany import GermanyClient
        client = GermanyClient(str(sources_dir), str(logs_dir))

        try:
            # Using real example from API documentation:
            # https://testphase.rechtsinformationen.bund.de/v1/case-law/STRE201770751.xml
            result = client.download(
                document_type='case_law',
                format='xml',
                document_number='STRE201770751'
            )
        except Exception as e:
            pytest.skip(f"Germany RIS API unavailable: {e}")

        assert result is not None, "Download failed"
        assert os.path.exists(result), f"Downloaded file not found: {result}"

        # Verify file content
        with open(result, 'r', encoding='utf-8') as f:
            content = f.read()
            assert len(content) > 100, f"Downloaded file seems too small"
            assert '<?xml' in content, "File doesn't contain XML"

    @pytest.mark.slow
    def test_germany_download_literature_html(self, db_paths):
        """Test downloading German literature in HTML format using real API example."""
        sources_dir = db_paths['sources'] / 'member_states' / 'germany' / 'literature'
        logs_dir = db_paths['logs']

        from tulit.client.state.germany import GermanyClient
        client = GermanyClient(str(sources_dir), str(logs_dir))

        try:
            # Using real example from API documentation:
            # https://testphase.rechtsinformationen.bund.de/v1/literature/BJLU075748788.html
            result = client.download(
                document_type='literature',
                format='html',
                document_number='BJLU075748788'
            )
        except Exception as e:
            pytest.skip(f"Germany RIS API unavailable: {e}")

        assert result is not None, "Download failed"
        assert os.path.exists(result), f"Downloaded file not found: {result}"

        # Verify file content
        with open(result, 'r', encoding='utf-8') as f:
            content = f.read()
            assert len(content) > 100, f"Downloaded file seems too small"
            assert '<!DOCTYPE html' in content or '<html' in content, "File doesn't contain HTML"

    @pytest.mark.slow
    def test_germany_download_literature_xml(self, db_paths):
        """Test downloading German literature in XML format using real API example."""
        sources_dir = db_paths['sources'] / 'member_states' / 'germany' / 'literature'
        logs_dir = db_paths['logs']

        from tulit.client.state.germany import GermanyClient
        client = GermanyClient(str(sources_dir), str(logs_dir))

        try:
            # Using real example from API documentation:
            # https://testphase.rechtsinformationen.bund.de/v1/literature/BJLU075748788.xml
            result = client.download(
                document_type='literature',
                format='xml',
                document_number='BJLU075748788'
            )
        except Exception as e:
            pytest.skip(f"Germany RIS API unavailable: {e}")

        assert result is not None, "Download failed"
        assert os.path.exists(result), f"Downloaded file not found: {result}"

        # Verify file content
        with open(result, 'r', encoding='utf-8') as f:
            content = f.read()
            assert len(content) > 100, f"Downloaded file seems too small"
            assert '<?xml' in content, "File doesn't contain XML"

    @pytest.mark.slow
    def test_germany_download_eli_html(self, db_paths):
        """Test downloading German documents using ELI URL in HTML format."""
        sources_dir = db_paths['sources'] / 'member_states' / 'germany' / 'eli'
        logs_dir = db_paths['logs']

        from tulit.client.state.germany import GermanyClient
        client = GermanyClient(str(sources_dir), str(logs_dir))

        try:
            # Using a sample ELI URL
            eli_url = "/eli/bgbl-1/2024/123/2024-01-01/gesetz"
            result = client.download(
                document_type='eli',
                format='html',
                eli_url=eli_url
            )
        except Exception as e:
            pytest.skip(f"Germany RIS API unavailable: {e}")

        assert result is not None, "Download failed"
        assert os.path.exists(result), f"Downloaded file not found: {result}"

        # Verify file content
        with open(result, 'r', encoding='utf-8') as f:
            content = f.read()
            assert len(content) > 100, f"Downloaded file seems too small"
            assert '<!DOCTYPE html' in content or '<html' in content, "File doesn't contain HTML"

    @pytest.mark.slow
    def test_germany_download_eli_xml(self, db_paths):
        """Test downloading German documents using ELI URL in XML format."""
        sources_dir = db_paths['sources'] / 'member_states' / 'germany' / 'eli'
        logs_dir = db_paths['logs']

        from tulit.client.state.germany import GermanyClient
        client = GermanyClient(str(sources_dir), str(logs_dir))

        try:
            # Using a sample ELI URL
            eli_url = "/eli/bgbl-1/2024/123/2024-01-01/gesetz"
            result = client.download(
                document_type='eli',
                format='xml',
                eli_url=eli_url
            )
        except Exception as e:
            pytest.skip(f"Germany RIS API unavailable: {e}")

        assert result is not None, "Download failed"
        assert os.path.exists(result), f"Downloaded file not found: {result}"

        # Verify file content
        with open(result, 'r', encoding='utf-8') as f:
            content = f.read()
            assert len(content) > 100, f"Downloaded file seems too small"
            assert '<?xml' in content, "File doesn't contain XML"

    def test_germany_invalid_document_type(self, db_paths):
        """Test error handling for invalid document type."""
        sources_dir = db_paths['sources'] / 'member_states' / 'germany'
        logs_dir = db_paths['logs']

        from tulit.client.state.germany import GermanyClient
        client = GermanyClient(str(sources_dir), str(logs_dir))

        with pytest.raises(ValueError, match="Unknown document_type"):
            client.download(document_type='invalid_type')

    def test_germany_literature_zip_not_supported(self, db_paths):
        """Test that literature doesn't support ZIP format."""
        sources_dir = db_paths['sources'] / 'member_states' / 'germany'
        logs_dir = db_paths['logs']

        from tulit.client.state.germany import GermanyClient
        client = GermanyClient(str(sources_dir), str(logs_dir))

        with pytest.raises(ValueError, match="Literature does not support ZIP format"):
            client.download(
                document_type='literature',
                format='zip',
                document_number='LIT123456'
            )