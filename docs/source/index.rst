Welcome to tulit's documentation!
===================================

**tulit** retrieves the legislation of the European Union and of its 27 Member
States from their official sources, as adopted and as in force on any date, and
converts it to one format, legalJSON, whatever the source publishes (XML, HTML,
JSON or PDF). It also writes Akoma Ntoso 3.0 and LEOS packages.

.. code-block:: python

    import tulit

    doc = tulit.fetch("32016R0679")                                   # GDPR, from EUR-Lex
    doc = tulit.fetch("10001597", jurisdiction="AT", version="consolidated")
    xml = tulit.export(doc, to="akn")

Start with :doc:`getting_started`; :doc:`jurisdictions` lists what each country
offers, :doc:`legaljson` describes the output, and :doc:`export` the Akoma Ntoso
and LEOS formats.

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   getting_started
   jurisdictions
   legaljson
   export
   migration
   architecture

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api
   client
   parsers

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

