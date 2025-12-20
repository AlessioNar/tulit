import importlib


class TestArticleExtraction:
    def test_import(self):
        importlib.import_module('tulit.parsers.strategies.article_extraction')
