import unittest
import json
from tulit.client.cellar import CellarClient
import os
from unittest.mock import patch, Mock
import requests
import io

class TestCellarClient(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.downloader = CellarClient(download_dir='./tests/data', log_dir='./tests/logs')
                
    def test_download_documents(self):
        
        # Load the JSON data
        with open('./tests/metadata/query_results/query_results.json', 'r') as f:
            results = json.loads(f.read())  # Load the JSON data 
                
        # Download the documents                           
        document_paths = self.downloader.download(results, format='fmx4')

        expected = ['tests\\data\\e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.04\\DOC_1.xml', 'tests\\data\\e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.04\\DOC_2.xml', 'tests\\data\\e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.04\\DOC_3.xml', 'tests\\data\\e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.04\\DOC_4.xml']
        
        self.assertEqual(document_paths, expected)
    
    def test_get_cellar_ids_from_json_results(self):
        
        with open('./tests/metadata/query_results/query_results.json', 'r') as f:
            cellar_results = json.loads(f.read())
        
        self.downloader = CellarClient(download_dir='./tests/data', log_dir='./tests/logs')
        
        # Test for formex format
        extracted_ids = self.downloader.get_cellar_ids_from_json_results(cellar_results, 'fmx4')
        expected = [
            'e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.04/DOC_1', 'e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.04/DOC_2', 'e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.04/DOC_3', 'e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.04/DOC_4'
            ]
        
        self.assertEqual(extracted_ids, expected)

    def test_build_request_url(self):

        params = {'cellar': 'e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.04/DOC_1'}
        expected_url = 'http://publications.europa.eu/resource/cellar/e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.04/DOC_1'
        actual_url = self.downloader.build_request_url(params)
        self.assertEqual(actual_url, expected_url)
    
    @patch('tulit.client.client.requests.request')
    def test_fetch_content(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        url = 'http://publications.europa.eu/resource/cellar/e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.04/DOC_1'
        response = self.downloader.fetch_content(url)

        # Check that the request was made with the correct URL and headers
        headers = {
            'Accept': "*, application/zip, application/zip;mtype=fmx4, application/xml;mtype=fmx4, application/xhtml+xml, text/html, text/html;type=simplified, application/msword, text/plain, application/xml, application/xml;notice=object",
            'Accept-Language': "eng",
            'Content-Type': "application/x-www-form-urlencoded",
            'Host': "publications.europa.eu"
        }
        mock_request.assert_called_once_with("GET", url, headers=headers)

        # Check that the response is as expected
        self.assertEqual(response, mock_response)

    @patch('tulit.client.client.requests.request')
    def test_fetch_content_request_exception(self, mock_request):
        # Mock request to raise a RequestException
        mock_request.side_effect = requests.RequestException("Error sending GET request")

        url = 'http://publications.europa.eu/resource/cellar/e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.04/DOC_1'
        response = self.downloader.fetch_content(url)

        # Check that the response is None when an exception is raised
        self.assertIsNone(response)



if __name__ == "__main__":
    unittest.main()