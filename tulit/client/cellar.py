import logging
import argparse
import requests
import json
from tulit.client.client import Client
from tulit.sparql import send_sparql_query

class CellarClient(Client):
    
    def __init__(self, download_dir, log_dir, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.endpoint = 'http://publications.europa.eu/resource/cellar/'
   

    def fetch_content(self, url) -> requests.Response:
        """
        Send a GET request to download a file

        Parameters
        ----------
        url : str
            The URL to send the request to.

        Returns
        -------
        requests.Response
            The response from the server.

        Notes
        -----
        The request is sent with the following headers:
        - Accept: application/zip;mtype=fmx4, application/xml;mtype=fmx4, application/xhtml+xml, text/html, text/html;type=simplified, application/msword, text/plain, application/xml;notice=object
        - Accept-Language: eng
        - Content-Type: application/x-www-form-urlencoded
        - Host: publications.europa.eu

        Raises
        ------
        requests.RequestException
            If there is an error sending the request.

        See Also
        --------
        requests : The underlying library used for making HTTP requests.

        """
        try:
            headers = {
                'Accept': "*, application/zip, application/zip;mtype=fmx4, application/xml;mtype=fmx4, application/xhtml+xml, text/html, text/html;type=simplified, application/msword, text/plain, application/xml, application/xml;notice=object",
                'Accept-Language': "eng",
                'Content-Type': "application/x-www-form-urlencoded",
                'Host': "publications.europa.eu"
            }
            response = requests.request("GET", url, headers=headers, proxies=self.proxies)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logging.error(f"Error sending GET request: {e}")
            return None
             
    def build_request_url(self, params):
        """
        Build the request URL based on the source and parameters.
        """
        url = f"{self.endpoint}{params['cellar']}"
        
        return url
    
    def get_cellar_ids_from_json_results(self, results, format):
        """
        Extract CELLAR ids from a JSON dictionary.

        Parameters
        ----------
        cellar_results : dict
            A dictionary containing the response of the CELLAR SPARQL query

        Returns
        -------
        list
            A list of CELLAR ids.

        Notes
        -----
        The function assumes that the JSON dictionary has the following structure:
        - The dictionary contains a key "results" that maps to another dictionary.
        - The inner dictionary contains a key "bindings" that maps to a list of dictionaries.
        - Each dictionary in the list contains a key "cellarURIs" that maps to a dictionary.
        - The innermost dictionary contains a key "value" that maps to a string representing the CELLAR URI.

        The function extracts the CELLAR id by splitting the CELLAR URI at "cellar/" and taking the second part.

        Examples
        --------
        >>> cellar_results = {
        ...     "results": {
        ...         "bindings": [
        ...             {"cellarURIs": {"value": "https://example.com/cellar/some_id"}},
        ...             {"cellarURIs": {"value": "https://example.com/cellar/another_id"}}
        ...         ]
        ...     }
        ... }
        >>> cellar_ids = get_cellar_ids_from_json_results(cellar_results)
        >>> print(cellar_ids)
        ['some_id', 'another_id']
        """
        cellar_ids = []
        results_list = results["results"]["bindings"]
        for i, file in enumerate(results_list):
            if file['format']['value'] == format:
                cellar_ids.append(file['cellarURIs']["value"].split("cellar/")[1])

        return cellar_ids

    def download(self, results, format=None):
        """
        Sends a REST query to the specified source APIs and downloads the documents
        corresponding to the given results.

        Parameters
        ----------
        results : dict
            A dictionary containing the JSON results from the APIs.
        format : str, optional
            The format of the documents to download.        

        Returns
        -------
        list
            A list of paths to the downloaded documents.
        """
        
        cellar_ids = self.get_cellar_ids_from_json_results(results, format=format)
        
        try:
            document_paths = []
            
            for id in cellar_ids:
                # Build the request URL
                url = self.build_request_url(params={'cellar': id})
                
                # Send the GET request
                response = self.fetch_content(url)
                # Handle the response
                file_path = self.handle_response(response=response, filename=id)
                # Append the file path to the list
                document_paths.append(file_path)
                
            return document_paths

        except Exception as e:
            logging.error(f"Error processing range: {e}")
        
        return document_paths

def main():
    parser = argparse.ArgumentParser(description='Download a Cellar document to a folder')
    parser.add_argument('--celex', type=str, default='32024R0903', help='CELEX identifier of the document')
    parser.add_argument('--format', type=str, default='fmx4', help='Format of the document, either fmx4 or xhtml')
    parser.add_argument('--dir', type=str, default='tests/data/formex', help='Path to the directory')
    
    args = parser.parse_args()
    
    client = CellarClient(download_dir=args.dir, log_dir='./tests/logs')
    
    if args.format == 'fmx4':
        sparql_query = './tests/metadata/queries/formex_query.rq'
    elif args.format == 'xhtml':
        sparql_query = './tests/metadata/queries/html_query.rq'
    else:
        print('No valid format')
        return None
        
    results = send_sparql_query(sparql_query_filepath=sparql_query, celex=args.celex)
        
    documents = client.download(results, format=args.format)
    
    print(documents)

    
# Example usage
if __name__ == "__main__":
    main()
    