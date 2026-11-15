Moving to 1.0
=============

tulit 1.0 keeps the 0.10 API; code written for 0.10 runs unchanged except for
the points below.

What is new
-----------

* ``tulit.export(doc, to='akn'|'leg')``, ``tulit get ... --to akn|leg`` and
  ``tulit export``: Akoma Ntoso 3.0 and LEOS packages (see :doc:`export`); the
  ``leg`` parser reads LEOS packages.
* ``tulit.errors``: every error derives from ``TulitError``.
* legalJSON documents carry ``schema_version`` and ``meta.identifier``.
* ``tulit dump {jorf,legi} --dir DIR`` downloads the French DILA dumps
  (``fetch(..., dump_dir=DIR)``, ``tulit get ... --dump-dir DIR``).

What changed
------------

* **Unsupported requests** (unknown jurisdiction, version, language or option, an
  identifier a source does not recognise) raise ``tulit.errors.UnsupportedError``.
  It is a ``ValueError`` too, so ``except ValueError`` keeps working.
* **The earlier Italian client** ``tulit.client.state.normattiva.NormattivaClient``
  is removed; use ``tulit.fetch(..., jurisdiction="IT")`` or
  ``tulit.client.state.italy.NormattivaAKNClient``.
* **The Akoma Ntoso parser** reads more of what Akoma Ntoso holds: annexes
  (``attachments``), amendments (``mod``), unnumbered articles, ``book``,
  ``division`` and ``subtitle`` divisions, and the closing text of the conclusions
  (``conclusions.conclusion_text``). Akoma Ntoso documents can therefore come out
  with more annexes, divisions and amendments than with 0.10, and a ``section`` in
  a document that also has ``article`` elements is now always a division.
* **legalJSON**: the new fields are optional in the schema, so documents saved by
  0.10 still validate.
* **Packaging**: ``pyproject.toml`` uses the standard ``[project]`` table; the
  extras are unchanged (``pip install "tulit[pdf]"``).
