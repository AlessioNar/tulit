import json
import logging
import os
from tulit.download.client import download_documents
from sparql import send_sparql_query
from parsers.html import HTMLParser
from parsers.formex import Formex4Parser

def main():
    """
    Main function to execute SPARQL query and download documents
    """
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:

        # Send SPARQL query
        logger.info("Executing SPARQL query")
        results = send_sparql_query('./tests/metadata/queries/formex_query.rq', celex='32008R1137')
        

        # Save query results to JSON
        results_file = './tests/metadata/query_results/query_results.json'
        with open(results_file, "w") as f:
            json.dump(results, f, indent=4)
            logger.info(f"Results dumped in {results_file}")

        # Load query results
        with open('./tests/metadata/query_results/query_results.json', 'r') as f:
            results = json.loads(f.read())

        # Download documents
        logger.info("Downloading documents")
        downloaded_document_paths = download_documents(
            results, 
            './tests/data/formex', 
            log_dir='./tests/logs', 
            format='fmx4'
        )
        logger.info(f'{len(downloaded_document_paths)} documents downloaded in {downloaded_document_paths}')
                
        # Extract the directory path (removing what's after the last '/')

        # List the contents of the first directory
        first_path = downloaded_document_paths[0]
        first_item = os.listdir(first_path)[0]
        file_path = os.path.join(*first_path.split('/'), first_item)
    
        print(f'Parsing {file_path}')
        # Sort the contents alphabetically and get the first item
        
        parser = Formex4Parser()
        parser.parse(file_path)
        print(parser.articles)
        #print(document_tree)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise

if __name__ == "__main__":
    main()