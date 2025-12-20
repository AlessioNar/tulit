import importlib


class TestParserModule:
    def test_import(self):
        importlib.import_module('tulit.parsers.parser')
