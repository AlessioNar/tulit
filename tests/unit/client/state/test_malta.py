import unittest
from unittest.mock import patch, Mock
import os
from tulit.client.state.malta import MaltaLegislationClient
from tests.conftest import locate_data_dir, locate_tests_dir

class TestMaltaLegislationClient(unittest.TestCase):
    def setUp(self):
        data_root = locate_data_dir(__file__)
        tests_root = locate_tests_dir(__file__)
        self.download_dir = str(data_root / 'malta')
        self.log_dir = str(tests_root / 'logs')
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        self.client = MaltaLegislationClient(download_dir=self.download_dir, log_dir=self.log_dir)

    @patch('tulit.client.state.malta.requests.Session.get')
    def test_download_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'%PDF-1.4 test pdf content'
        mock_response.headers = {'Content-Type': 'application/pdf'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        file_path = self.client.download('ln/2015/433', lang='mlt', fmt='pdf')
        self.assertTrue(os.path.exists(file_path))
        with open(file_path, 'rb') as f:
            content = f.read()
        self.assertIn(b'%PDF', content)
        os.remove(file_path)

    @patch('tulit.client.state.malta.requests.Session.get')
    def test_download_http_error(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception('HTTP error')
        mock_get.return_value = mock_response
        file_path = self.client.download('ln/2015/999999', lang='mlt', fmt='pdf')
        self.assertIsNone(file_path)

if __name__ == "__main__":
    unittest.main()
