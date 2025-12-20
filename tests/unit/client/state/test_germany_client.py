"""
Test script for the Germany RIS client.

This script demonstrates the various capabilities of the Germany client:
- Searching and downloading legislation
- Downloading case law decisions
- Downloading literature
- Multiple format support (HTML, XML, ZIP)
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch, Mock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tulit.client.state.germany import GermanyClient


class TestGermanyClient:
    """Test suite for the Germany RIS client."""
    
    @pytest.fixture
    def client(self, tmp_path):
        """Create a client instance with temporary directories."""
        download_dir = tmp_path / "downloads"
        log_dir = tmp_path / "logs"
        return GermanyClient(
            download_dir=str(download_dir),
            log_dir=str(log_dir)
        )
    
    # ===== UNIT TESTS =====
    
    def test_build_url(self, client):
        """Test URL building."""
        # Test with relative endpoint
        url = client._build_url("legislation")
        assert url == "https://testphase.rechtsinformationen.bund.de/v1/legislation"
        
        # Test with absolute URL
        url = client._build_url("https://example.com/test")
        assert url == "https://example.com/test"
        
        # Test with leading slash
        url = client._build_url("/legislation")
        assert url == "https://testphase.rechtsinformationen.bund.de/v1/legislation"
    
    @pytest.mark.parametrize("status_code,should_raise", [
        (200, False),
        (404, True),
        (500, True),
    ])
    def test_make_request(self, client, status_code, should_raise):
        """Test HTTP request handling."""
        with patch('tulit.client.state.germany.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = status_code
            if status_code == 200:
                mock_response.raise_for_status = Mock()
            else:
                mock_response.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
            mock_get.return_value = mock_response
            
            if should_raise:
                with pytest.raises(Exception):
                    client._make_request("https://example.com")
            else:
                response = client._make_request("https://example.com")
                assert response == mock_response
    
    def test_init(self, client):
        """Test client initialization."""
        assert client.base_url == "https://testphase.rechtsinformationen.bund.de"
        assert client.api_version == "v1"
        assert hasattr(client, 'logger')
    
    def test_download_legislation_html(self, client):
        """Test downloading legislation as HTML with mock."""
        with patch('tulit.client.state.germany.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'<html><body>Test Legislation HTML</body></html>'
            mock_response.headers = {'Content-Type': 'text/html'}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            file_path = client.download_legislation_html(
                jurisdiction='bund',
                agent='bgbl-1',
                year='1979',
                natural_identifier='s1325',
                point_in_time='2020-06-19',
                version=2,
                language='deu',
                point_in_time_manifestation='2020-06-19',
                subtype='regelungstext-1'
            )
            
            assert file_path is not None
            assert os.path.exists(file_path)
            with open(file_path, 'rb') as f:
                content = f.read()
            assert b'Test Legislation HTML' in content
            os.remove(file_path)
    
    def test_download_legislation_xml(self, client):
        """Test downloading legislation as XML with mock."""
        with patch('tulit.client.state.germany.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'<?xml version="1.0"?><legislation>Test XML</legislation>'
            mock_response.headers = {'Content-Type': 'application/xml'}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            file_path = client.download_legislation_xml(
                jurisdiction='bund',
                agent='bgbl-1',
                year='1979',
                natural_identifier='s1325',
                point_in_time='2020-06-19',
                version=2,
                language='deu',
                point_in_time_manifestation='2020-06-19',
                subtype='regelungstext-1'
            )
            
            assert file_path is not None
            assert os.path.exists(file_path)
            with open(file_path, 'rb') as f:
                content = f.read()
            assert b'Test XML' in content
            os.remove(file_path)
    
    def test_download_legislation_zip(self, client):
        """Test downloading legislation as ZIP with mock."""
        with patch('tulit.client.state.germany.requests.get') as mock_get:
            # Create a valid ZIP file content in memory
            import zipfile
            import io
            
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zf:
                zf.writestr('test.txt', 'Test ZIP content')
            zip_content = zip_buffer.getvalue()
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = zip_content
            mock_response.headers = {'Content-Type': 'application/zip'}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            file_path = client.download_legislation_zip(
                jurisdiction='bund',
                agent='bgbl-1',
                year='1979',
                natural_identifier='s1325',
                point_in_time='2020-06-19',
                version=2,
                language='deu',
                point_in_time_manifestation='2020-06-19'
            )
            
            assert file_path is not None
            assert os.path.exists(file_path)
            assert os.path.isdir(file_path)  # Should be a directory after extraction
            # Check if the test file was extracted
            test_file = os.path.join(file_path, 'test.txt')
            assert os.path.exists(test_file)
            with open(test_file, 'r') as f:
                content = f.read()
            assert content == 'Test ZIP content'
            # Clean up
            import shutil
            shutil.rmtree(file_path)
    
    def test_get_legislation_metadata(self, client):
        """Test retrieving legislation metadata with mock."""
        mock_data = {
            "jurisdiction": "bund",
            "agent": "bgbl-1",
            "year": "1979",
            "naturalIdentifier": "s1325"
        }
        
        with patch('tulit.client.state.germany.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            metadata = client.get_legislation_metadata(
                jurisdiction='bund',
                agent='bgbl-1',
                year='1979',
                natural_identifier='s1325',
                point_in_time='2020-06-19',
                version=2,
                language='deu'
            )
            
            assert metadata == mock_data
            mock_get.assert_called_once()
            print(f"Legislation metadata: {metadata.get('name', 'N/A')}")
    
    def test_download_from_eli_url(self, client):
        """Test downloading from a full ELI URL with mock."""
        eli_url = "https://testphase.rechtsinformationen.bund.de/v1/legislation/eli/bund/bgbl-1/1979/s1325/2020-06-19/2/deu/2020-06-19/regelungstext-1.html"
        
        with patch('tulit.client.state.germany.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'<html><body>Test ELI Content</body></html>'
            mock_response.headers = {'Content-Type': 'text/html'}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            file_path = client.download_from_eli(eli_url, fmt='html')
            
            assert file_path is not None
            assert os.path.exists(file_path)
            with open(file_path, 'rb') as f:
                content = f.read()
            assert b'Test ELI Content' in content
            os.remove(file_path)
    
    # ===== CASE LAW TESTS =====
    
    def test_search_case_law(self, client):
        """Test searching for case law."""
        results = client.search_case_law(
            search_term="Urteil",
            size=5
        )
        
        assert results is not None
        assert 'totalItems' in results
        print(f"Found {results['totalItems']} case law items")
        
        if results['member']:
            first_item = results['member'][0]['item']
            print(f"First result: {first_item.get('headline', 'N/A')}")
    
    def test_download_case_law_html(self, client):
        """Test downloading case law as HTML with mock."""
        with patch('tulit.client.state.germany.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'<html><body>Test Case Law HTML</body></html>'
            mock_response.headers = {'Content-Type': 'text/html'}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            file_path = client.download_case_law_html('STRE201770751')
            
            assert file_path is not None
            assert os.path.exists(file_path)
            with open(file_path, 'rb') as f:
                content = f.read()
            assert b'Test Case Law HTML' in content
            os.remove(file_path)
    
    def test_download_case_law_xml(self, client):
        """Test downloading case law as XML with mock."""
        with patch('tulit.client.state.germany.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'<?xml version="1.0"?><case-law>Test XML</case-law>'
            mock_response.headers = {'Content-Type': 'application/xml'}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            file_path = client.download_case_law_xml('STRE201770751')
            
            assert file_path is not None
            assert os.path.exists(file_path)
            with open(file_path, 'rb') as f:
                content = f.read()
            assert b'Test XML' in content
            os.remove(file_path)
    
    def test_download_case_law_zip(self, client):
        """Test downloading case law as ZIP with mock."""
        with patch('tulit.client.state.germany.requests.get') as mock_get:
            # Create a valid ZIP file content in memory
            import zipfile
            import io
            
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zf:
                zf.writestr('case_law.txt', 'Test Case Law ZIP content')
            zip_content = zip_buffer.getvalue()
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = zip_content
            mock_response.headers = {'Content-Type': 'application/zip'}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            file_path = client.download_case_law_zip('STRE201770751')
            
            assert file_path is not None
            assert os.path.exists(file_path)
            assert os.path.isdir(file_path)  # Should be a directory after extraction
            # Check if the test file was extracted
            test_file = os.path.join(file_path, 'case_law.txt')
            assert os.path.exists(test_file)
            with open(test_file, 'r') as f:
                content = f.read()
            assert content == 'Test Case Law ZIP content'
            # Clean up
            import shutil
            shutil.rmtree(file_path)
    
    def test_get_case_law_metadata(self, client):
        """Test retrieving case law metadata with mock."""
        mock_data = {
            "documentNumber": "STRE201770751",
            "headline": "Test Case Law Document",
            "court": "Test Court"
        }
        
        with patch('tulit.client.state.germany.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            metadata = client.get_case_law_metadata('STRE201770751')
            
            assert metadata == mock_data
            mock_get.assert_called_once()
            print(f"Case law metadata: {metadata.get('headline', 'N/A')}")
    
    # ===== LITERATURE TESTS =====
    
    def test_search_literature(self, client):
        """Test searching for literature."""
        results = client.search_literature(
            search_term="Recht",
            size=5
        )
        
        assert results is not None
        assert 'totalItems' in results
        print(f"Found {results['totalItems']} literature items")
        
        if results['member']:
            first_item = results['member'][0]['item']
            print(f"First result: {first_item.get('headline', 'N/A')}")
    
    def test_download_literature_html(self, client):
        """Test downloading literature as HTML with mock."""
        with patch('tulit.client.state.germany.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'<html><body>Test Literature HTML</body></html>'
            mock_response.headers = {'Content-Type': 'text/html'}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            file_path = client.download_literature_html('BJLU075748788')
            
            assert file_path is not None
            assert os.path.exists(file_path)
            with open(file_path, 'rb') as f:
                content = f.read()
            assert b'Test Literature HTML' in content
            os.remove(file_path)
    
    def test_download_literature_xml(self, client):
        """Test downloading literature as XML with mock."""
        with patch('tulit.client.state.germany.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'<?xml version="1.0"?><literature>Test XML</literature>'
            mock_response.headers = {'Content-Type': 'application/xml'}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            file_path = client.download_literature_xml('BJLU075748788')
            
            assert file_path is not None
            assert os.path.exists(file_path)
            with open(file_path, 'rb') as f:
                content = f.read()
            assert b'Test XML' in content
            os.remove(file_path)
    
    def test_get_literature_metadata(self, client):
        """Test retrieving literature metadata with mock."""
        mock_data = {
            "documentNumber": "BJLU075748788",
            "headline": "Test Literature Document",
            "author": "Test Author"
        }
        
        with patch('tulit.client.state.germany.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            metadata = client.get_literature_metadata('BJLU075748788')
            
            assert metadata == mock_data
            mock_get.assert_called_once()
            print(f"Literature metadata: {metadata.get('headline', 'N/A')}")
    
    # ===== GLOBAL SEARCH TESTS =====
    
    def test_search_all_documents(self, client):
        """Test searching across all document types."""
        results = client.search_all_documents(
            search_term="Gesetz",
            size=10
        )
        
        assert results is not None
        assert 'totalItems' in results
        print(f"Found {results['totalItems']} documents across all types")
        
        if results['member']:
            for i, member in enumerate(results['member'][:5]):
                item = member['item']
                doc_type = item.get('@type', 'Unknown')
                name = item.get('name', item.get('headline', 'N/A'))
                print(f"  {i+1}. [{doc_type}] {name}")
    
    def test_search_legislation_only(self, client):
        """Test searching only legislation documents."""
        results = client.search_all_documents(
            search_term="Verordnung",
            document_kind='N',  # N for Normen (legislation)
            size=5
        )
        
        assert results is not None
        assert 'totalItems' in results
        print(f"Found {results['totalItems']} legislation documents")
    
    def test_search_case_law_only(self, client):
        """Test searching only case law documents."""
        results = client.search_all_documents(
            search_term="Urteil",
            document_kind='R',  # R for Rechtsprechung (case law)
            size=5
        )
        
        assert results is not None
        assert 'totalItems' in results
        print(f"Found {results['totalItems']} case law documents")


if __name__ == "__main__":
    """Run tests manually without pytest."""
    import tempfile
    
    print("=" * 80)
    print("Testing Germany RIS Client")
    print("=" * 80)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        download_dir = tmp_path / "downloads"
        log_dir = tmp_path / "logs"
        
        client = GermanyClient(
            download_dir=str(download_dir),
            log_dir=str(log_dir)
        )
        
        test_suite = TestGermanyClient()
        
        # Run a subset of tests
        tests_to_run = [
            ("Search Legislation", lambda: test_suite.test_search_legislation(client)),
            ("Download Legislation HTML", lambda: test_suite.test_download_legislation_html(client)),
            ("Download Case Law HTML", lambda: test_suite.test_download_case_law_html(client)),
            ("Download Literature HTML", lambda: test_suite.test_download_literature_html(client)),
            ("Search All Documents", lambda: test_suite.test_search_all_documents(client)),
        ]
        
        for test_name, test_func in tests_to_run:
            print(f"\n--- {test_name} ---")
            try:
                test_func()
                print(f"✓ {test_name} passed")
            except Exception as e:
                print(f"✗ {test_name} failed: {e}")
        
        print("\n" + "=" * 80)
        print("Test run complete")
        print("=" * 80)
