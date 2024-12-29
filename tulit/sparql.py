#!/usr/bin/python
# coding=<utf-8>

"""
It also includes functions to create a list of CELLAR IDs from the query results and to read a list of
CELLAR IDs from a CSV file.

"""

from SPARQLWrapper import SPARQLWrapper, JSON, POST
import json

def send_sparql_query(sparql_query_filepath, celex=None):
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
            results = get_results_table(sparql_query)

        return results
    
    except FileNotFoundError as e:
        print(f"Error: The file {sparql_query_filepath} was not found.")
        raise e
    except Exception as e:
        print(f"An error occurred: {e}")
        raise e

def get_results_table(sparql_query):
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

    # Define the EU SPARQL endpoint URL
    endpoint = "http://publications.europa.eu/webapi/rdf/sparql"

    try:
        # Create a SPARQLWrapper object with the endpoint URL
        sparql = SPARQLWrapper(endpoint)

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
        print(f"An error occurred: {e}")
        raise e

# Main function
if __name__ == "__main__":

    document_paths = send_sparql_query('./tests/metadata/queries/formex_query.rq', celex='32024R1689')# 32024R0903')
    with open('./tests/metadata/ai_act.json', "w") as f:
        json.dump(document_paths, f, indent=4) 