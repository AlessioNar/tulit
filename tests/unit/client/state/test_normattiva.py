import unittest
from unittest.mock import patch, Mock
from tulit.client.state.normattiva import NormattivaClient

from tests.conftest import locate_data_dir, locate_tests_dir

class TestNormattivaClient(unittest.TestCase):
    def setUp(self):
        data_root = locate_data_dir(__file__)
        tests_root = locate_tests_dir(__file__)
        self.downloader = NormattivaClient(download_dir=str(data_root / 'akn' / 'italy'), log_dir=str(tests_root / 'logs'))
    
    @patch('tulit.client.state.normattiva.requests.get')
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
    
    @patch('tulit.client.state.normattiva.requests.get')
    def test_fetch_content(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.cookies = {'cookie_key': 'cookie_value'}
        mock_get.return_value = mock_response
        
        uri = "https://www.normattiva.it/eli/id/2021/01/01//12345/CONSOLIDATED"
        url = "https://www.normattiva.it/do/atto/caricaAKN?dataGU=20210101&codiceRedaz=12345&dataVigenza=20211231"
        
        response = self.downloader.fetch_content(uri, url)
        self.assertEqual(response, mock_response)
    
    @patch('tulit.client.state.normattiva.requests.get')
    @patch('tulit.client.state.normattiva.NormattivaClient.handle_response')
    def test_download(self, mock_handle_response, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.headers = {'Content-Type': 'application/xml'}
        mock_get.return_value = mock_response
        expected_path = str(locate_data_dir(__file__) / 'sources' / 'member_states' / 'italy' / 'normattiva' / 'akn' / '20210101_12345_VIGENZA_20211231.xml')
        mock_handle_response.return_value = expected_path
        
        document_paths = self.downloader.download(dataGU='20210101', codiceRedaz='12345', dataVigenza='20211231')
        expected_paths = [expected_path]
        self.assertEqual(document_paths, expected_paths)

    @patch('tulit.client.state.normattiva.requests.get')
    @patch('tulit.client.state.normattiva.NormattivaClient.handle_response')
    def test_download_pdf_format(self, mock_handle_response, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.headers = {'Content-Type': 'application/pdf'}
        mock_get.return_value = mock_response
        expected_path = str(locate_data_dir(__file__) / 'sources' / 'member_states' / 'italy' / 'normattiva' / 'akn' / '20210101_12345_VIGENZA_20211231.pdf')
        mock_handle_response.return_value = expected_path
        
        document_paths = self.downloader.download(dataGU='20210101', codiceRedaz='12345', dataVigenza='20211231', fmt='pdf')
        expected_paths = [expected_path]
        self.assertEqual(document_paths, expected_paths)

    @patch('tulit.client.state.normattiva.requests.get')
    @patch('tulit.client.state.normattiva.NormattivaClient.handle_response')
    def test_download_html_format(self, mock_handle_response, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_get.return_value = mock_response
        expected_path = str(locate_data_dir(__file__) / 'sources' / 'member_states' / 'italy' / 'normattiva' / 'akn' / '20210101_12345_VIGENZA_20211231.html')
        mock_handle_response.return_value = expected_path
        
        document_paths = self.downloader.download(dataGU='20210101', codiceRedaz='12345', dataVigenza='20211231', fmt='html')
        expected_paths = [expected_path]
        self.assertEqual(document_paths, expected_paths)

    @patch('tulit.client.state.normattiva.requests.get')
    def test_download_wrong_content_type_xml(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.headers = {'Content-Type': 'text/plain'}
        mock_get.return_value = mock_response
        
        with self.assertRaises(SystemExit):
            self.downloader.download(dataGU='20210101', codiceRedaz='12345', dataVigenza='20211231', fmt='xml')

    @patch('tulit.client.state.normattiva.requests.get')
    def test_download_wrong_content_type_pdf(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.headers = {'Content-Type': 'text/plain'}
        mock_get.return_value = mock_response
        
        with self.assertRaises(SystemExit):
            self.downloader.download(dataGU='20210101', codiceRedaz='12345', dataVigenza='20211231', fmt='pdf')

    @patch('tulit.client.state.normattiva.requests.get')
    def test_fetch_content_request_exception(self, mock_get):
        from requests import RequestException
        mock_get.side_effect = RequestException('Request failed')
        response = self.downloader.fetch_content('http://example.com', 'http://example.com/data')
        self.assertIsNone(response)

    @patch('tulit.client.state.normattiva.requests.get')
    def test_fetch_content_cookie_request_fails(self, mock_get):
        from requests import RequestException
        mock_get.side_effect = [RequestException('Cookie request failed'), Mock()]
        response = self.downloader.fetch_content('http://example.com', 'http://example.com/data')
        self.assertIsNone(response)

if __name__ == "__main__":
    unittest.main()

