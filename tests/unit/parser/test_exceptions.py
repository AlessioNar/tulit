import importlib


class TestExceptionsModule:
    def test_import(self):
        importlib.import_module('tulit.parsers.exceptions')
