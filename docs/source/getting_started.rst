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
    
    format = 'fmx4'

    if format == 'fmx4':
        sparql_query = './tests/metadata/queries/formex_query.rq'
    elif format == 'xhtml':
        sparql_query = './tests/metadata/queries/html_query.rq'
    else:
        print('No valid format')
    
    
    results = send_sparql_query(sparql_query_filepath=sparql_query, celex=celex)
        
    documents = client.download(results, format=format)

    print(documents)

Parsing legal documents
-----------------------

The `tulit` parsers support exclusively legislative documents which were adopted in the following formats:
* Akoma Ntoso 3.0
* FORMEX 4
* XHTML originated from Cellar

The following code snippet shows how to use the `tulit` package to parse a legal document in Akoma Ntoso format:

.. code-block:: python

    from tulit.parsers.xml.akomantoso import AkomaNtosoParser

    parser = AkomaNtosoParser()
    
    file_to_parse = 'tests/data/akn/eu/32014L0092.akn'
    parser.parse(file_to_parse)

A similar approach can be used to parse a legal document in FORMEX and XHTML format:

.. code-block:: python

    from tulit.parsers.xml.formex import FormexParser

    formex_file = 'tests/data/formex/c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.02/DOC_1/L_202400903EN.000101.fmx.xml'
    parser = FormexParser()

    parser.parse(formex_file)

    from tulit.parsers.html.xhtml import HTMLParser

    html_file = 'tests/data/html/c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.03/DOC_1.html'

    parser = HTMLParser()
    parser.parse(html_file)


After parsing the document, the various attributes of the parser can be accessed as follows:

.. code-block:: python
    
    print(parser.preface)
    print(parser.citations)
    print(parser.recitals)
    print(parser.chapters)
    print(parser.articles)


`tulit` clients and parsers can also be called via command line by providing input and output paths of the file to be parsed, for example:

.. code-block:: bash

    python ./tulit/parsers/xml/formex.py --input input/file/path.xml --output output/file/path.json

