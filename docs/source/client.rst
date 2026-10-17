Client
===============

The tulit Client library supports multiple legal document retrieval sources organized by jurisdiction:

**EU Level Clients**

* **Cellar**: EU Publications Office SPARQL endpoint for retrieving EU legal documents

**Member State Clients**

* **Austria (RIS)**: Rechtsinformationssystem des Bundes and the Federal Law Gazette
* **Croatia (Narodne novine)**: Official Gazette, with ELI metadata
* **Czechia (e-Sbírka)**: Collection of Laws
* **Denmark (Retsinformation)**: LexDania XML
* **Estonia (Riigi Teataja)**: State Gazette
* **Finland (Finlex)**: Finnish legal database
* **France (Legifrance)**: French legal database  
* **Germany (RIS)**: German legal information system
* **Italy (Normattiva)**: Italian legal database
* **Luxembourg (Legilux)**: Luxembourg legal portal
* **Malta**: Maltese legal information
* **Netherlands (BWB)**: Basiswettenbestand, wetten.overheid.nl, and the Staatsblad
* **Poland (Sejm ELI API)**: Dziennik Ustaw and Monitor Polski
* **Portugal (DRE)**: Portuguese official gazette
* **Slovakia (Slov-Lex)**: MetaLex XML
* **Sweden (Riksdagen)**: consolidated statutes (SFS)
* **Spain (BOE)**: Spanish official gazette and consolidated legislation
* **Ireland (Irish Statute Book and Revised Acts)**: Irish legal database

**Regional Clients**

* **Veneto**: Italian regional legislation (Veneto region)

``tulit.fetch`` uses these clients through the sources in ``tulit.sources``,
one per jurisdiction (see :doc:`getting_started`).

.. toctree::
    :maxdepth: 2

Base Client
-----------

.. automodule:: tulit.client.client
     :members:
     :undoc-members:
     :show-inheritance:

EU Clients
----------

.. automodule:: tulit.client.eu.cellar
     :members:
     :undoc-members:
     :show-inheritance:

Member State Clients
--------------------

Austria (RIS)
~~~~~~~~~~~~~

.. automodule:: tulit.client.state.austria
     :members:
     :undoc-members:
     :show-inheritance:

Croatia (Narodne novine)
~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.croatia
     :members:
     :undoc-members:
     :show-inheritance:

Czechia (e-Sbírka)
~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.czechia
     :members:
     :undoc-members:
     :show-inheritance:

Denmark (Retsinformation)
~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.denmark
     :members:
     :undoc-members:
     :show-inheritance:

Estonia (Riigi Teataja)
~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.estonia
     :members:
     :undoc-members:
     :show-inheritance:

Finland (Finlex)
~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.finlex
     :members:
     :undoc-members:
     :show-inheritance:

France (Legifrance)
~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.legifrance
     :members:
     :undoc-members:
     :show-inheritance:

Germany (RIS)
~~~~~~~~~~~~~

.. automodule:: tulit.client.state.germany
     :members:
     :undoc-members:
     :show-inheritance:

Ireland
~~~~~~~

.. automodule:: tulit.client.state.irishstatutebook
     :members:
     :undoc-members:
     :show-inheritance:

Italy (Normattiva)
~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.normattiva
     :members:
     :undoc-members:
     :show-inheritance:

Luxembourg (Legilux)
~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.legilux
     :members:
     :undoc-members:
     :show-inheritance:

Malta
~~~~~

.. automodule:: tulit.client.state.malta
     :members:
     :undoc-members:
     :show-inheritance:

Netherlands (BWB)
~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.netherlands
     :members:
     :undoc-members:
     :show-inheritance:

Poland (Sejm ELI API)
~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.poland
     :members:
     :undoc-members:
     :show-inheritance:

Portugal (DRE)
~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.portugal
     :members:
     :undoc-members:
     :show-inheritance:

Slovakia (Slov-Lex)
~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.slovakia
     :members:
     :undoc-members:
     :show-inheritance:

Spain (BOE)
~~~~~~~~~~~

.. automodule:: tulit.client.state.boe
     :members:
     :undoc-members:
     :show-inheritance:

Sweden (Riksdagen)
~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.sweden
     :members:
     :undoc-members:
     :show-inheritance:

Regional Clients
----------------

Veneto
~~~~~~

.. automodule:: tulit.client.regional.veneto
     :members:
     :undoc-members:
     :show-inheritance:

Sources
-------

Source framework
~~~~~~~~~~~~~~~~

.. automodule:: tulit.sources.base
     :members:
     :undoc-members:
     :show-inheritance:

Source registry
~~~~~~~~~~~~~~~

.. automodule:: tulit.sources.registry
     :members:
     :undoc-members:
     :show-inheritance:
