Parsers
===============

This subpackage contains modules for parsing legal documents in various formats into a JSON representation.

The formats currently supported are:

* **XML Formats:**
  
  * Formex 4 (EU legislative documents)
  * Akoma Ntoso 3.0 (multiple variants: EU, German LegalDocML, Luxembourg CSD13)
  * BOE XML (Spanish Official Gazette)

* **HTML Formats:**
  
  * Cellar XHTML (semantic structure)
  * Cellar Standard HTML (simple structure)
  * EU Legislative Proposals

Core Parser Architecture
-------------------------

.. automodule:: tulit.parser.parser
    :members:
    :undoc-members:
    :show-inheritance:

Domain Models
-------------

.. automodule:: tulit.parser.models
    :members:
    :undoc-members:
    :show-inheritance:

Parser Registry
---------------

.. automodule:: tulit.parser.registry
    :members:
    :undoc-members:
    :show-inheritance:

Text Normalization
------------------

.. automodule:: tulit.parser.normalization
    :members:
    :undoc-members:
    :show-inheritance:

Parser Exceptions
-----------------

.. automodule:: tulit.parser.exceptions
    :members:
    :undoc-members:
    :show-inheritance:

XML Parsers
-----------

Base XML Parser
~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.xml.xml
    :members:
    :undoc-members:
    :show-inheritance:

XML Helpers
~~~~~~~~~~~

.. automodule:: tulit.parser.xml.helpers
    :members:
    :undoc-members:
    :show-inheritance:

Formex Parser
~~~~~~~~~~~~~

.. automodule:: tulit.parser.xml.formex
    :members:
    :undoc-members:
    :show-inheritance:
    :exclude-members: main

Akoma Ntoso Parsers
~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.xml.akomantoso.base
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: tulit.parser.xml.akomantoso.akn4eu
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: tulit.parser.xml.akomantoso.german
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: tulit.parser.xml.akomantoso.luxembourg
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: tulit.parser.xml.akomantoso.utils
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: tulit.parser.xml.akomantoso.extractors
    :members:
    :undoc-members:
    :show-inheritance:

BOE Parser
~~~~~~~~~~

.. automodule:: tulit.parser.xml.boe
    :members:
    :undoc-members:
    :show-inheritance:

HTML Parsers
------------

Base HTML Parser
~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.html.html_parser
    :members:
    :undoc-members:
    :show-inheritance:

Cellar HTML Parsers
~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.html.cellar.cellar
    :members:
    :undoc-members:
    :show-inheritance:
    :exclude-members: main

.. automodule:: tulit.parser.html.cellar.cellar_standard
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: tulit.parser.html.cellar.proposal
    :members:
    :undoc-members:
    :show-inheritance:

Other HTML Parsers
~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.html.veneto
    :members:
    :undoc-members:
    :show-inheritance:

Article Extraction Strategies
------------------------------

.. automodule:: tulit.parser.strategies.article_extraction
    :members:
    :undoc-members:
    :show-inheritance:
