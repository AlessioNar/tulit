import importlib


class TestCellar:
    def test_import(self):
        importlib.import_module('tulit.parsers.html.cellar.cellar')
