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

.. automodule:: tulit.parsers.parser
    :members:
    :undoc-members:
    :show-inheritance:

Domain Models
-------------

.. automodule:: tulit.parsers.models
    :members:
    :undoc-members:
    :show-inheritance:

Parser Registry
---------------

.. automodule:: tulit.parsers.registry
    :members:
    :undoc-members:
    :show-inheritance:

Text Normalization
------------------

.. automodule:: tulit.parsers.normalization
    :members:
    :undoc-members:
    :show-inheritance:

Parser Exceptions
-----------------

.. automodule:: tulit.parsers.exceptions
    :members:
    :undoc-members:
    :show-inheritance:

XML Parsers
-----------

Base XML Parser
~~~~~~~~~~~~~~~

.. automodule:: tulit.parsers.xml.xml
    :members:
    :undoc-members:
    :show-inheritance:

XML Helpers
~~~~~~~~~~~

.. automodule:: tulit.parsers.xml.helpers
    :members:
    :undoc-members:
    :show-inheritance:

Formex Parser
~~~~~~~~~~~~~

.. automodule:: tulit.parsers.xml.formex
    :members:
    :undoc-members:
    :show-inheritance:
    :exclude-members: main

Akoma Ntoso Parsers
~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parsers.xml.akomantoso.base
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: tulit.parsers.xml.akomantoso.akn4eu
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: tulit.parsers.xml.akomantoso.german
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: tulit.parsers.xml.akomantoso.luxembourg
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: tulit.parsers.xml.akomantoso.utils
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: tulit.parsers.xml.akomantoso.extractors
    :members:
    :undoc-members:
    :show-inheritance:

BOE Parser
~~~~~~~~~~

.. automodule:: tulit.parsers.xml.boe
    :members:
    :undoc-members:
    :show-inheritance:

HTML Parsers
------------

Base HTML Parser
~~~~~~~~~~~~~~~~

.. automodule:: tulit.parsers.html.html_parser
    :members:
    :undoc-members:
    :show-inheritance:

Cellar HTML Parsers
~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parsers.html.cellar.cellar
    :members:
    :undoc-members:
    :show-inheritance:
    :exclude-members: main

.. automodule:: tulit.parsers.html.cellar.cellar_standard
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: tulit.parsers.html.cellar.proposal
    :members:
    :undoc-members:
    :show-inheritance:

Other HTML Parsers
~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parsers.html.veneto
    :members:
    :undoc-members:
    :show-inheritance:

Article Extraction Strategies
------------------------------

.. automodule:: tulit.parsers.strategies.article_extraction
    :members:
    :undoc-members:
    :show-inheritance:
