import unittest
import json
from tulit.client.cellar import CellarClient
import os
from unittest.mock import patch, Mock
import requests
import io

from tests.unittests.conftest import locate_data_dir

class TestCellarClient(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        data_root = locate_data_dir(__file__)
        self.downloader = CellarClient(download_dir=str(data_root / 'formex'), log_dir=str(data_root.parent / 'logs'), proxies=None)
                
    def test_download(self):
        celex = "32008R1137"
        
        # Download the documents                           
        document_paths = self.downloader.download(celex, format='fmx4')

        data_root = locate_data_dir(__file__)
        expected = [
            str(data_root / 'formex' / 'e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.04' / 'DOC_1.xml'),
            str(data_root / 'formex' / 'e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.04' / 'DOC_2.xml'),
            str(data_root / 'formex' / 'e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.04' / 'DOC_3.xml'),
            str(data_root / 'formex' / 'e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.04' / 'DOC_4.xml'),
        ]

        self.assertEqual(document_paths, expected)
    
    def test_get_cellar_ids_from_json_results(self):
        
        from tests.unittests.conftest import locate_tests_dir
        tests_root = locate_tests_dir(__file__)
        with open(tests_root / 'metadata' / 'query_results' / 'query_results.json', 'r') as f:
            cellar_results = json.loads(f.read())
        
        data_root = locate_data_dir(__file__)
        self.downloader = CellarClient(download_dir=str(data_root / 'formex'), log_dir=str(tests_root / 'logs'))
        
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

        # Check that the request was made with the correct URL
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        self.assertEqual(call_args[0][0], "GET")
        self.assertEqual(call_args[0][1], url)

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

    def test_send_sparql_query(self):    
        sparql_query = """
        PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
        PREFIX purl: <http://purl.org/dc/elements/1.1/>

        SELECT DISTINCT ?cellarURIs, ?manif, ?format, ?expr
        WHERE {
                ?work owl:sameAs <http://publications.europa.eu/resource/celex/{CELEX}> .
                ?expr cdm:expression_belongs_to_work ?work ;
                cdm:expression_uses_language ?lang .
                ?lang purl:identifier ?langCode .
                ?manif cdm:manifestation_manifests_expression ?expr;
                cdm:manifestation_type ?format.
                ?cellarURIs cdm:item_belongs_to_manifestation ?manif.
        FILTER(str(?format)="fmx4" && str(?langCode)="ENG")
        }
        ORDER BY ?cellarURIs
        LIMIT 10
        """    
        celex = "32024R0903"
        # Send query
        response = self.downloader.send_sparql_query(sparql_query=sparql_query, celex=celex)        
        
        # Check response structure and key fields (API may return 'literal' or 'typed-literal')
        self.assertIn('head', response)
        self.assertIn('results', response)
        self.assertIn('bindings', response['results'])
        self.assertGreater(len(response['results']['bindings']), 0)
        
        # Check first binding has expected fields
        first_binding = response['results']['bindings'][0]
        self.assertIn('cellarURIs', first_binding)
        self.assertIn('format', first_binding)
        self.assertEqual(first_binding['format']['value'], 'fmx4')

if __name__ == "__main__":
    unittest.main()