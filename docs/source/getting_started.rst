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

``tulit.fetch`` downloads an act from its official source, parses it and
returns validated legalJSON with its metadata:

.. code-block:: python

    import tulit

    doc = tulit.fetch("32024R0903")  # Interoperable Europe Act

    doc["meta"]["eli"]          # 'http://data.europa.eu/eli/reg/2024/903/oj'
    doc["meta"]["in_force"]     # True
    article = doc["articles"][0]
    article["eId"], article["heading"]   # ('art_1', 'Subject matter and scope')

Options:

* ``jurisdiction``: ``'EU'`` (default) or a Member State code (``'AT'``,
  ``'ES'``, ...). It is inferred when the identifier is an ELI URI.
* ``version``: ``'original'`` (the text as adopted) or ``'consolidated'``
  (the text in force). Defaults to ``'original'`` where the source
  publishes it.
* ``date``: ISO date of the consolidated version; defaults to today.
* ``language``: ISO 639-3 language code (``'eng'``, ``'fra'``, ``'deu'``,
  ...); defaults to the source's main language.
* ``download_dir``: keep the source files in this directory. By default they
  go to a temporary directory that is removed afterwards.
* ``metadata``: attach the metadata as ``meta`` (default ``True``).
* ``validate``: validate the result against the legalJSON schema (default
  ``True``); raises ``tulit.parser.exceptions.ValidationError`` otherwise.
* source-specific options, such as ``format`` for the EU: ``'fmx4'``
  (Formex 4, default), ``'xhtml'`` or ``'html'``.

.. code-block:: python

    gdpr_fr = tulit.fetch("32016R0679", format="xhtml", language="fra")
    gdpr_fr["meta"]["repeals"]   # ['31995L0046']

    # Member States: national identifier or ELI, original or consolidated
    dsg = tulit.fetch("10001597", jurisdiction="AT")
    lopd = tulit.fetch("BOE-A-2018-16673", jurisdiction="ES",
                       version="consolidated", date="2021-01-01")
    dpa = tulit.fetch("http://www.irishstatutebook.ie/eli/2018/act/7")
    lopd["meta"]["version_date"]   # '2019-06-25'


Sources
-------

Each jurisdiction has one source, all official: the EU (Cellar), Austria
(RIS), Belgium (Moniteur belge and Justel), Bulgaria (Държавен вестник),
Croatia (Narodne novine), Cyprus (Official Gazette), Czechia (e-Sbírka),
Denmark (Retsinformation), Estonia (Riigi Teataja), Finland (Finlex), France
(Journal officiel and Légifrance, from the DILA open data), Germany
(Rechtsinformationen des Bundes), Greece (ΦΕΚ), Hungary (Nemzeti
Jogszabálytár), Ireland (Irish Statute Book and Revised Acts), Italy
(Normattiva), Latvia (Latvijas Vēstnesis and Likumi.lv), Lithuania (Teisės
aktų registras), Luxembourg (Legilux), Malta (Legislation Malta), the
Netherlands (Basiswettenbestand and Staatsblad), Poland (Sejm ELI API),
Portugal (Diário da República), Romania (Portal Legislativ), Slovakia
(Slov-Lex), Slovenia (PISRS), Spain (BOE) and Sweden (Riksdagen). ``tulit
sources`` lists them with the versions, languages and identifiers they
accept.

Cyprus, Greece, Malta and Portugal publish PDF; reading them needs the ``pdf`` extra:

.. code-block:: console

    $ pip install 'tulit[pdf]'

.. code-block:: python

    tulit.fetch("Cap. 586", jurisdiction="MT")                          # consolidated Chapter
    tulit.fetch("Lei n.º 58/2019, de 8 de agosto", jurisdiction="PT")   # act as published
    tulit.fetch("IKS", jurisdiction="EE", version="consolidated", date="2024-06-01")
    tulit.fetch("BGBl. I Nr. 5/2024", jurisdiction="AT")                 # law as adopted
    tulit.fetch("ν. 4624/2019", jurisdiction="GR")                      # law as published in the ΦΕΚ
    tulit.fetch("2011. évi CXII. törvény", jurisdiction="HU",
                version="consolidated", date="2019-01-01")
    tulit.fetch("https://www.ejustice.just.fgov.be/eli/loi/2018/07/30/2018040581")  # Belgium, by ELI

France needs no credentials: texts published since the last global DILA dump
come from the daily Journal officiel and Légifrance archives. For older texts,
download and extract the global JORF and LEGI dumps from
https://echanges.dila.gouv.fr/OPENDATA/ and pass their folder:

.. code-block:: python

    tulit.fetch("Loi n° 2018-493 du 20 juin 2018", jurisdiction="FR", dump_dir="dila")

Some acts exist only as scanned PDFs without text: the Moniteur belge
before June 1997 and the Cypriot Official Gazette before about 2015.
``fetch`` cannot parse them and says so; ``tulit.download`` returns the
official file of any act, scanned or not, without parsing it:

.. code-block:: python

    scan = tulit.download("constitution/1994/02/17/1994021048", jurisdiction="BE",
                          download_dir="acts")
    scan["path"], scan["parser"]   # ('acts/BE/1994021048_fra_scan.pdf', None)
    scan["meta"]["page"]           # 2: where the act starts in the issue
    tulit.download("4252, 23.7.2010", jurisdiction="CY")   # Gazette issue holding a 2010 law

The sources are listed in code as well:

.. code-block:: python

    from tulit.sources import get_source, list_sources

    for code in list_sources():
        source = get_source(code)
        print(code, source.name, source.versions)
    get_source("DK").identifier_help

Some sources publish only one version or cannot select a date; ``fetch``
raises ``ValueError`` when a request cannot be met. The coverage table in the
README tracks the progress towards all 27 Member States.


Command line
------------

The same is available from the command line:

.. code-block:: console

    $ tulit get 32024R0903 -o 32024R0903.json
    $ tulit get 32016R0679 --format xhtml --language fra
    $ tulit get BOE-A-2018-16673 -j ES --version consolidated --date 2021-01-01
    $ tulit parse --format akn 32014L0092.akn -o 32014L0092.json
    $ tulit formats
    $ tulit sources

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
* ``meta`` (added by ``fetch``): ``jurisdiction``, ``language``,
  ``version`` and ``version_date`` (the FRBR expression of the text),
  ``eli``, ``date_document``, ``in_force``, ``source`` and ``valid``; for EU
  acts also ``celex``, ``cellar_uuid``, ``amends``, ``repeals`` and
  ``corrects``.

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

    from tulit.client.state.italy import NormattivaAKNClient

    client = NormattivaAKNClient(download_dir="./database")
    client.open_act(date="2024-12-31", code="24G00229")
    path = client.download(date="2024-12-31", code="24G00229")

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
