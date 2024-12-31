import unittest
from unittest.mock import patch, Mock
import os
from tulit.client.client import Client


class TestClient(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.downloader = Client(download_dir='./tests/data', log_dir='./tests/logs')
        
    def test_get_extension_from_content_type(self):
        content_type_mapping = {
            'text/html': 'html',
            'application/json': 'json',
            'application/xml': 'xml',
            'text/plain': 'txt',
            'application/zip': 'zip'
        }
        for content_type, expected_extension in content_type_mapping.items():
            actual_extension = self.downloader.get_extension_from_content_type(content_type)
            self.assertEqual(actual_extension, expected_extension)

    @patch('tulit.client.client.zipfile.ZipFile')
    def test_extract_zip(self, mock_zipfile):
        # Mock zipfile object
        mock_zip = Mock()
        mock_zipfile.return_value = mock_zip

        response = Mock()
        response.content = b'fake zip content'

        folder_path = './downloads/test_folder'
        self.downloader.extract_zip(response, folder_path)

        # Check that the zipfile was opened and extracted
        args, kwargs = mock_zipfile.call_args
        self.assertEqual(args[0].getvalue(), response.content)
        mock_zip.extractall.assert_called_once_with(folder_path)
    
    @patch('tulit.client.client.Client.extract_zip')
    @patch('tulit.client.client.os.makedirs')
    def test_handle_response(self, mock_makedirs, mock_extract_zip):
        # Mock response object
        response = Mock()
        response.headers = {'Content-Type': 'application/zip'}
        response.content = b'fake zip content'

        cellar_id = 'e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.04\\DOC_1'
        target_path = os.path.join(self.downloader.download_dir, cellar_id)

        # Test handling zip content
        result = self.downloader.handle_response(response, cellar_id)
        mock_extract_zip.assert_called_once_with(response, target_path)
        self.assertEqual(result, target_path)

        # Test handling non-zip content
        response.headers = {'Content-Type': 'application/xml'}
        mock_extract_zip.reset_mock()
        result = self.downloader.handle_response(response, cellar_id)
        expected_file_path = os.path.normpath(f"{target_path}.xml")
        self.assertEqual(os.path.normpath(result), expected_file_path)



if __name__ == "__main__":
    unittest.main()