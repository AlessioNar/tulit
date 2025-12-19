import unittest
from unittest.mock import patch, Mock
import os
from tulit.client.malta import MaltaLegislationClient

class TestMaltaLegislationClient(unittest.TestCase):
    def setUp(self):
        self.download_dir = './tests/data/malta'
        self.log_dir = './tests/logs'
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        self.client = MaltaLegislationClient(download_dir=self.download_dir, log_dir=self.log_dir)

    @patch('tulit.client.malta.requests.Session.get')
    def test_get_document_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'%PDF-1.4 test pdf content'
        mock_response.headers = {'Content-Type': 'application/pdf'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        file_path = self.client.get_document('ln/2015/433', lang='mlt', fmt='pdf')
        self.assertTrue(os.path.exists(file_path))
        with open(file_path, 'rb') as f:
            content = f.read()
        self.assertIn(b'%PDF', content)
        os.remove(file_path)

    @patch('tulit.client.malta.requests.Session.get')
    def test_get_document_http_error(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception('HTTP error')
        mock_get.return_value = mock_response
        file_path = self.client.get_document('ln/2015/999999', lang='mlt', fmt='pdf')
        self.assertIsNone(file_path)

if __name__ == "__main__":
    unittest.main()
