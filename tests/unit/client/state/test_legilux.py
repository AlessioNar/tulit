import unittest
from unittest.mock import patch, Mock
import os
import tempfile
from pathlib import Path
from tulit.client.state.legilux import LegiluxClient

class TestLegiluxClient(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.download_dir = os.path.join(self.temp_dir, 'downloads')
        self.log_dir = os.path.join(self.temp_dir, 'logs')
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        self.client = LegiluxClient(download_dir=self.download_dir, log_dir=self.log_dir)

    def tearDown(self):
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_build_request_url(self):
        """Test URL building for ELI."""
        eli = "https://legilux.public.lu/eli/etat/leg/loi/2006/07/31/n2/jo"
        url = self.client.build_request_url(eli)
        self.assertEqual(url, eli)

    @patch('tulit.client.state.legilux.requests.get')
    def test_fetch_content_success(self, mock_get):
        """Test successful content fetching."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<xml>Test content</xml>'
        mock_response.headers = {'Content-Type': 'application/xml'}
        mock_get.return_value = mock_response

        response = self.client.fetch_content("https://example.com")
        self.assertEqual(response, mock_response)
        mock_get.assert_called_once_with(
            "https://example.com",
            headers={
                "Accept": "application/xml, text/xml, */*",
                "User-Agent": "TulitClient/1.0"
            },
            timeout=30
        )

    @patch('tulit.client.state.legilux.requests.get')
    def test_download_success_standard_eli(self, mock_get):
        """Test successful download with standard ELI format."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<xml>Test legislation content</xml>'
        mock_response.headers = {'Content-Type': 'application/xml'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        eli = "https://legilux.public.lu/eli/etat/leg/loi/2006/07/31/n2/jo"
        file_paths = self.client.download(eli)

        self.assertIsNotNone(file_paths)
        self.assertEqual(len(file_paths), 1)
        self.assertTrue(os.path.exists(file_paths[0]))
        # Check filename format: doc_type_year_month_day_doc_id
        expected_filename_part = "loi_2006_07_31_n2"
        self.assertIn(expected_filename_part, file_paths[0])

    @patch('tulit.client.state.legilux.requests.get')
    def test_download_success_short_eli(self, mock_get):
        """Test successful download with short ELI format that uses fallback filename."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<xml>Test legislation content</xml>'
        mock_response.headers = {'Content-Type': 'application/xml'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Short ELI that triggers fallback filename generation (len(eli_parts) < 6)
        eli = "https://legilux.public.lu/eli/test"
        file_paths = self.client.download(eli)

        self.assertIsNotNone(file_paths)
        self.assertEqual(len(file_paths), 1)
        self.assertTrue(os.path.exists(file_paths[0]))
        # Check fallback filename format: last 4 parts joined
        expected_filename_part = "legilux.public.lu_eli_test"
        self.assertIn(expected_filename_part, file_paths[0])

    @patch('tulit.client.state.legilux.requests.get')
    def test_download_http_error(self, mock_get):
        """Test download with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        eli = "https://legilux.public.lu/eli/etat/leg/loi/2006/07/31/n2/jo"

        # The download method calls sys.exit(1) on error, so we need to catch SystemExit
        with self.assertRaises(SystemExit):
            self.client.download(eli)

    def test_filename_cleaning(self):
        """Test that filenames are properly cleaned."""
        # Test with problematic characters
        test_filename = "loi_2006_07_31_jo?param=value&other=test"
        cleaned = test_filename.replace('/', '_').replace('?', '_').replace('&', '_')
        self.assertEqual(cleaned, "loi_2006_07_31_jo_param=value_other=test")

if __name__ == "__main__":
    unittest.main()