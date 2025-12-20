import unittest
from unittest.mock import patch, Mock
import os
from tulit.client.state.finlex import FinlexClient
from tests.conftest import locate_data_dir, locate_tests_dir

class TestFinlexClient(unittest.TestCase):
    def setUp(self):
        data_root = locate_data_dir(__file__)
        tests_root = locate_tests_dir(__file__)
        self.download_dir = str(data_root / 'finlex')
        self.log_dir = str(tests_root / 'logs')
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        self.client = FinlexClient(download_dir=self.download_dir, log_dir=self.log_dir)

    @patch('tulit.client.state.finlex.requests.Session.get')
    def test_get_statute_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<akn:akomaNtoso>Test</akn:akomaNtoso>'
        mock_response.headers = {'Content-Type': 'application/xml'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        file_path = self.client.get_statute(year=2024, number=123)
        self.assertTrue(os.path.exists(file_path))
        with open(file_path, 'rb') as f:
            content = f.read()
        self.assertIn(b'Test', content)
        os.remove(file_path)

    @patch('tulit.client.state.finlex.requests.Session.get')
    def test_get_statute_http_error(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception('HTTP error')
        mock_get.return_value = mock_response
        file_path = self.client.get_statute(year=2024, number=999999)
        self.assertIsNone(file_path)

    @patch('tulit.client.state.finlex.requests.Session.get')
    def test_get_statute_pdf_format(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'%PDF-1.4 test content'
        mock_response.headers = {'Content-Type': 'application/pdf'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        file_path = self.client.get_statute(year=2024, number=123, fmt='pdf')
        self.assertTrue(os.path.exists(file_path))
        self.assertTrue(file_path.endswith('.pdf'))
        with open(file_path, 'rb') as f:
            content = f.read()
        self.assertIn(b'%PDF', content)
        os.remove(file_path)

    @patch('tulit.client.state.finlex.requests.Session.get')
    def test_get_statute_html_format(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<html><body>Test HTML</body></html>'
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        file_path = self.client.get_statute(year=2024, number=123, fmt='html')
        self.assertTrue(os.path.exists(file_path))
        self.assertTrue(file_path.endswith('.html'))
        with open(file_path, 'rb') as f:
            content = f.read()
        self.assertIn(b'HTML', content)
        os.remove(file_path)

    @patch('tulit.client.state.finlex.requests.Session.get')
    def test_get_statute_wrong_content_type_xml(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'test content'
        mock_response.headers = {'Content-Type': 'text/plain'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Should exit with code 1 for wrong content type
        with self.assertRaises(SystemExit):
            self.client.get_statute(year=2024, number=123, fmt='xml')

    @patch('tulit.client.state.finlex.requests.Session.get')
    def test_get_statute_wrong_content_type_pdf(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'test content'
        mock_response.headers = {'Content-Type': 'text/plain'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with self.assertRaises(SystemExit):
            self.client.get_statute(year=2024, number=123, fmt='pdf')

    @patch('tulit.client.state.finlex.requests.Session.get')
    def test_get_statute_network_error(self, mock_get):
        mock_get.side_effect = Exception('Network error')
        file_path = self.client.get_statute(year=2024, number=123)
        self.assertIsNone(file_path)

    @patch('tulit.client.state.finlex.requests.Session.get')
    def test_get_statute_with_proxies(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<akn:akomaNtoso>Test</akn:akomaNtoso>'
        mock_response.headers = {'Content-Type': 'application/xml'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Test with proxies
        client_with_proxies = FinlexClient(
            download_dir=self.download_dir, 
            log_dir=self.log_dir, 
            proxies={'http': 'http://proxy.example.com:8080'}
        )
        file_path = client_with_proxies.get_statute(year=2024, number=123)
        self.assertTrue(os.path.exists(file_path))
        os.remove(file_path)

if __name__ == "__main__":
    unittest.main()
