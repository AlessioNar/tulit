import logging
import argparse
import requests
from tulit.client.client import Client
from SPARQLWrapper import SPARQLWrapper, JSON, POST

import logging

logger = logging.getLogger(__name__)

class CellarClient(Client):
    
    def __init__(self, download_dir, log_dir, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.endpoint = 'http://publications.europa.eu/resource/cellar/'
        self.sparql_endpoint = "http://publications.europa.eu/webapi/rdf/sparql"
    
    def send_sparql_query(self, sparql_query_filepath, celex=None):
        """
        Sends a SPARQL query to the EU SPARQL endpoint and stores the results in a JSON file.

        Parameters
        ----------
        sparql_query_filepath : str
            The path to the file containing the SPARQL query.
        response_file : str
            The path to the file where the results will be stored.

        Returns
        -------
        None

        Raises
        ------
        FileNotFoundError
            If the SPARQL query file is not found.
        Exception
            If there is an error sending the query or storing the results.

        Notes
        -----
        This function assumes that the SPARQL query file contains a valid SPARQL query.
        The results are stored in JSON format.

        """

        # Open SPARQL QUERY and print it to screen
        try:
            with open(sparql_query_filepath, 'r') as file:
                sparql_query = file.read()
            
            if celex is not None:
                # Option 1: If you want to use format()
                sparql_query = sparql_query.replace("{CELEX}", celex) 

                # send query to cellar endpoint and retrieve results
                results = self.get_results_table(sparql_query)

            return results
    
        except FileNotFoundError as e:
            print(f"Error: The file {sparql_query_filepath} was not found.")
            raise e
        except Exception as e:
            print(f"An error occurred: {e}")
            raise e

    def get_results_table(self, sparql_query):
        """
        Sends a SPARQL query to the EU SPARQL endpoint and returns the results as a JSON object.

        Parameters
        ----------
        sparql_query : str
            The SPARQL query as a string.

        Returns
        -------
        dict
            The results of the SPARQL query in JSON format.

        Raises
        ------
        Exception
            If there is an error sending the query or retrieving the results.

        Notes
        -----
        This function uses the SPARQLWrapper library to send the query and retrieve the results.
        The results are returned in JSON format.

        """        

        try:
            # Create a SPARQLWrapper object with the endpoint URL
            sparql = SPARQLWrapper(self.sparql_endpoint)

            # Set the SPARQL query
            sparql.setQuery(sparql_query)

            # Set the query method to POST
            sparql.setMethod(POST)

            # Set the return format to JSON
            sparql.setReturnFormat(JSON)

            # Send the query and retrieve the results
            results = sparql.query().convert()

            return results
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            raise e
    
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
            if self.proxies is not None:
                response = requests.request("GET", url, headers=headers, proxies=self.proxies)
            else:
                response = requests.request("GET", url, headers=headers)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"Error sending GET request: {e}")
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

    def download(self, celex, format=None):
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
        if format == 'fmx4':
            sparql_query = './tests/metadata/queries/formex_query.rq'
        elif format == 'xhtml':
            sparql_query = './tests/metadata/queries/html_query.rq'
        else:
            logger.error('No valid format provided. Please choose one between fmx4 or xhtml')
            return None
            
        results = self.send_sparql_query(sparql_query, celex)                
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
    
    documents = client.download(celex=args.celex, format=args.format)
    
    print(documents)

if __name__ == "__main__":
    main()
    