Getting Started
===============

tulit is hosted on PyPi, and documentation is published on readthedocs.io.

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

The `tulit` package main components are:
* a client to query and retrieve data from a variety of legal data sources. Currently the package supports the Cellar, LegiLux and Normattiva.
* a parser to convert legal documents from a variety of formats to a json representation.

Retrieving legal documents
---------------------------

The `tulit` package provides a client to query and retrieve data from a variety of legal data sources. The following code snippet shows how to use the `tulit` package to retrieve a legal document from Cellar, given its CELEX number:

.. code-block:: python

    from tulit.client.cellar import CellarClient
    
    client = CellarClient(download_dir='./database', log_dir='./logs')

    file_format = 'fmx4' # Or xhtml
    celex = "32024R0903"

    documents = client.download(celex=celex, format=file_format)

    # Location of the documents
    print(documents)

Parsing legal documents
-----------------------

The `tulit` parsers support legislative documents in the following formats:

**XML Formats:**
  * Akoma Ntoso 3.0 (EU, German LegalDocML, Luxembourg variants)
  * FORMEX 4 (EU legislative documents)
  * BOE XML (Spanish Official Gazette)

**HTML Formats:**
  * Cellar XHTML (semantic structure)
  * Cellar Standard HTML
  * EU Legislative Proposals

Parsing XML Documents
~~~~~~~~~~~~~~~~~~~~~

**Akoma Ntoso:** The package automatically detects the variant (EU, German, Luxembourg) based on namespace and structure:

.. code-block:: python

    from tulit.parsers.xml.akomantoso import AkomaNtosoParser, create_akn_parser
    
    # Automatic variant detection
    parser = create_akn_parser('tests/data/akn/eu/32014L0092.akn')
    parser.parse('tests/data/akn/eu/32014L0092.akn')
    
    # Or use specific parser directly
    from tulit.parsers.xml.akomantoso import AKN4EUParser, GermanLegalDocMLParser
    parser = AKN4EUParser()
    parser.parse('tests/data/akn/eu/32014L0092.akn')

**FORMEX 4:** Parse EU legislative documents in FORMEX format:

.. code-block:: python

    from tulit.parsers.xml.formex import Formex4Parser

    parser = Formex4Parser()
    formex_file = 'tests/data/formex/c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.02/DOC_1/L_202400903EN.000101.fmx.xml'
    parser.parse(formex_file)

Parsing HTML Documents
~~~~~~~~~~~~~~~~~~~~~~

**Cellar HTML:** Parse documents from EU Cellar in semantic XHTML format:

.. code-block:: python

    from tulit.parsers.html.cellar import CellarHTMLParser
    
    parser = CellarHTMLParser()
    html_file = 'tests/data/html/c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.03/DOC_1.html'
    parser.parse(html_file)

**Cellar Standard HTML:** Parse documents with simple <TXT_TE> structure:

.. code-block:: python

    from tulit.parsers.html.cellar import CellarStandardHTMLParser
    
    parser = CellarStandardHTMLParser()
    parser.parse('document.html')

**EU Proposals:** Parse legislative proposals with special structure:

.. code-block:: python

    from tulit.parsers.html.cellar import ProposalHTMLParser
    
    parser = ProposalHTMLParser()
    parser.parse('proposal.html')


Accessing Parsed Content
~~~~~~~~~~~~~~~~~~~~~~~~

After parsing, the document structure is available through parser attributes:

.. code-block:: python
    
    # Metadata and preface
    print(parser.preface)
    
    # Preamble components
    print(parser.citations)
    print(parser.recitals)
    print(parser.formula)
    print(parser.preamble_final)
    
    # Body structure
    print(parser.chapters)
    print(parser.articles)
    
    # Conclusions
    print(parser.conclusions)
    
    # Export to JSON
    json_output = parser.export_to_json()

Using the Parser Registry
~~~~~~~~~~~~~~~~~~~~~~~~~~

The parser registry allows dynamic parser selection based on format:

.. code-block:: python

    from tulit.parsers.registry import get_parser_for_format
    
    # Automatically get the right parser for a format
    parser = get_parser_for_format('akn')
    parser.parse('document.akn')
    
    # Supported formats: 'akn', 'formex', 'fmx4', 'xhtml', 'html', 'boe'

Advanced Features
~~~~~~~~~~~~~~~~~

**Text Normalization:** Use normalization strategies for consistent text processing:

.. code-block:: python

    from tulit.parsers.normalization import create_html_normalizer, create_xml_normalizer
    
    normalizer = create_html_normalizer()
    clean_text = normalizer.normalize(raw_text)

**Custom Article Extraction:** Implement custom article extraction strategies:

.. code-block:: python

    from tulit.parsers.strategies.article_extraction import FormexArticleStrategy
    
    strategy = FormexArticleStrategy()
    articles = strategy.extract_articles(root_element)

**Domain Models:** Work with structured domain objects:

.. code-block:: python

    from tulit.parsers.models import Article, Citation, Recital
    
    # Models provide type-safe access to document components
    for article in parser.articles:
        print(f"Article {article.number}: {article.title}")
        for child in article.children:
            print(f"  {child.type}: {child.content}")

