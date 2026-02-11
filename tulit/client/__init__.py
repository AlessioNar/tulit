"""
TULIT Client Module
===================

This module provides client implementations for downloading legal documents from various
jurisdictions and official sources. It includes specialized clients for EU databases,
member state legal portals, and regional legal information systems.

Main Components
---------------
- Client: Base class providing common functionality for document downloading
- EU Clients: Specialized clients for European Union legal databases (Cellar, etc.)
- Member State Clients: Clients for national legal databases (Legifrance, BOE, etc.)
- Regional Clients: Clients for regional/sub-national legal information systems

Available Clients
----------------
EU Clients:
    - CellarClient: For accessing EU Cellar documents via SPARQL and REST APIs

Member State Clients:
    - LegifranceClient: French legal database (codes, laws, case law)
    - BOEClient: Spanish Official State Gazette
    - FinlexClient: Finnish legal database
    - GermanyClient: German legal information system
    - LegiluxClient: Luxembourg legal database
    - MaltaClient: Maltese legal database
    - NormattivaClient: Italian legal database
    - PortugalClient: Portuguese legal database
    - IrishStatuteBookClient: Irish legal database

Regional Clients:
    - VenetoClient: Veneto regional legal documents (Italy)

Usage Example
-------------
>>> from tulit.client.eu.cellar import CellarClient
>>> from tulit.client.state.legifrance import LegifranceClient

# EU Cellar client
>>> cellar = CellarClient(download_dir='./downloads', log_dir='./logs')
>>> documents = cellar.download(celex='32018R0001', format='fmx4')

# Legifrance client
>>> legifrance = LegifranceClient(client_id='your_id', client_secret='your_secret')
>>> token = legifrance.get_token()
>>> legifrance.search_documents(query='code civil', document_type='CODE')

Key Features
------------
- Unified interface for diverse legal data sources
- SPARQL query support for semantic legal databases
- OAuth2 authentication for protected APIs
- Proxy support for enterprise environments
- Comprehensive logging and error handling
- Automatic directory management for downloads

Error Handling
--------------
All clients implement robust error handling with:
- Detailed logging at different levels (INFO, WARNING, ERROR)
- Graceful degradation on partial failures
- Comprehensive exception handling for network issues
- Validation of API responses

Notes
-----
- Some APIs require authentication (OAuth2, API keys)
- Rate limiting may apply to certain endpoints
- Check individual client documentation for specific requirements

Author
------
Alessio Nardin (maintainer)

Date
----
Last updated: 02-2026 (ongoing development)
"""