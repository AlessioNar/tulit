import importlib


class TestModelsModule:
    def test_import(self):
        importlib.import_module('tulit.parser.models')
