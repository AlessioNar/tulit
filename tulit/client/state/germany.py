import logging
import requests
import argparse
import os
import sys
from tulit.client.client import Client
from datetime import datetime
from typing import Optional, List, Dict


class GermanyClient(Client):
    """
    Client for retrieving legal documents from the German RIS (Rechtsinformationssystem) API.
    
    This client supports:
    - Legislation (laws and decrees)
    - Case Law (court decisions)
    - Literature (legal literature)
    
    Base API: https://testphase.rechtsinformationen.bund.de
    API Documentation: https://testphase.rechtsinformationen.bund.de/swagger-ui/index.html
    """
    
    def __init__(self, download_dir, log_dir, proxies=None):
        """
        Initialize the Germany RIS client.
        
        Parameters
        ----------
        download_dir : str
            Directory where downloaded files will be saved.
        log_dir : str
            Directory where log files will be saved.
        proxies : dict, optional
            Proxy configuration for requests.
        """
        super().__init__(download_dir, log_dir, proxies)
        self.base_url = "https://testphase.rechtsinformationen.bund.de"
        self.api_version = "v1"
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def _build_url(self, endpoint: str) -> str:
        """Build a complete API URL from an endpoint path."""
        if endpoint.startswith('http'):
            return endpoint
        # Remove leading slash from endpoint to avoid double slashes
        endpoint = endpoint.lstrip('/')
        return f"{self.base_url}/{self.api_version}/{endpoint}"
    
    def _make_request(self, url: str, params: dict = None, headers: dict = None) -> requests.Response:
        """
        Make an HTTP GET request with error handling.
        
        Parameters
        ----------
        url : str
            The URL to request.
        params : dict, optional
            Query parameters.
        headers : dict, optional
            HTTP headers.
            
        Returns
        -------
        requests.Response
            The response object.
        """
        try:
            self.logger.info(f"Requesting URL: {url}")
            if params:
                self.logger.debug(f"Parameters: {params}")
                
            default_headers = {
                'Accept': 'application/json',
                'User-Agent': 'TuLit-Germany-Client/1.0'
            }
            if headers:
                default_headers.update(headers)
                
            if self.proxies:
                response = requests.get(url, params=params, headers=default_headers, proxies=self.proxies)
            else:
                response = requests.get(url, params=params, headers=default_headers)
                
            response.raise_for_status()
            self.logger.info(f"Successfully retrieved content from {url}")
            return response
            
        except requests.RequestException as e:
            self.logger.error(f"Request failed for {url}: {e}")
            raise
    
    # ===== LEGISLATION ENDPOINTS =====
    
    def search_legislation(self, search_term: str = None, eli: str = None, 
                          temporal_coverage_from: str = None, temporal_coverage_to: str = None,
                          date_from: str = None, date_to: str = None,
                          size: int = 100, page_index: int = 0, sort: str = None) -> dict:
        """
        Search for legislation documents.
        
        Parameters
        ----------
        search_term : str, optional
            Search term (all tokens must match).
        eli : str, optional
            European Legislation Identifier (work ELI).
        temporal_coverage_from : str, optional
            Filter expressions in force on/after this date (YYYY-MM-DD).
        temporal_coverage_to : str, optional
            Filter expressions in force on/before this date (YYYY-MM-DD).
        date_from : str, optional
            Filter by adoption/signature date from (YYYY-MM-DD).
        date_to : str, optional
            Filter by adoption/signature date to (YYYY-MM-DD).
        size : int, optional
            Number of results per page (max 100).
        page_index : int, optional
            Page number (starts at 0).
        sort : str, optional
            Sort field (date, temporalCoverageFrom, legislationIdentifier).
            
        Returns
        -------
        dict
            JSON response with search results.
        """
        params = {
            'size': size,
            'pageIndex': page_index
        }
        if search_term:
            params['searchTerm'] = search_term
        if eli:
            params['eli'] = eli
        if temporal_coverage_from:
            params['temporalCoverageFrom'] = temporal_coverage_from
        if temporal_coverage_to:
            params['temporalCoverageTo'] = temporal_coverage_to
        if date_from:
            params['dateFrom'] = date_from
        if date_to:
            params['dateTo'] = date_to
        if sort:
            params['sort'] = sort
            
        url = self._build_url('legislation')
        response = self._make_request(url, params=params)
        return response.json()
    
    def get_legislation_metadata(self, jurisdiction: str, agent: str, year: str, 
                                 natural_identifier: str, point_in_time: str, 
                                 version: int, language: str = 'deu') -> dict:
        """
        Get metadata for a specific legislation expression.
        
        Parameters
        ----------
        jurisdiction : str
            Jurisdiction (e.g., 'bund').
        agent : str
            Issuing agent (e.g., 'bgbl-1' for Federal Law Gazette Part I).
        year : str
            Year of enactment.
        natural_identifier : str
            Natural identifier (e.g., 's1325').
        point_in_time : str
            Point in time date (YYYY-MM-DD).
        version : int
            Version number.
        language : str, optional
            Language code (default 'deu').
            
        Returns
        -------
        dict
            JSON metadata for the legislation.
        """
        endpoint = f"legislation/eli/{jurisdiction}/{agent}/{year}/{natural_identifier}/{point_in_time}/{version}/{language}"
        url = self._build_url(endpoint)
        response = self._make_request(url)
        return response.json()
    
    def download_legislation_html(self, jurisdiction: str, agent: str, year: str,
                                  natural_identifier: str, point_in_time: str,
                                  version: int, language: str, point_in_time_manifestation: str,
                                  subtype: str, filename: str = None) -> str:
        """
        Download legislation as HTML.
        
        Parameters
        ----------
        jurisdiction : str
            Jurisdiction (e.g., 'bund').
        agent : str
            Issuing agent (e.g., 'bgbl-1').
        year : str
            Year of enactment.
        natural_identifier : str
            Natural identifier (e.g., 's1325').
        point_in_time : str
            Point in time date (YYYY-MM-DD).
        version : int
            Version number.
        language : str
            Language code (e.g., 'deu').
        point_in_time_manifestation : str
            Manifestation date (YYYY-MM-DD).
        subtype : str
            Subtype (e.g., 'regelungstext-1').
        filename : str, optional
            Custom filename for saving.
            
        Returns
        -------
        str
            Path to the downloaded file.
        """
        endpoint = f"legislation/eli/{jurisdiction}/{agent}/{year}/{natural_identifier}/{point_in_time}/{version}/{language}/{point_in_time_manifestation}/{subtype}.html"
        url = self._build_url(endpoint)
        
        headers = {'Accept': 'text/html'}
        response = self._make_request(url, headers=headers)
        
        if not filename:
            filename = f"{jurisdiction}_{agent}_{year}_{natural_identifier}_{point_in_time}_{version}_{language}_{subtype}"
            
        return self.handle_response(response, filename)
    
    def download_legislation_xml(self, jurisdiction: str, agent: str, year: str,
                                natural_identifier: str, point_in_time: str,
                                version: int, language: str, point_in_time_manifestation: str,
                                subtype: str, filename: str = None) -> str:
        """
        Download legislation as XML (LegalDocML format).
        
        Parameters
        ----------
        jurisdiction : str
            Jurisdiction (e.g., 'bund').
        agent : str
            Issuing agent (e.g., 'bgbl-1').
        year : str
            Year of enactment.
        natural_identifier : str
            Natural identifier (e.g., 's1325').
        point_in_time : str
            Point in time date (YYYY-MM-DD).
        version : int
            Version number.
        language : str
            Language code (e.g., 'deu').
        point_in_time_manifestation : str
            Manifestation date (YYYY-MM-DD).
        subtype : str
            Subtype (e.g., 'regelungstext-1').
        filename : str, optional
            Custom filename for saving.
            
        Returns
        -------
        str
            Path to the downloaded file.
        """
        endpoint = f"legislation/eli/{jurisdiction}/{agent}/{year}/{natural_identifier}/{point_in_time}/{version}/{language}/{point_in_time_manifestation}/{subtype}.xml"
        url = self._build_url(endpoint)
        
        headers = {'Accept': 'application/xml'}
        response = self._make_request(url, headers=headers)
        
        if not filename:
            filename = f"{jurisdiction}_{agent}_{year}_{natural_identifier}_{point_in_time}_{version}_{language}_{subtype}"
            
        return self.handle_response(response, filename)
    
    def download_legislation_zip(self, jurisdiction: str, agent: str, year: str,
                                natural_identifier: str, point_in_time: str,
                                version: int, language: str, point_in_time_manifestation: str,
                                filename: str = None) -> str:
        """
        Download legislation as ZIP (including XML and attachments).
        
        Parameters
        ----------
        jurisdiction : str
            Jurisdiction (e.g., 'bund').
        agent : str
            Issuing agent (e.g., 'bgbl-1').
        year : str
            Year of enactment.
        natural_identifier : str
            Natural identifier (e.g., 's1325').
        point_in_time : str
            Point in time date (YYYY-MM-DD).
        version : int
            Version number.
        language : str
            Language code (e.g., 'deu').
        point_in_time_manifestation : str
            Manifestation date (YYYY-MM-DD).
        filename : str, optional
            Custom filename for saving.
            
        Returns
        -------
        str
            Path to the downloaded/extracted file.
        """
        endpoint = f"legislation/eli/{jurisdiction}/{agent}/{year}/{natural_identifier}/{point_in_time}/{version}/{language}/{point_in_time_manifestation}.zip"
        url = self._build_url(endpoint)
        
        headers = {'Accept': 'application/zip'}
        response = self._make_request(url, headers=headers)
        
        if not filename:
            filename = f"{jurisdiction}_{agent}_{year}_{natural_identifier}_{point_in_time}_{version}_{language}"
            
        return self.handle_response(response, filename)
    
    # ===== CASE LAW ENDPOINTS =====
    
    def search_case_law(self, search_term: str = None, file_number: str = None,
                       ecli: str = None, court: str = None, document_type: str = None,
                       date_from: str = None, date_to: str = None,
                       size: int = 100, page_index: int = 0, sort: str = None) -> dict:
        """
        Search for case law decisions.
        
        Parameters
        ----------
        search_term : str, optional
            Search term (all tokens must match).
        file_number : str, optional
            File number (Aktenzeichen).
        ecli : str, optional
            European Case Law Identifier.
        court : str, optional
            Court name or type.
        document_type : str, optional
            Document type (e.g., 'Urteil', 'Beschluss').
        date_from : str, optional
            Decision date from (YYYY-MM-DD).
        date_to : str, optional
            Decision date to (YYYY-MM-DD).
        size : int, optional
            Number of results per page (max 100).
        page_index : int, optional
            Page number (starts at 0).
        sort : str, optional
            Sort field (date, courtName, documentNumber).
            
        Returns
        -------
        dict
            JSON response with search results.
        """
        params = {
            'size': size,
            'pageIndex': page_index
        }
        if search_term:
            params['searchTerm'] = search_term
        if file_number:
            params['fileNumber'] = file_number
        if ecli:
            params['ecli'] = ecli
        if court:
            params['court'] = court
        if document_type:
            params['type'] = document_type
        if date_from:
            params['dateFrom'] = date_from
        if date_to:
            params['dateTo'] = date_to
        if sort:
            params['sort'] = sort
            
        url = self._build_url('case-law')
        response = self._make_request(url, params=params)
        return response.json()
    
    def get_case_law_metadata(self, document_number: str) -> dict:
        """
        Get metadata for a specific case law decision.
        
        Parameters
        ----------
        document_number : str
            Document number.
            
        Returns
        -------
        dict
            JSON metadata for the case law.
        """
        endpoint = f"case-law/{document_number}"
        url = self._build_url(endpoint)
        response = self._make_request(url)
        return response.json()
    
    def download_case_law_html(self, document_number: str, filename: str = None) -> str:
        """
        Download case law decision as HTML.
        
        Parameters
        ----------
        document_number : str
            Document number.
        filename : str, optional
            Custom filename for saving.
            
        Returns
        -------
        str
            Path to the downloaded file.
        """
        endpoint = f"case-law/{document_number}.html"
        url = self._build_url(endpoint)
        
        headers = {'Accept': 'text/html'}
        response = self._make_request(url, headers=headers)
        
        if not filename:
            filename = f"case_law_{document_number}"
            
        return self.handle_response(response, filename)
    
    def download_case_law_xml(self, document_number: str, filename: str = None) -> str:
        """
        Download case law decision as XML.
        
        Parameters
        ----------
        document_number : str
            Document number.
        filename : str, optional
            Custom filename for saving.
            
        Returns
        -------
        str
            Path to the downloaded file.
        """
        endpoint = f"case-law/{document_number}.xml"
        url = self._build_url(endpoint)
        
        headers = {'Accept': 'application/xml'}
        response = self._make_request(url, headers=headers)
        
        if not filename:
            filename = f"case_law_{document_number}"
            
        return self.handle_response(response, filename)
    
    def download_case_law_zip(self, document_number: str, filename: str = None) -> str:
        """
        Download case law decision as ZIP (including XML and attachments).
        
        Parameters
        ----------
        document_number : str
            Document number.
        filename : str, optional
            Custom filename for saving.
            
        Returns
        -------
        str
            Path to the downloaded/extracted file.
        """
        endpoint = f"case-law/{document_number}.zip"
        url = self._build_url(endpoint)
        
        headers = {'Accept': 'application/zip'}
        response = self._make_request(url, headers=headers)
        
        if not filename:
            filename = f"case_law_{document_number}"
            
        return self.handle_response(response, filename)
    
    # ===== LITERATURE ENDPOINTS =====
    
    def search_literature(self, search_term: str = None, document_number: str = None,
                         year_of_publication: str = None, author: str = None,
                         date_from: str = None, date_to: str = None,
                         size: int = 100, page_index: int = 0, sort: str = None) -> dict:
        """
        Search for literature documents.
        
        Parameters
        ----------
        search_term : str, optional
            Search term (all tokens must match).
        document_number : str, optional
            Document number.
        year_of_publication : str, optional
            Year of publication.
        author : str, optional
            Author name.
        date_from : str, optional
            Date from (YYYY-MM-DD).
        date_to : str, optional
            Date to (YYYY-MM-DD).
        size : int, optional
            Number of results per page (max 100).
        page_index : int, optional
            Page number (starts at 0).
        sort : str, optional
            Sort field (date, documentNumber).
            
        Returns
        -------
        dict
            JSON response with search results.
        """
        params = {
            'size': size,
            'pageIndex': page_index
        }
        if search_term:
            params['searchTerm'] = search_term
        if document_number:
            params['documentNumber'] = document_number
        if year_of_publication:
            params['yearOfPublication'] = year_of_publication
        if author:
            params['author'] = author
        if date_from:
            params['dateFrom'] = date_from
        if date_to:
            params['dateTo'] = date_to
        if sort:
            params['sort'] = sort
            
        url = self._build_url('literature')
        response = self._make_request(url, params=params)
        return response.json()
    
    def get_literature_metadata(self, document_number: str) -> dict:
        """
        Get metadata for a specific literature document.
        
        Parameters
        ----------
        document_number : str
            Document number.
            
        Returns
        -------
        dict
            JSON metadata for the literature.
        """
        endpoint = f"literature/{document_number}"
        url = self._build_url(endpoint)
        response = self._make_request(url)
        return response.json()
    
    def download_literature_html(self, document_number: str, filename: str = None) -> str:
        """
        Download literature document as HTML.
        
        Parameters
        ----------
        document_number : str
            Document number.
        filename : str, optional
            Custom filename for saving.
            
        Returns
        -------
        str
            Path to the downloaded file.
        """
        endpoint = f"literature/{document_number}.html"
        url = self._build_url(endpoint)
        
        headers = {'Accept': 'text/html'}
        response = self._make_request(url, headers=headers)
        
        if not filename:
            filename = f"literature_{document_number}"
            
        return self.handle_response(response, filename)
    
    def download_literature_xml(self, document_number: str, filename: str = None) -> str:
        """
        Download literature document as XML.
        
        Parameters
        ----------
        document_number : str
            Document number.
        filename : str, optional
            Custom filename for saving.
            
        Returns
        -------
        str
            Path to the downloaded file.
        """
        endpoint = f"literature/{document_number}.xml"
        url = self._build_url(endpoint)
        
        headers = {'Accept': 'application/xml'}
        response = self._make_request(url, headers=headers)
        
        if not filename:
            filename = f"literature_{document_number}"
            
        return self.handle_response(response, filename)
    
    # ===== GLOBAL SEARCH =====
    
    def search_all_documents(self, search_term: str = None, document_kind: str = None,
                            date_from: str = None, date_to: str = None,
                            size: int = 100, page_index: int = 0, sort: str = None) -> dict:
        """
        Search across all document types (legislation, case law, literature).
        
        Parameters
        ----------
        search_term : str, optional
            Search term (all tokens must match).
        document_kind : str, optional
            Document kind: 'R' for case law (Rechtsprechung) or 'N' for legislation (Normen).
        date_from : str, optional
            Date from (YYYY-MM-DD).
        date_to : str, optional
            Date to (YYYY-MM-DD).
        size : int, optional
            Number of results per page (max 100).
        page_index : int, optional
            Page number (starts at 0).
        sort : str, optional
            Sort field (date, courtName, documentNumber, temporalCoverageFrom, legislationIdentifier).
            
        Returns
        -------
        dict
            JSON response with search results.
        """
        params = {
            'size': size,
            'pageIndex': page_index
        }
        if search_term:
            params['searchTerm'] = search_term
        if document_kind:
            params['documentKind'] = document_kind
        if date_from:
            params['dateFrom'] = date_from
        if date_to:
            params['dateTo'] = date_to
        if sort:
            params['sort'] = sort
            
        url = self._build_url('document')
        response = self._make_request(url, params=params)
        return response.json()
    
    # ===== CONVENIENCE METHODS =====
    
    def download_from_eli(self, eli_url: str, fmt: str = 'html', filename: str = None) -> str:
        """
        Download a document from a full ELI URL.
        
        Parameters
        ----------
        eli_url : str
            Full ELI URL or path.
        fmt : str, optional
            Format: 'html', 'xml', or 'zip' (default 'html').
        filename : str, optional
            Custom filename for saving.
            
        Returns
        -------
        str
            Path to the downloaded file.
        """
        # Parse ELI URL
        if not eli_url.startswith('http'):
            # Remove leading slash and version if present to avoid duplication
            eli_url = eli_url.lstrip('/')
            if eli_url.startswith('v1/'):
                eli_url = eli_url[3:]  # Remove 'v1/' prefix
            eli_url = f"{self.base_url}/{self.api_version}/{eli_url}"
            
        # Ensure correct format extension
        if not eli_url.endswith(f'.{fmt}'):
            if eli_url.endswith('.html') or eli_url.endswith('.xml') or eli_url.endswith('.zip'):
                eli_url = eli_url.rsplit('.', 1)[0]
            eli_url = f"{eli_url}.{fmt}"
        
        headers = {
            'html': {'Accept': 'text/html'},
            'xml': {'Accept': 'application/xml'},
            'zip': {'Accept': 'application/zip'}
        }.get(fmt, {'Accept': 'text/html'})
        
        response = self._make_request(eli_url, headers=headers)
        
        if not filename:
            # Extract filename from URL
            parts = eli_url.split('/')
            filename = '_'.join(parts[-8:]) if len(parts) >= 8 else parts[-1]
            filename = filename.replace('.html', '').replace('.xml', '').replace('.zip', '')
            
        return self.handle_response(response, filename)


