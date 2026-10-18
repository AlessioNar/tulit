"""
Exports of legalJSON documents to other legal formats.

- ``to_akn``: Akoma Ntoso 3.0 XML, annexes attached inline.
- ``to_leg``: a LEOS .leg package, a zip of Akoma Ntoso documents (the
  collection in ``main.xml``, the act, and one file per annex).
"""
from tulit.exporters.akn import to_akn, to_akn_tree, validate
from tulit.exporters.leg import leg_files, to_leg

FORMATS = ('akn', 'leg')

__all__ = ['FORMATS', 'leg_files', 'to_akn', 'to_akn_tree', 'to_leg', 'validate']
