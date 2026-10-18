Exporting to Akoma Ntoso and LEOS
=================================

A legalJSON document converts to two XML formats used across European
legislative drafting and publication:

* **Akoma Ntoso 3.0** (OASIS LegalDocML): one XML document, the act with its
  annexes attached inline;
* **LEOS .leg packages**: a zip of Akoma Ntoso documents, the exchange format of
  LEOS (the European Commission's Legislation Editing Open Software) and of
  AKN4EU.

Both are valid against the Akoma Ntoso 3.0 schema bundled with tulit
(``tulit/parser/xml/assets/akomantoso30.xsd``), and tulit reads both back:
every division, article, paragraph, annex and structured amendment survives
the round trip.

From Python
-----------

.. code-block:: python

    import tulit

    doc = tulit.fetch("32024R0903")
    xml = tulit.export(doc, to="akn")                          # bytes
    tulit.export(doc, to="leg", path="32024R0903.leg")         # also written to a file

    from tulit.exporters import validate
    assert validate(xml) == []                                 # errors against the schema

From the command line
---------------------

.. code-block:: console

    $ tulit get 32024R0903 --to akn -o 32024R0903.xml
    $ tulit get 300099 -j LV --to leg -o 300099.leg
    $ tulit export 32024R0903.json --to leg -o 32024R0903.leg     # from a saved legalJSON file
    $ tulit parse --format leg 32024R0903.leg -o 32024R0903.json  # and back

What goes where
---------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - legalJSON
     - Akoma Ntoso
   * - ``meta``
     - ``meta/identification``: FRBR Work (country, number, date), Expression (language,
       version date) and Manifestation, following the Akoma Ntoso naming convention
       (``/akn/lv/act/2018-06-21/300099/lav@2018-06-21``); the ELI and CELEX as
       ``FRBRalias``; every other field in ``meta/proprietary``
   * - ``preface``
     - ``preface/longTitle/p/docTitle``
   * - ``preamble``
     - ``formula`` (enacting formula), ``citations``, ``recitals`` (with ``intro``),
       ``block name="preamble.final"``
   * - ``chapters`` and ``structure``
     - nested ``book``, ``part``, ``title``, ``chapter``, ``section``, ``subsection``,
       ``division`` and ``subtitle``; other division types as ``hcontainer name="..."``
   * - ``articles``
     - ``article`` with ``num``, ``heading`` and one ``paragraph`` per child
       (``par_2`` becomes ``art_1__para_2``)
   * - an ``amendment``
     - ``mod``: the paragraph's text with the quoted new text marked in place
       (``quotedText``) and quoted structures after it (``quotedStructure``); a
       ``textualMod`` in ``meta/analysis`` gives its type (substitution, insertion,
       repeal, renumbering) and the amended act. The legalJSON action and instruction
       are kept as ``tulit:action`` and ``tulit:instruction`` attributes
   * - tables
     - ``table`` with ``caption`` and ``tr``/``td`` rows
   * - ``conclusions``
     - ``conclusions``: the closing text as paragraphs, signatures in
       ``container name="signature"``
   * - ``annexes``
     - ``attachments/attachment/doc name="annex"``, each with its own metadata, its number
       and title in the preface, its children in ``mainBody``

The .leg package
----------------

.. code-block:: text

    main.xml                    documentCollection: references the act
    ACT-300099-lav.xml          the act; its attachments reference the annexes
    ANNEX-1-300099-lav.xml      each annex, as <doc name="ANNEX">

The layout follows the AKN4EU packages of the Publications Office: ``main.xml``
holds a ``documentCollection`` whose ``collectionBody`` has one ``component`` with
a ``documentRef`` to the act's file, and the act refers to each annex's file from
an ``attachment``. File names carry the act's number and language.

Limits
------

* The XML is valid Akoma Ntoso 3.0, not the stricter AKN4EU profile: AKN4EU adds
  required metadata (authority tables of the Publications Office, ``xml:id``
  attributes) that tulit's sources do not provide for national acts.
* Paragraph text is kept as written; inline markup of the source (emphasis,
  references, footnotes) is not, since legalJSON does not hold it.
