import importlib


class TestBase:
    def test_import(self):
        importlib.import_module('tulit.parsers.xml.akomantoso.base')
