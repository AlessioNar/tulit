legalJSON
=========

``tulit.fetch`` returns acts as legalJSON: one JSON object per act, the same
shape for every jurisdiction and source format. The JSON Schema is
``tulit/parser/legaljson_schema.json``; ``fetch`` validates its result against it
unless called with ``validate=False``.

Versioning
----------

Each document carries ``schema_version`` (``"1.0"``). Minor versions only add
optional fields, so a reader written for 1.0 reads every 1.x document; a new
major version may change or remove fields, and comes with a migration note.

Top level
---------

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Field
     - Content
   * - ``schema_version``
     - Version of this schema, e.g. ``"1.0"``.
   * - ``meta``
     - Metadata (below).
   * - ``preface``
     - The act's title.
   * - ``preamble``
     - ``formula`` (enacting formula), ``citations`` and ``recitals`` (lists of
       ``{eId, text}``), ``recitals_intro`` and ``final`` (the formula closing the
       preamble, such as "HAS ADOPTED THIS REGULATION:").
   * - ``chapters``
     - Divisions above the article (parts, titles, chapters, sections...), in document
       order: ``{eId, type, num, heading, parent}``, ``parent`` being the eId of the
       enclosing division.
   * - ``articles``
     - Articles in document order: ``{eId, num, heading, parent, children}``.
   * - ``conclusions``
     - Closing text and signatures, as the source gives them.
   * - ``annexes``
     - ``{eId, num, heading, children}``, children as for articles.
   * - ``structure``
     - The same divisions and articles as a tree of references
       (``{eId, type, num, children}``), for navigation.

Identifiers (``eId``) follow the European subdivision table used in ELI URIs:
``prt_``, ``tit_``, ``cpt_``, ``sct_``, ``sbs_`` for divisions, ``art_`` for articles
with the number as published (``art_16a``), and for article children ``par_N``
(numbered paragraphs) and ``unp_N`` (unnumbered blocks).

Article and annex children
--------------------------

.. code-block:: json

    {"eId": "par_2", "text": "The Member States shall ...", "amendment": null}

``text`` is the full readable text. A child holding a table also has ``table``:
``{caption, rows: [[cell, ...], ...], notes}``. A child that amends another act has
a structured ``amendment`` instead of ``null``:

.. code-block:: json

    {"action": "replace",
     "instruction": "Article 5 is replaced by the following:",
     "amended_act": "Regulation (EU) 2016/679",
     "quoted": [{"kind": "text", "text": "..."},
                {"kind": "structure", "children": [{"text": "..."}]}]}

``action`` is one of ``replace``, ``insert``, ``add``, ``delete``, ``amend``,
``repeal``, ``renumber``, ``substitute`` (or ``null`` when the instruction does not
say); ``quoted`` holds the new text, as words (``text``) or as provisions
(``structure``).

Metadata
--------

Always present (with ``fetch(..., metadata=True)``, the default):

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Field
     - Content
   * - ``jurisdiction``
     - ``EU`` or the ISO 3166-1 alpha-2 code of a Member State.
   * - ``language``
     - ISO 639-3 code of the text (``eng``, ``deu``...).
   * - ``version``
     - ``original`` (the act as adopted or published) or ``consolidated`` (the text in
       force on ``version_date``).
   * - ``version_date``
     - ISO date of this version: publication or adoption for originals, the date a
       consolidated text applies from.
   * - ``identifier``
     - The identifier the act was fetched by.
   * - ``source``
     - Address of the official document the text was read from.

Where the source gives them: ``eli``, ``celex``, ``date_document``,
``date_publication``, ``date_in_force``, ``in_force``, ``number``, ``title``,
``amends``, ``repeals``, ``corrects``, and source-specific fields (gazette issue and
page, national identifiers), all listed in the schema.

Quality checks
--------------

``tulit.quality.check(doc)`` reports what a parser can get wrong while still
producing schema-valid legalJSON: duplicate or dangling eIds, empty paragraphs,
markup or page headers left in the text, malformed amendments, missing or non-ISO
metadata. ``tulit.quality.counts(doc)`` gives a document's size.

.. code-block:: python

    from tulit.quality import check, counts

    errors = [p for p in check(doc) if p.severity == "error"]
    counts(doc)   # {'divisions': 8, 'articles': 37, 'paragraphs': 112, ...}