def main():
    """Command-line interface for the Germany client."""
    parser = argparse.ArgumentParser(
        description='Download documents from the German RIS API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download legislation by ELI URL
  python -m tulit.client.germany --type legislation --eli-url "https://testphase.rechtsinformationen.bund.de/v1/legislation/eli/bund/bgbl-1/1979/s1325/2020-06-19/2/deu/2020-06-19/regelungstext-1.html"
  
  # Download case law by document number
  python -m tulit.client.germany --type case-law --document-number STRE201770751 --format html
  
  # Search and download legislation
  python -m tulit.client.germany --type legislation --search "Kakaoverordnung" --format xml
  
  # Download literature
  python -m tulit.client.germany --type literature --document-number BJLU075748788 --format html
        """
    )
    
    parser.add_argument('--type', type=str, required=True, 
                       choices=['legislation', 'case-law', 'literature', 'search'],
                       help='Type of document to download')
    parser.add_argument('--eli-url', type=str, help='Full ELI URL for legislation')
    parser.add_argument('--document-number', type=str, help='Document number for case-law or literature')
    parser.add_argument('--search', type=str, help='Search term')
    parser.add_argument('--format', type=str, default='xml', choices=['html', 'xml', 'zip'],
                       help='Output format (default: xml - LegalDocML format)')
    parser.add_argument('--dir', type=str, default='./tests/data/html/germany',
                       help='Directory to save files')
    parser.add_argument('--logdir', type=str, default='./tests/logs',
                       help='Directory for logs')
    
    args = parser.parse_args()
    
    # Initialize client
    client = GermanyClient(download_dir=args.dir, log_dir=args.logdir)
    
    try:
        if args.type == 'legislation':
            if args.eli_url:
                # Download from ELI URL
                file_path = client.download_from_eli(args.eli_url, fmt=args.format)
                logging.info(f"Downloaded legislation to: {file_path}")
            elif args.search:
                # Search and download first result
                results = client.search_legislation(search_term=args.search, size=1)
                if results.get('totalItems', 0) > 0:
                    item = results['member'][0]['item']
                    if 'workExample' in item:
                        work_example_id = item['workExample']['@id']
                        # Fetch the expression metadata to get encoding URLs
                        # Remove leading /v1/ if present since _build_url will add it
                        path = work_example_id.lstrip('/')
                        if path.startswith('v1/'):
                            path = path[3:]  # Remove 'v1/' prefix
                        
                        url = client._build_url(path)
                        response = client._make_request(url)
                        expression_data = response.json()
                        
                        # The encoding is in the workExample field of the expression metadata
                        if 'workExample' in expression_data and 'encoding' in expression_data['workExample']:
                            format_map = {
                                'html': 'text/html',
                                'xml': 'application/xml',
                                'zip': 'application/zip'
                            }
                            encoding_url = None
                            for encoding in expression_data['workExample']['encoding']:
                                if encoding.get('encodingFormat') == format_map.get(args.format):
                                    encoding_url = encoding.get('contentUrl')
                                    break
                            
                            if encoding_url:
                                file_path = client.download_from_eli(encoding_url, fmt=args.format)
                                logging.info(f"Downloaded legislation to: {file_path}")
                            else:
                                logging.error(f"No {args.format} encoding found")
                                sys.exit(1)
                        else:
                            logging.error("No encoding information in expression data")
                            sys.exit(1)
                    else:
                        logging.error("No workExample in search results")
                        sys.exit(1)
                else:
                    logging.error("No results found for search term")
                    sys.exit(1)
            else:
                logging.error("For legislation, provide --eli-url or --search")
                sys.exit(1)
                
        elif args.type == 'case-law':
            if not args.document_number:
                logging.error("For case-law, provide --document-number")
                sys.exit(1)
            
            if args.format == 'html':
                file_path = client.download_case_law_html(args.document_number)
            elif args.format == 'xml':
                file_path = client.download_case_law_xml(args.document_number)
            elif args.format == 'zip':
                file_path = client.download_case_law_zip(args.document_number)
            logging.info(f"Downloaded case law to: {file_path}")
            
        elif args.type == 'literature':
            if not args.document_number:
                logging.error("For literature, provide --document-number")
                sys.exit(1)
            
            if args.format == 'html':
                file_path = client.download_literature_html(args.document_number)
            elif args.format == 'xml':
                file_path = client.download_literature_xml(args.document_number)
            else:
                logging.error("Literature only supports html and xml formats")
                sys.exit(1)
            logging.info(f"Downloaded literature to: {file_path}")
            
        elif args.type == 'search':
            if not args.search:
                logging.error("For search, provide --search term")
                sys.exit(1)
            
            results = client.search_all_documents(search_term=args.search)
            print(f"Found {results.get('totalItems', 0)} results:")
            for member in results.get('member', [])[:10]:
                item = member.get('item', {})
                print(f"  - {item.get('@type', 'Unknown')}: {item.get('name', item.get('headline', 'N/A'))}")
                
    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
