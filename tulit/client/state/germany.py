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
    API Documentation: https://docs.rechtsinformationen.bund.de/
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
        
    # ===== CONVENIENCE METHODS =====
    
    def _download_from_eli(self, eli_url: str, fmt: str = 'html', filename: str = None) -> str:
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
    
    def download(self, document_type: str, format: str = 'html', **kwargs) -> str:
        """
        Unified download method for German legal documents.
        
        Parameters
        ----------
        document_type : str
            Type of document: 'legislation', 'case_law', 'literature', 'eli'
        format : str, optional
            Format: 'html', 'xml', 'zip' (default 'html')
        **kwargs
            Additional parameters depending on document_type:
            
            For 'legislation':
                jurisdiction, agent, year, natural_identifier, point_in_time, 
                version, language, point_in_time_manifestation, subtype, filename
                
            For 'case_law':
                document_number, filename
                
            For 'literature':
                document_number, filename
                
            For 'eli':
                eli_url, filename
                
        Returns
        -------
        str
            Path to the downloaded file.
        """
        if document_type == 'legislation':
            return self._download_legislation(
                jurisdiction=kwargs.get('jurisdiction'),
                agent=kwargs.get('agent'), 
                year=kwargs.get('year'),
                natural_identifier=kwargs.get('natural_identifier'),
                point_in_time=kwargs.get('point_in_time'),
                version=kwargs.get('version'),
                language=kwargs.get('language', 'deu'),
                point_in_time_manifestation=kwargs.get('point_in_time_manifestation'),
                subtype=kwargs.get('subtype'),
                format=format,
                filename=kwargs.get('filename')
            )
        elif document_type == 'case_law':
            return self._download_case_law(
                document_number=kwargs.get('document_number'),
                format=format,
                filename=kwargs.get('filename')
            )
        elif document_type == 'literature':
            return self._download_literature(
                document_number=kwargs.get('document_number'),
                format=format,
                filename=kwargs.get('filename')
            )
        elif document_type == 'eli':
            return self._download_from_eli(
                eli_url=kwargs.get('eli_url'),
                fmt=format,
                filename=kwargs.get('filename')
            )
        else:
            raise ValueError(f"Unknown document_type: {document_type}")
    
    def _download_legislation(self, jurisdiction, agent, year, natural_identifier, 
                             point_in_time, version, language, point_in_time_manifestation, 
                             subtype, format, filename):
        """Internal method for legislation downloads."""
        endpoint = f"legislation/eli/{jurisdiction}/{agent}/{year}/{natural_identifier}/{point_in_time}/{version}/{language}/{point_in_time_manifestation}/{subtype}.{format}"
        url = self._build_url(endpoint)
        
        headers = {
            'html': {'Accept': 'text/html'},
            'xml': {'Accept': 'application/xml'},
            'zip': {'Accept': 'application/zip'}
        }.get(format, {'Accept': 'text/html'})
        
        response = self._make_request(url, headers=headers)
        
        if not filename:
            filename = f"{jurisdiction}_{agent}_{year}_{natural_identifier}_{point_in_time}_{version}_{language}_{subtype}"
            
        return self.handle_response(response, filename)
    
    def _download_case_law(self, document_number, format, filename):
        """Internal method for case law downloads."""
        endpoint = f"case-law/{document_number}.{format}"
        url = self._build_url(endpoint)
        
        headers = {
            'html': {'Accept': 'text/html'},
            'xml': {'Accept': 'application/xml'},
            'zip': {'Accept': 'application/zip'}
        }.get(format, {'Accept': 'text/html'})
        
        response = self._make_request(url, headers=headers)
        
        if not filename:
            filename = f"case_law_{document_number}"
            
        return self.handle_response(response, filename)
    
    def _download_literature(self, document_number, format, filename):
        """Internal method for literature downloads."""
        if format == 'zip':
            raise ValueError("Literature does not support ZIP format")
            
        endpoint = f"literature/{document_number}.{format}"
        url = self._build_url(endpoint)
        
        headers = {
            'html': {'Accept': 'text/html'},
            'xml': {'Accept': 'application/xml'}
        }.get(format, {'Accept': 'text/html'})
        
        response = self._make_request(url, headers=headers)
        
        if not filename:
            filename = f"literature_{document_number}"
            
        return self.handle_response(response, filename)
