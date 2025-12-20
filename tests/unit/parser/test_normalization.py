import importlib


class TestNormalizationModule:
    def test_import(self):
        importlib.import_module('tulit.parsers.normalization')
