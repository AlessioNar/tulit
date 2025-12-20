import importlib


class TestCellarStandard:
    def test_import(self):
        importlib.import_module('tulit.parsers.html.cellar.cellar_standard')
