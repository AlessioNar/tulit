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
    
    # ===== LEGISLATION TESTS =====
    
    @pytest.mark.skip(reason="German RIS test server returns no results - external test data may have changed")
    def test_search_legislation(self, client):
        """Test searching for legislation."""
        results = client.search_legislation(
            search_term="Kakaoverordnung",
            size=5
        )
        
        assert results is not None
        assert 'totalItems' in results
        assert results['totalItems'] > 0
        print(f"Found {results['totalItems']} legislation items")
        
        if results['member']:
            first_item = results['member'][0]['item']
            print(f"First result: {first_item.get('name', 'N/A')}")
    
    @pytest.mark.skip(reason="German RIS test server returns 404 - test document no longer available")
    def test_download_legislation_html(self, client):
        """Test downloading legislation as HTML."""
        # Using the example from the API documentation
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
        print(f"Downloaded legislation HTML to: {file_path}")
    
    @pytest.mark.skip(reason="German RIS test server returns 404 - test document no longer available")
    def test_download_legislation_xml(self, client):
        """Test downloading legislation as XML."""
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
        print(f"Downloaded legislation XML to: {file_path}")
    
    @pytest.mark.skip(reason="German RIS test server returns 404 - test document no longer available")
    def test_download_legislation_zip(self, client):
        """Test downloading legislation as ZIP."""
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
        print(f"Downloaded legislation ZIP to: {file_path}")
    
    @pytest.mark.skip(reason="German RIS test server returns 404 - test document no longer available")
    def test_get_legislation_metadata(self, client):
        """Test retrieving legislation metadata."""
        metadata = client.get_legislation_metadata(
            jurisdiction='bund',
            agent='bgbl-1',
            year='1979',
            natural_identifier='s1325',
            point_in_time='2020-06-19',
            version=2,
            language='deu'
        )
        
        assert metadata is not None
        assert 'name' in metadata or 'legislationIdentifier' in metadata
        print(f"Legislation metadata: {metadata.get('name', 'N/A')}")
    
    @pytest.mark.skip(reason="German RIS test server returns 404 - test document no longer available")
    def test_download_from_eli_url(self, client):
        """Test downloading from a full ELI URL."""
        eli_url = "https://testphase.rechtsinformationen.bund.de/v1/legislation/eli/bund/bgbl-1/1979/s1325/2020-06-19/2/deu/2020-06-19/regelungstext-1.html"
        
        file_path = client.download_from_eli(eli_url, fmt='html')
        
        assert file_path is not None
        assert os.path.exists(file_path)
        print(f"Downloaded from ELI URL to: {file_path}")
    
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
    
    @pytest.mark.skip(reason="German RIS test server returns 404 - test document no longer available")
    def test_download_case_law_html(self, client):
        """Test downloading case law as HTML."""
        # Using the example document number from the API documentation
        file_path = client.download_case_law_html('STRE201770751')
        
        assert file_path is not None
        assert os.path.exists(file_path)
        print(f"Downloaded case law HTML to: {file_path}")
    
    @pytest.mark.skip(reason="German RIS test server returns 404 - test document no longer available")
    def test_download_case_law_xml(self, client):
        """Test downloading case law as XML."""
        file_path = client.download_case_law_xml('STRE201770751')
        
        assert file_path is not None
        assert os.path.exists(file_path)
        print(f"Downloaded case law XML to: {file_path}")
    
    @pytest.mark.skip(reason="German RIS test server returns 404 - test document no longer available")
    def test_download_case_law_zip(self, client):
        """Test downloading case law as ZIP."""
        file_path = client.download_case_law_zip('STRE201770751')
        
        assert file_path is not None
        assert os.path.exists(file_path)
        print(f"Downloaded case law ZIP to: {file_path}")
    
    @pytest.mark.skip(reason="German RIS test server returns 404 - test document no longer available")
    def test_get_case_law_metadata(self, client):
        """Test retrieving case law metadata."""
        metadata = client.get_case_law_metadata('STRE201770751')
        
        assert metadata is not None
        assert 'documentNumber' in metadata or 'headline' in metadata
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
    
    @pytest.mark.skip(reason="German RIS test server returns 404 - test document no longer available")
    def test_download_literature_html(self, client):
        """Test downloading literature as HTML."""
        # Using the example document number from the API documentation
        file_path = client.download_literature_html('BJLU075748788')
        
        assert file_path is not None
        assert os.path.exists(file_path)
        print(f"Downloaded literature HTML to: {file_path}")
    
    @pytest.mark.skip(reason="German RIS test server returns 404 - test document no longer available")
    def test_download_literature_xml(self, client):
        """Test downloading literature as XML."""
        file_path = client.download_literature_xml('BJLU075748788')
        
        assert file_path is not None
        assert os.path.exists(file_path)
        print(f"Downloaded literature XML to: {file_path}")
    
    @pytest.mark.skip(reason="German RIS test server returns 404 - test document no longer available")
    def test_get_literature_metadata(self, client):
        """Test retrieving literature metadata."""
        metadata = client.get_literature_metadata('BJLU075748788')
        
        assert metadata is not None
        assert 'documentNumber' in metadata or 'headline' in metadata
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
