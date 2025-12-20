"""
End-to-end tests for client downloads.
Tests the complete download pipeline from external APIs to local storage.
"""

import pytest
import os
from pathlib import Path
import json
import time


@pytest.mark.e2e
@pytest.mark.client_download
class TestClientDownloads:
    """Test suite for client download functionality."""

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

    # @pytest.mark.slow
    # @pytest.mark.requires_credentials
    # def test_france_legifrance_download(self, db_paths):
    #     """Test downloading from France Legifrance (requires credentials)."""
    #     # Kept on the side for now

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

    @pytest.mark.slow
    def test_germany_legislation_download(self, db_paths):
        """Test downloading German legislation."""
        sources_dir = db_paths['sources'] / 'member_states' / 'germany' / 'gesetze' / 'legislation'
        logs_dir = db_paths['logs']

        from tulit.client.state.germany import GermanyClient
        client = GermanyClient(str(sources_dir), str(logs_dir))

        try:
            result = client.download(document_type='legislation', format='xml', search='Auslandszuschlagsverordnung')
        except Exception as e:
            pytest.skip(f"Germany RIS API unavailable: {e}")

        assert result is not None, "Download failed"
        assert Path(result).exists(), f"Downloaded file not found: {result}"

        # Check file content
        content = Path(result).read_text()
        assert len(content) > 100, "Downloaded file seems too small"
        assert '<?xml' in content, "File doesn't contain XML"

    def test_veneto_download(self, db_paths):
        """Test downloading from Veneto regional authority."""
        sources_dir = db_paths['sources'] / 'regional_authorities' / 'italy' / 'veneto'

        from tulit.client.regional.veneto import VenetoClient
        client = VenetoClient(str(sources_dir), str(db_paths['logs']))

        try:
            text = client.download('https://www.consiglioveneto.it/web/crv/dettaglio-legge?numeroDocumento=10&id=69599315', fmt='html')
        except Exception as e:
            pytest.skip(f"Veneto website unavailable: {e}")

        if text is None:
            pytest.skip("Veneto website returned no content (possibly blocked)")

        assert len(text) > 1000, "Downloaded content seems too small"
        assert '<html' in text.lower(), "Content doesn't contain HTML"

        # Save to file
        html_file = sources_dir / 'veneto_law.html'
        html_file.write_text(text)
        assert html_file.exists(), "File was not saved"