Parsers
===============

This subpackage contains modules for parsing legal documents in various formats into a JSON representation.

The formats currently supported are:

* **XML Formats:**

  * Formex 4 (EU legislative documents)
  * Akoma Ntoso 3.0 (multiple variants: EU, German LegalDocML, Luxembourg CSD13, Normattiva)
  * BOE XML (Spanish Official Gazette) and BOE consolidated legislation
  * RIS XML and the Federal Law Gazette (Austria), LexDania (Denmark), BWB
    and Staatsblad XML (Netherlands), MetaLex (Slovakia), the Irish Statute
    Book XML, Riigi Teataja XML (Estonia), JORF and LEGI XML (France, DILA)
    and the Portal Legislativ XML (Romania)

* **JSON Formats:** Légifrance, e-Sbírka fragments (Czechia)

* **PDF** (``pdf`` extra): Legislation Malta, Diário da República (Portugal),
  the Official Gazette of Cyprus and the Greek Government Gazette (ΦΕΚ)

* **HTML Formats:**

  * Cellar XHTML (semantic structure)
  * Cellar Standard HTML (simple structure)
  * EU Legislative Proposals
  * Sejm ELI API (Poland), Riksdagen SFS (Sweden), Narodne novine (Croatia),
    Moniteur belge and Justel (Belgium), Държавен вестник (Bulgaria),
    Nemzeti Jogszabálytár (Hungary), Likumi.lv and Latvijas Vēstnesis
    (Latvia), Teisės aktų registras (Lithuania) and PISRS (Slovenia)

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

BOE Consolidated Parser
~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.xml.boe_consolidated
     :members:
     :undoc-members:
     :show-inheritance:

Austrian RIS Parser
~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.xml.ris
     :members:
     :undoc-members:
     :show-inheritance:

Danish LexDania Parser
~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.xml.lexdania
     :members:
     :undoc-members:
     :show-inheritance:

Dutch BWB Parser
~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.xml.bwb
     :members:
     :undoc-members:
     :show-inheritance:

Slovak MetaLex Parser
~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.xml.metalex
     :members:
     :undoc-members:
     :show-inheritance:

Irish Act Parser
~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.xml.irish
     :members:
     :undoc-members:
     :show-inheritance:

Structure Builders
~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.structure
     :members:
     :undoc-members:
     :show-inheritance:

Austrian Federal Law Gazette Parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.xml.bgbl_at
     :members:
     :undoc-members:
     :show-inheritance:

Estonian Riigi Teataja Parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.xml.riigiteataja
     :members:
     :undoc-members:
     :show-inheritance:

Italian Normattiva Akoma Ntoso Parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.xml.akomantoso.normattiva
     :members:
     :undoc-members:
     :show-inheritance:

French DILA Parser (JORF and LEGI)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.xml.dila
     :members:
     :undoc-members:
     :show-inheritance:

Romanian Portal Legislativ Parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.xml.legislatie_ro
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

Romanian Portal Legislativ HTML Parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.html.legislatie_ro
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

Polish Sejm ELI Parser
~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.html.sejm
     :members:
     :undoc-members:
     :show-inheritance:

Swedish SFS Parser
~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.html.riksdagen
     :members:
     :undoc-members:
     :show-inheritance:

Croatian Narodne Novine Parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.html.narodne_novine
     :members:
     :undoc-members:
     :show-inheritance:

Belgian eJustice Parser
~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.html.ejustice
     :members:
     :undoc-members:
     :show-inheritance:

Bulgarian State Gazette Parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.html.darzhaven_vestnik
     :members:
     :undoc-members:
     :show-inheritance:

Hungarian NJT Parser
~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.html.njt
     :members:
     :undoc-members:
     :show-inheritance:

Latvian Likumi Parser
~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.html.likumi
     :members:
     :undoc-members:
     :show-inheritance:

Lithuanian Register of Legal Acts Parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.html.etar
     :members:
     :undoc-members:
     :show-inheritance:

Slovenian PISRS Parser
~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.html.pisrs
     :members:
     :undoc-members:
     :show-inheritance:

JSON Parsers
------------

Czech e-Sbírka Parser
~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.json.esbirka
     :members:
     :undoc-members:
     :show-inheritance:

PDF Parsers
-----------

These need the ``pdf`` extra: ``pip install 'tulit[pdf]'``.

PDF Layout
~~~~~~~~~~

.. automodule:: tulit.parser.pdf.layout
     :members:
     :undoc-members:
     :show-inheritance:

Maltese Legislation Parser
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.pdf.malta
     :members:
     :undoc-members:
     :show-inheritance:

Portuguese Diário da República Parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.pdf.portugal
     :members:
     :undoc-members:
     :show-inheritance:

Cypriot Official Gazette Parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.pdf.cyprus
     :members:
     :undoc-members:
     :show-inheritance:

Greek Government Gazette Parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.parser.pdf.greece
     :members:
     :undoc-members:
     :show-inheritance:

Article Extraction Strategies
------------------------------

.. automodule:: tulit.parser.strategies.article_extraction
    :members:
    :undoc-members:
    :show-inheritance:
