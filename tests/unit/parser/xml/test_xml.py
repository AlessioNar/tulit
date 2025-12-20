import importlib


class TestXmlModule:
    def test_import(self):
        importlib.import_module('tulit.parsers.xml.xml')
