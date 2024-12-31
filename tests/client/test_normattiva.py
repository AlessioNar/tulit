import unittest

from unittest.mock import patch, Mock
from tulit.client.normattiva import NormattivaClient

class TestNormattivaClient(unittest.TestCase):
    def setUp(self):
        self.downloader = NormattivaClient(download_dir='./tests/data/akn/italy', log_dir='./tests/logs')
    
    @patch('tulit.client.normattiva.requests.get')
    def test_build_request_url(self, mock_get):
        params = {
            'dataGU': '20210101',
            'codiceRedaz': '12345',
            'dataVigenza': '20211231',
            'date': '2021/01/01'
        }
        uri, url = self.downloader.build_request_url(params)
        expected_uri = "https://www.normattiva.it/eli/id/2021/01/01//12345/CONSOLIDATED"
        expected_url = "https://www.normattiva.it/do/atto/caricaAKN?dataGU=20210101&codiceRedaz=12345&dataVigenza=20211231"
        self.assertEqual(uri, expected_uri)
        self.assertEqual(url, expected_url)
    
    @patch('tulit.client.normattiva.requests.get')
    def test_fetch_content(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.cookies = {'cookie_key': 'cookie_value'}
        mock_get.return_value = mock_response
        
        uri = "https://www.normattiva.it/eli/id/2021/01/01//12345/CONSOLIDATED"
        url = "https://www.normattiva.it/do/atto/caricaAKN?dataGU=20210101&codiceRedaz=12345&dataVigenza=20211231"
        
        response = self.downloader.fetch_content(uri, url)
        self.assertEqual(response, mock_response)
    
    @patch('tulit.client.normattiva.requests.get')
    @patch('tulit.client.normattiva.NormattivaClient.handle_response')
    def test_download(self, mock_handle_response, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.headers = {'Content-Type': 'application/xml'}
        mock_get.return_value = mock_response
        mock_handle_response.return_value = './tests/data/akn/italy/20210101_12345_VIGENZA_20211231.xml'
        
        document_paths = self.downloader.download(dataGU='20210101', codiceRedaz='12345', dataVigenza='20211231')
        expected_paths = ['./tests/data/akn/italy/20210101_12345_VIGENZA_20211231.xml']
        self.assertEqual(document_paths, expected_paths)

if __name__ == "__main__":
    unittest.main()

