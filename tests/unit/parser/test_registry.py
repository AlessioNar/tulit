import importlib


class TestRegistryModule:
    def test_import(self):
        importlib.import_module('tulit.parser.registry')
