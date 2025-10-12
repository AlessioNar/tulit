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
        self.downloader = CellarClient(download_dir='./tests/data/formex', log_dir='./tests/logs', proxies=None)
                
    def test_download(self):
        celex = "32008R1137"
        
        # Download the documents                           
        document_paths = self.downloader.download(celex, format='fmx4')

        expected = ['tests\\data\\formex\\e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.04\\DOC_1.xml', 'tests\\data\\formex\\e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.04\\DOC_2.xml', 'tests\\data\\formex\\e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.04\\DOC_3.xml', 'tests\\data\\formex\\e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.04\\DOC_4.xml']
        
        self.assertEqual(document_paths, expected)
    
    def test_get_cellar_ids_from_json_results(self):
        
        with open('./tests/metadata/query_results/query_results.json', 'r') as f:
            cellar_results = json.loads(f.read())
        
        self.downloader = CellarClient(download_dir='./tests/data/formex', log_dir='./tests/logs')
        
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
        expected_results = json.loads('''{"head": {"link": [], "vars": ["cellarURIs", "manif", "format", "expr"]}, "results": {"distinct": false, "ordered": true, "bindings": [{"cellarURIs": {"type": "uri", "value": "http://publications.europa.eu/resource/cellar/c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.02/DOC_1"}, "manif": {"type": "uri", "value": "http://publications.europa.eu/resource/cellar/c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.02"}, "format": {"type": "typed-literal", "datatype": "http://www.w3.org/2001/XMLSchema#string", "value": "fmx4"}, "expr": {"type": "uri", "value": "http://publications.europa.eu/resource/cellar/c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006"}}]}}''')        
        self.assertEqual(response, expected_results)

if __name__ == "__main__":
    unittest.main()