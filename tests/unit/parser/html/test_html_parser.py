import importlib


class TestHtmlParser:
    def test_import(self):
        importlib.import_module('tulit.parsers.html.html_parser')
