Getting Started
===============

Installation
------------

To use tulit, first install it using poetry:

.. code-block:: console

    $ poetry shell
    $ poetry install

This will install the package and its dependencies.

Alternatively, you can install the package using pip:

.. code-block:: console

    $ pip install tulit


Basic usage
-----------

The `tulit` package has two main components:

* **Client**: Query and retrieve data from legal sources across Europe:
  
  * EU: Cellar (EU Publications Office)
  * Member States: Finland, France, Germany, Ireland, Italy, Luxembourg, Malta, Portugal, Spain
  * Regional: Italian regions (Veneto)

* **Parser**: Convert legal documents from various formats to JSON:
  
  * XML: Akoma Ntoso, FORMEX 4, BOE XML
  * HTML: Cellar variants, Regional parsers
  * JSON: Legifrance

Retrieving legal documents
---------------------------

EU Cellar Client
~~~~~~~~~~~~~~~~

Retrieve documents from the EU Publications Office:

.. code-block:: python

    from tulit.client.eu.cellar import CellarClient
    
    client = CellarClient(download_dir='./database', log_dir='./logs')

    file_format = 'fmx4'  # Or 'xhtml', 'pdfa', etc.
    celex = "32024R0903"

    documents = client.download(celex=celex, format=file_format)
    print(f"Downloaded: {documents}")

Member State Clients
~~~~~~~~~~~~~~~~~~~~

**Italy (Normattiva):**

.. code-block:: python

    from tulit.client.state.normattiva import NormativaClient
    
    client = NormativaClient(download_dir='./database')
    # Download by URN
    client.download(urn='urn:nir:stato:decreto.legge:2024-01-01;1')

**Luxembourg (Legilux):**

.. code-block:: python

    from tulit.client.state.legilux import LegiluxClient
    
    client = LegiluxClient(download_dir='./database')
    client.download(eli='eli/etat/leg/code/travail')

**Germany (RIS):**

.. code-block:: python

    from tulit.client.state.germany import GermanyClient
    
    client = GermanyClient(download_dir='./database')
    client.download(doc_type='bgbl', year='2024', number='145')

Regional Clients
~~~~~~~~~~~~~~~~

**Veneto (Italy):**

.. code-block:: python

    from tulit.client.regional.veneto import VenetoClient
    
    client = VenetoClient(download_dir='./database')
    client.download(bur_number='1', year='2024')

Parsing legal documents
-----------------------

The `tulit` parsers support legislative documents in the following formats:

**XML Formats:**

  * Akoma Ntoso 3.0 (EU, German LegalDocML, Luxembourg variants)
  * FORMEX 4 (EU legislative documents)
  * BOE XML (Spanish Official Gazette)

**HTML Formats:**

  * Cellar XHTML (semantic structure)
  * Cellar Standard HTML (simple structure)
  * EU Legislative Proposals
  * Veneto Regional HTML

**JSON Formats:**

  * Legifrance JSON

Parsing XML Documents
~~~~~~~~~~~~~~~~~~~~~

**Akoma Ntoso:** The package automatically detects variants (EU, German, Luxembourg):

.. code-block:: python
    
    from tulit.parser.xml.akomantoso import AKN4EUParser, GermanLegalDocMLParser
    
    eu_parser = AKN4EUParser()
    eu_parser.parse('tests/data/akn/eu/32014L0092.akn')
    
    german_parser = GermanLegalDocMLParser()
    german_parser.parse('tests/data/akn/germany/document.akn')

**FORMEX 4:** Parse EU legislative documents in FORMEX format:

.. code-block:: python

    from tulit.parser.xml.formex import Formex4Parser

    parser = Formex4Parser()
    formex_file = 'tests/data/formex/c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.02/DOC_1/L_202400903EN.000101.fmx.xml'
    result = parser.parse(formex_file)
    
    # Access parsed content
    print(f"Found {len(parser.articles)} articles")
    for article in parser.articles:
        print(f"Article {article.number}: {article.title}")

Parsing HTML Documents
~~~~~~~~~~~~~~~~~~~~~~

**Cellar HTML:** Parse documents from EU Cellar in semantic XHTML format:

.. code-block:: python

    from tulit.parser.html.cellar import CellarHTMLParser
    
    parser = CellarHTMLParser()
    html_file = 'tests/data/html/c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.03/DOC_1.html'
    parser.parse(html_file)

**Cellar Standard HTML:** Parse documents with simple <TXT_TE> structure:

.. code-block:: python

    from tulit.parser.html.cellar import CellarStandardHTMLParser
    
    parser = CellarStandardHTMLParser()
    parser.parse('document.html')

**EU Proposals:** Parse legislative proposals with special structure:

.. code-block:: python

    from tulit.parser.html.cellar import ProposalHTMLParser
    
    parser = ProposalHTMLParser()
    parser.parse('proposal.html')

**Veneto Regional:** Parse Italian regional legislation:

.. code-block:: python

    from tulit.parser.html.veneto import VenetoHTMLParser
    
    parser = VenetoHTMLParser()
    parser.parse('tests/data/html/veneto/esg.html')


Accessing Parsed Content
~~~~~~~~~~~~~~~~~~~~~~~~

After parsing, the document structure is available through parser attributes:

.. code-block:: python
    
    # Parse a document
    from tulit.parser.xml.formex import Formex4Parser
    parser = Formex4Parser()
    parser.parse('document.fmx.xml')
    
    # Metadata and preface
    print(f"Title: {parser.preface}")
    
    # Preamble components
    for citation in parser.citations:
        print(f"Citation: {citation.content}")
    
    for recital in parser.recitals:
        print(f"Recital {recital.number}: {recital.content}")
    
    print(f"Formula: {parser.formula}")
    print(f"Preamble final: {parser.preamble_final}")
    
    # Body structure
    for chapter in parser.chapters:
        print(f"Chapter {chapter.number}: {chapter.title}")
    
    for article in parser.articles:
        print(f"Article {article.number}: {article.title}")
        print(f"Content: {article.content}")
        for child in article.children:
            print(f"  {child.type} {child.number}: {child.content}")
    
    # Conclusions
    print(f"Conclusions: {parser.conclusions}")
    
    # Export to JSON
    json_output = parser.export_to_json()
    print(json_output)
