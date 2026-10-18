Client
===============

The tulit Client library supports multiple legal document retrieval sources organized by jurisdiction:

**EU Level Clients**

* **Cellar**: EU Publications Office SPARQL endpoint for retrieving EU legal documents

**Member State Clients**

* **Austria (RIS and the Federal Law Gazette)**: Rechtsinformationssystem des Bundes and the Federal Law Gazette
* **Belgium (Moniteur belge and Justel)**: Moniteur belge / Belgisch Staatsblad and Justel (eJustice)
* **Bulgaria (Държавен вестник)**: State Gazette, acts as published
* **Croatia (Narodne novine)**: Official Gazette, with ELI metadata
* **Cyprus (Official Gazette)**: Official Gazette of the Republic (Government Printing Office)
* **Czechia (e-Sbírka)**: Collection of Laws
* **Denmark (Retsinformation)**: LexDania XML
* **Estonia (Riigi Teataja)**: State Gazette
* **Finland (Finlex)**: Finnish legal database
* **France (DILA open data)**: Journal officiel and consolidated legislation from the DILA open data
* **France (Légifrance PISTE API)**: Légifrance PISTE API (needs credentials)
* **Germany (Rechtsinformationen des Bundes)**: Rechtsinformationen des Bundes (test phase)
* **Greece (ΦΕΚ)**: Government Gazette (ΦΕΚ), National Printing House
* **Hungary (Nemzeti Jogszabálytár)**: National Legislation Database
* **Ireland (Irish Statute Book and Revised Acts)**: Irish Statute Book and Revised Acts
* **Italy (Normattiva)**: Normattiva, Akoma Ntoso export
* **Latvia (Likumi.lv and Latvijas Vēstnesis)**: Likumi.lv and the Latvijas Vēstnesis gazette
* **Lithuania (Teisės aktų registras)**: Register of Legal Acts, via e-seimas.lrs.lt
* **Luxembourg (Legilux)**: Luxembourg legal portal
* **Malta (Legislation Malta)**: Legislation Malta
* **Netherlands (BWB and Staatsblad)**: Basiswettenbestand, wetten.overheid.nl, and the Staatsblad
* **Poland (Sejm ELI API)**: Dziennik Ustaw and Monitor Polski
* **Portugal (Diário da República)**: Diário da República
* **Romania (Portal Legislativ)**: Portal Legislativ web service (Ministry of Justice)
* **Slovakia (Slov-Lex)**: MetaLex XML
* **Slovenia (PISRS)**: PISRS (Ministry of Justice)
* **Spain (BOE)**: Spanish official gazette and consolidated legislation
* **Sweden (Riksdagen)**: consolidated statutes (SFS)

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

Austria (RIS and the Federal Law Gazette)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.austria
     :members:
     :undoc-members:
     :show-inheritance:

Belgium (Moniteur belge and Justel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.belgium
     :members:
     :undoc-members:
     :show-inheritance:

Bulgaria (Държавен вестник)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.bulgaria
     :members:
     :undoc-members:
     :show-inheritance:

Croatia (Narodne novine)
~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.croatia
     :members:
     :undoc-members:
     :show-inheritance:

Cyprus (Official Gazette)
~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.cyprus
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

France (DILA open data)
~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.france_dila
     :members:
     :undoc-members:
     :show-inheritance:

France (Légifrance PISTE API)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.legifrance
     :members:
     :undoc-members:
     :show-inheritance:

Germany (Rechtsinformationen des Bundes)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.germany
     :members:
     :undoc-members:
     :show-inheritance:

Greece (ΦΕΚ)
~~~~~~~~~~~~

.. automodule:: tulit.client.state.greece
     :members:
     :undoc-members:
     :show-inheritance:

Hungary (Nemzeti Jogszabálytár)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.hungary
     :members:
     :undoc-members:
     :show-inheritance:

Ireland (Irish Statute Book and Revised Acts)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.irishstatutebook
     :members:
     :undoc-members:
     :show-inheritance:

Italy (Normattiva)
~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.italy
     :members:
     :undoc-members:
     :show-inheritance:

Latvia (Likumi.lv and Latvijas Vēstnesis)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.latvia
     :members:
     :undoc-members:
     :show-inheritance:

Lithuania (Teisės aktų registras)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.lithuania
     :members:
     :undoc-members:
     :show-inheritance:

Luxembourg (Legilux)
~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.legilux
     :members:
     :undoc-members:
     :show-inheritance:

Malta (Legislation Malta)
~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.malta
     :members:
     :undoc-members:
     :show-inheritance:

Netherlands (BWB and Staatsblad)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

Portugal (Diário da República)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.portugal
     :members:
     :undoc-members:
     :show-inheritance:

Romania (Portal Legislativ)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.romania
     :members:
     :undoc-members:
     :show-inheritance:

Slovakia (Slov-Lex)
~~~~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.slovakia
     :members:
     :undoc-members:
     :show-inheritance:

Slovenia (PISRS)
~~~~~~~~~~~~~~~~

.. automodule:: tulit.client.state.slovenia
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
