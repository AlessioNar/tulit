import importlib


class TestLegifrance:
    def test_import(self):
        importlib.import_module('tulit.parser.json.legifrance')
