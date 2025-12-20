import importlib


class TestFormex:
    def test_import(self):
        importlib.import_module('tulit.parsers.xml.formex')
