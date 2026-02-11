import logging
import argparse
import requests
from tulit.client.client import Client
from SPARQLWrapper import SPARQLWrapper, JSON, POST
import sys

from importlib.resources import files



logger = logging.getLogger(__name__)

class CellarClient(Client):
    
    def __init__(self, download_dir, log_dir, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.endpoint = 'http://publications.europa.eu/resource/cellar/'
        self.sparql_endpoint = "http://publications.europa.eu/webapi/rdf/sparql"
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def send_sparql_query(self, sparql_query, celex=None):
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
            
            if celex is not None:
                # URL encode parentheses in CELEX number for SPARQL query
                # This is needed for documents with suffixes like (01), (02), etc.
                import urllib.parse
                celex_encoded = celex.replace("(", "%28").replace(")", "%29")
                
                sparql_query = sparql_query.replace("{CELEX}", celex_encoded) 

                # send query to cellar endpoint and retrieve results
                results = self.get_results_table(sparql_query)

            return results
    
        except FileNotFoundError as e:
            self.logger.error(f"SPARQL query file not found: {e}")
            from tulit.parser.exceptions import FileLoadError
            raise FileLoadError(f"SPARQL query file not found: {e}") from e
        except Exception as e:
            self.logger.error(f"Error sending SPARQL query: {e}")
            from tulit.parser.exceptions import SPARQLError
            raise SPARQLError(f"SPARQL query execution failed: {e}") from e

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
            self.logger.info("Getting results table from SPARQL query")
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
            self.logger.error(f"Error retrieving SPARQL results: {e}")
            from tulit.parser.exceptions import SPARQLError
            raise SPARQLError(f"Failed to retrieve SPARQL results: {e}") from e
    
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
        - User-Agent: Browser user agent (required by EU server to bypass bot protection)

        Raises
        ------
        requests.RequestException
            If there is an error sending the request.

        See Also
        --------
        requests : The underlying library used for making HTTP requests.

        """
        try:
            self.logger.info(f"Fetching content from URL: {url}")
            headers = {
                'Accept': "*, application/zip, application/zip;mtype=fmx4, application/xml;mtype=fmx4, application/xhtml+xml, text/html, text/html;type=simplified, application/msword, text/plain, application/xml, application/xml;notice=object",
                'Accept-Language': "eng",
                'Content-Type': "application/x-www-form-urlencoded",
                'Host': "publications.europa.eu",
                # EU server blocks bot traffic - use browser User-Agent
                'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            if self.proxies is not None:
                response = requests.request("GET", url, headers=headers, proxies=self.proxies)
            else:
                response = requests.request("GET", url, headers=headers)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            self.logger.error(f"Error sending GET request: {e}")
            from tulit.parser.exceptions import NetworkError
            raise NetworkError(f"Network request failed: {e}") from e
             
    def build_request_url(self, params):
        """
        Build the request URL based on the source and parameters.
        """
        self.logger.info(f"Building request URL with params: {params}")
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
        self.logger.info(f"Extracting cellar IDs from results for format: {format}")
        cellar_ids = []
        results_list = results["results"]["bindings"]
        for i, file in enumerate(results_list):
            if file['format']['value'] == format:
                cellar_ids.append(file['cellarURIs']["value"].split("cellar/")[1])

        return cellar_ids

    def download(self, celex, format=None, type_id='celex'):
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
        self.logger.info(f"Downloading document for celex: {celex}, format: {format}")
        if format == 'fmx4':
            if type_id == 'eli':
                sparql_query = files("tulit.client.eu.queries").joinpath("formex_eli_query.rq").read_text()
                sparql_query = sparql_query.replace("{ELI}", celex)            
            elif type_id == 'celex':
                sparql_query = files("tulit.client.eu.queries").joinpath("formex_query.rq").read_text()
                sparql_query = sparql_query.replace("{CELEX}", celex)                
        elif format == 'xhtml':
            sparql_query = files("tulit.client.eu.queries").joinpath("html_query.rq").read_text()
        elif format == 'html':
            sparql_query = files("tulit.client.eu.queries").joinpath("html_standard_query.rq").read_text()
        else:
            self.logger.error('No valid format provided. Please choose one between fmx4, xhtml, or html')
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
            self.logger.error(f"Error processing range: {e}")
        
        return document_paths
