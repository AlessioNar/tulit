import unittest
from unittest.mock import patch, Mock
import os
from tulit.client.state.portugal import PortugalDREClient
from tests.conftest import locate_data_dir, locate_tests_dir

class TestPortugalDREClient(unittest.TestCase):
    def setUp(self):
        data_root = locate_data_dir(__file__)
        tests_root = locate_tests_dir(__file__)
        self.download_dir = str(data_root / 'portugal')
        self.log_dir = str(tests_root / 'logs')
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        self.client = PortugalDREClient(download_dir=self.download_dir, log_dir=self.log_dir)

    @patch('tulit.client.portugal.requests.Session.get')
    def test_get_journal_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<html>Journal</html>'
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        file_path = self.client.get_journal('1a', '1', '1991', '0', 'pt', 'html')
        self.assertTrue(os.path.exists(file_path))
        with open(file_path, 'rb') as f:
            content = f.read()
        self.assertIn(b'Journal', content)
        os.remove(file_path)

    @patch('tulit.client.portugal.requests.Session.get')
    def test_get_legal_act_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<html>Act</html>'
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        file_path = self.client.get_legal_act('lei', '39', '2016', '12', '19', 'p', 'pt', 'html')
        self.assertTrue(os.path.exists(file_path))
        with open(file_path, 'rb') as f:
            content = f.read()
        self.assertIn(b'Act', content)
        os.remove(file_path)

    @patch('tulit.client.portugal.requests.Session.get')
    def test_get_consolidated_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<html>Consolidated</html>'
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        file_path = self.client.get_consolidated('lei', '7', '2009', 'p', '20171002', 'pt', 'html')
        self.assertTrue(os.path.exists(file_path))
        with open(file_path, 'rb') as f:
            content = f.read()
        self.assertIn(b'Consolidated', content)
        os.remove(file_path)

    @patch('tulit.client.portugal.requests.Session.get')
    def test_download_http_error(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception('HTTP error')
        mock_get.return_value = mock_response
        file_path = self.client.get_journal('1a', '1', '1991', '0', 'pt', 'html')
        self.assertIsNone(file_path)

if __name__ == "__main__":
    unittest.main()
