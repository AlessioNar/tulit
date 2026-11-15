Python API
==========

The stable interface of tulit is small:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Name
     - Purpose
   * - ``tulit.fetch(identifier, jurisdiction=None, version=None, date=None, language=None, download_dir=None, metadata=True, validate=True, **options)``
     - Download an act from its official source and return it as legalJSON.
   * - ``tulit.download(identifier, ...)``
     - The official file of an act, without parsing it (also for scanned acts).
   * - ``tulit.export(doc, to='akn', path=None)``
     - legalJSON to Akoma Ntoso 3.0 (``akn``) or a LEOS package (``leg``).
   * - ``tulit.errors``
     - The errors tulit raises.
   * - ``tulit.quality``
     - Checks and counts of a legalJSON document.
   * - ``tulit.sources``
     - ``list_sources()`` and ``get_source(code)``: the jurisdictions and their sources.
   * - the ``tulit`` command
     - ``get``, ``parse``, ``export``, ``dump``, ``sources``, ``formats``.

From 1.0, these follow semantic versioning: a minor release adds and never
removes; a breaking change waits for a major release and is announced by a
deprecation warning in a minor release first. The legalJSON schema has its own
version (see :doc:`legaljson`). Clients and parsers (``tulit.client``,
``tulit.parser``) remain available for direct use, but their signatures may change
in minor releases as the official sources change.

.. autofunction:: tulit.fetch

.. autofunction:: tulit.download

.. autofunction:: tulit.export

Errors
------

.. automodule:: tulit.errors

All errors derive from ``TulitError``, so one ``except`` catches whatever tulit
raises:

.. code-block:: python

    from tulit.errors import NetworkError, TulitError, UnsupportedError

    try:
        doc = tulit.fetch("Lov 2018-06-15 nr. 38", jurisdiction="NO")
    except UnsupportedError as e:      # no such jurisdiction, version, option...
        print(e)
    except NetworkError:               # the source is down: try again later
        ...

Quality
-------

.. automodule:: tulit.quality
   :members: check, counts, Problem
