import unittest
from unittest.mock import patch, Mock
import os
from tulit.client.irishstatutebook import IrishStatuteBookClient

class TestIrishStatuteBookClient(unittest.TestCase):
    def setUp(self):
        self.download_dir = './tests/data/isb'
        self.log_dir = './tests/logs'
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        self.client = IrishStatuteBookClient(download_dir=self.download_dir, log_dir=self.log_dir)

    @patch('tulit.client.irishstatutebook.requests.Session.get')
    def test_get_act_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<akomaNtoso>Irish Test</akomaNtoso>'
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        file_path = self.client.get_act(year=2012, act_number=10)
        self.assertTrue(os.path.exists(file_path))
        with open(file_path, 'rb') as f:
            content = f.read()
        self.assertIn(b'Irish Test', content)
        os.remove(file_path)

    @patch('tulit.client.irishstatutebook.requests.Session.get')
    def test_get_act_http_error(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception('HTTP error')
        mock_get.return_value = mock_response
        file_path = self.client.get_act(year=2012, act_number=999999)
        self.assertIsNone(file_path)

if __name__ == "__main__":
    unittest.main()
