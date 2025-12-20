import importlib


class TestNormalizationModule:
    def test_import(self):
        importlib.import_module('tulit.parser.normalization')
