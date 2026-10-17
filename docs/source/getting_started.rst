Getting Started
===============

Installation
------------

Install the package from PyPI:

.. code-block:: console

    $ pip install tulit

tulit requires Python 3.11 or later. To work on tulit itself, clone the
repository and install it with Poetry:

.. code-block:: console

    $ git clone https://github.com/AlessioNar/tulit.git
    $ cd tulit
    $ poetry install


Quick start
-----------

``tulit.fetch`` downloads an EU act from Cellar, parses it and returns
validated legalJSON with its metadata:

.. code-block:: python

    import tulit

    doc = tulit.fetch("32024R0903")  # Interoperable Europe Act

    doc["meta"]["eli"]          # 'http://data.europa.eu/eli/reg/2024/903/oj'
    doc["meta"]["in_force"]     # True
    article = doc["articles"][0]
    article["eId"], article["heading"]   # ('art_1', 'Subject matter and scope')

Options:

* ``format``: Cellar format to download, ``'fmx4'`` (Formex 4, default),
  ``'xhtml'`` or ``'html'``.
* ``language``: three-letter language code, ``'ENG'`` (default), ``'FRA'``,
  ``'DEU'``, ...
* ``download_dir``: keep the source files in this directory. By default they
  go to a temporary directory that is removed afterwards.
* ``metadata``: attach the Cellar metadata as ``meta`` (default ``True``).
* ``validate``: validate the result against the legalJSON schema (default
  ``True``); raises ``tulit.parser.exceptions.ValidationError`` otherwise.

.. code-block:: python

    gdpr_fr = tulit.fetch("32016R0679", format="xhtml", language="FRA")
    gdpr_fr["meta"]["repeals"]   # ['31995L0046']


Command line
------------

The same is available from the command line:

.. code-block:: console

    $ tulit get 32024R0903 -o 32024R0903.json
    $ tulit get 32016R0679 --format xhtml --language FRA
    $ tulit parse --format akn 32014L0092.akn -o 32014L0092.json
    $ tulit formats

``tulit get`` writes to standard output unless ``-o`` is given. Run
``tulit <command> --help`` for all options, and add ``-v`` to log progress.


The legalJSON structure
-----------------------

Every parser returns the same structure from ``to_dict()``:

* ``preface``: the title of the act.
* ``preamble``: ``formula``, ``citations``, ``recitals_intro``, ``recitals``
  and ``final`` (e.g. "HAVE ADOPTED THIS REGULATION:").
* ``chapters``: every division above article level (part, title, chapter,
  section, subsection) with ``eId``, ``type``, ``num``, ``heading`` and a
  ``parent`` link.
* ``articles``: ``eId``, ``num``, ``heading``, ``parent`` and ``children``;
  each child has an ``eId`` (``par_N`` for numbered paragraphs, ``unp_N``
  for unnumbered blocks), its ``text`` and an ``amendment`` object when it
  amends another act.
* ``structure``: the nested skeleton of the enacting terms, referencing
  divisions and articles by ``eId``.
* ``conclusions``: ``conclusion_text`` and ``signature``.
* ``annexes``: annexes with ``eId``, ``num``, ``heading`` and ``children``.
* ``meta`` (added by ``fetch``): ``celex``, ``eli``, ``cellar_uuid``,
  ``date_document``, ``in_force``, ``amends``, ``repeals``, ``corrects``,
  ``source`` and ``valid``.

The identifiers follow the EU Publications Office subdivision authority
table, so ``art_5`` / ``par_2`` can be appended to an act's ELI. The full
schema is in ``tulit/parser/legaljson_schema.json``.

.. code-block:: python

    for article in doc["articles"]:
        print(article["eId"], article["num"], article["heading"])
        for child in article["children"]:
            print("  ", child["eId"], child["text"][:80])


Parsing local files
-------------------

Parsers are available from the registry by format id or alias
(``tulit formats`` lists them):

.. code-block:: python

    from tulit.parser.registry import get_parser

    parser = get_parser("formex")
    doc = parser.parse("path/to/DOC_1").to_dict()   # a Formex file or folder

    # Akoma Ntoso: the variant (AKN4EU, German LegalDocML, Luxembourg) is
    # detected from the file
    akn = get_parser("akn", file_path="32014L0092.akn")
    doc = akn.parse("32014L0092.akn").to_dict()

The parser classes can also be used directly:

.. list-table::
   :header-rows: 1

   * - Format id
     - Class
     - Documents
   * - ``formex``
     - ``tulit.parser.xml.formex.Formex4Parser``
     - Formex 4 (EU Publications Office)
   * - ``akn``
     - ``tulit.parser.xml.akomantoso.create_akn_parser``
     - Akoma Ntoso, variant detected automatically
   * - ``cellar-xhtml``
     - ``tulit.parser.html.cellar.CellarHTMLParser``
     - EUR-Lex XHTML
   * - ``cellar-html``
     - ``tulit.parser.html.cellar.CellarStandardHTMLParser``
     - EUR-Lex legacy HTML
   * - ``eu-proposal``
     - ``tulit.parser.html.cellar.ProposalHTMLParser``
     - Commission legislative proposals
   * - ``boe``
     - ``tulit.parser.xml.boe.BOEXMLParser``
     - Spanish Official Gazette XML
   * - ``veneto``
     - ``tulit.parser.html.veneto.VenetoHTMLParser``
     - Veneto regional legislation
   * - ``legifrance``
     - ``tulit.parser.json.legifrance.LegifranceParser``
     - Légifrance JSON

Validate any result against the legalJSON schema:

.. code-block:: python

    from tulit.parser.parser import LegalJSONValidator

    LegalJSONValidator().validate(doc)   # True or False


Downloading from other sources
------------------------------

Each source has a client. ``log_dir`` is optional; when given, the client
also writes a ``client.log`` file there.

**EU Cellar** (used by ``tulit.fetch``):

.. code-block:: python

    from tulit.client.eu.cellar import CellarClient

    client = CellarClient(download_dir="./database")
    paths = client.download(celex="32024R0903", format="fmx4", language="ENG")
    meta = client.get_metadata("32024R0903")

**Italy (Normattiva)**:

.. code-block:: python

    from tulit.client.state.normattiva import NormattivaClient

    client = NormattivaClient(download_dir="./database")
    client.download(dataGU="20241231", codiceRedaz="24G00229", fmt="xml")

**Luxembourg (Legilux)**:

.. code-block:: python

    from tulit.client.state.legilux import LegiluxClient

    client = LegiluxClient(download_dir="./database")
    client.download(eli="http://data.legilux.public.lu/eli/etat/leg/loi/2006/07/31/n2/jo")

**Germany (Rechtsinformationssystem)**:

.. code-block:: python

    from tulit.client.state.germany import GermanyClient

    client = GermanyClient(download_dir="./database")
    client.download(
        document_type="legislation", format="html",
        jurisdiction="bund", agent="bgbl-1", year="1979",
        natural_identifier="s1325", point_in_time="2020-06-19",
        version="2", language="deu",
        point_in_time_manifestation="2020-06-19", subtype="regelungstext-1",
    )

Clients for Finland, France, Ireland, Malta, Portugal, Spain and the Veneto
region are documented in :doc:`client`.


Logging
-------

tulit logs through the standard :mod:`logging` module and does not configure
handlers itself. To see progress messages:

.. code-block:: python

    import logging
    logging.basicConfig(level=logging.INFO)
