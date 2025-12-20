import unittest
from unittest.mock import patch, Mock
import os
import tempfile
from tulit.client.regional.veneto import VenetoClient

class TestVenetoClient(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.download_dir = os.path.join(self.temp_dir, 'downloads')
        self.log_dir = os.path.join(self.temp_dir, 'logs')
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        self.client = VenetoClient(download_dir=self.download_dir, log_dir=self.log_dir)

    def tearDown(self):
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir)

    @patch('tulit.client.regional.veneto.requests.get')
    def test_download_success_no_fmt(self, mock_get):
        """Test successful HTML retrieval without format validation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html>Test content</html>'
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.client.download("https://example.com")

        self.assertEqual(result, '<html>Test content</html>')
        mock_get.assert_called_once_with("https://example.com")

    @patch('tulit.client.regional.veneto.requests.get')
    def test_download_success_html_fmt_valid(self, mock_get):
        """Test successful HTML retrieval with valid HTML format validation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html>Test content</html>'
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.client.download("https://example.com", fmt='html')

        self.assertEqual(result, '<html>Test content</html>')
        mock_get.assert_called_once_with("https://example.com")

    @patch('tulit.client.regional.veneto.requests.get')
    def test_download_success_xml_fmt_valid(self, mock_get):
        """Test successful XML retrieval with valid XML format validation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<xml>Test content</xml>'
        mock_response.headers = {'Content-Type': 'application/xml'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.client.download("https://example.com", fmt='xml')

        self.assertEqual(result, '<xml>Test content</xml>')
        mock_get.assert_called_once_with("https://example.com")

    @patch('tulit.client.regional.veneto.requests.get')
    def test_download_success_pdf_fmt_valid(self, mock_get):
        """Test successful PDF retrieval with valid PDF format validation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '%PDF-1.4 Test content'
        mock_response.headers = {'Content-Type': 'application/pdf'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.client.download("https://example.com", fmt='pdf')

        self.assertEqual(result, '%PDF-1.4 Test content')
        mock_get.assert_called_once_with("https://example.com")

    @patch('tulit.client.regional.veneto.requests.get')
    def test_download_html_fmt_invalid(self, mock_get):
        """Test HTML retrieval with invalid content type for HTML format."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'Test content'
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with self.assertRaises(SystemExit):
            self.client.download("https://example.com", fmt='html')

    @patch('tulit.client.regional.veneto.requests.get')
    def test_download_xml_fmt_invalid(self, mock_get):
        """Test XML retrieval with invalid content type for XML format."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'Test content'
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with self.assertRaises(SystemExit):
            self.client.download("https://example.com", fmt='xml')

    @patch('tulit.client.regional.veneto.requests.get')
    def test_download_pdf_fmt_invalid(self, mock_get):
        """Test PDF retrieval with invalid content type for PDF format."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'Test content'
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with self.assertRaises(SystemExit):
            self.client.download("https://example.com", fmt='pdf')

    @patch('tulit.client.regional.veneto.requests.get')
    def test_download_request_exception(self, mock_get):
        """Test handling of RequestException."""
        from requests import RequestException
        mock_get.side_effect = RequestException("Network error")

        result = self.client.download("https://example.com")

        self.assertIsNone(result)
        mock_get.assert_called_once_with("https://example.com")

    @patch('tulit.client.regional.veneto.requests.get')
    def test_download_http_error(self, mock_get):
        """Test handling of HTTP errors."""
        from requests.exceptions import HTTPError
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = HTTPError("404 Client Error")
        mock_get.return_value = mock_response

        result = self.client.download("https://example.com")

        self.assertIsNone(result)
        mock_get.assert_called_once_with("https://example.com")

if __name__ == "__main__":
    unittest.main()