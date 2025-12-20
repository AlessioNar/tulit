import importlib


class TestHelpers:
    def test_import(self):
        importlib.import_module('tulit.parsers.xml.helpers')
