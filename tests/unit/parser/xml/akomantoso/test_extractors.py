import importlib


class TestExtractors:
    def test_import(self):
        importlib.import_module('tulit.parsers.xml.akomantoso.extractors')
