import importlib


class TestArticleExtraction:
    def test_import(self):
        importlib.import_module('tulit.parser.strategies.article_extraction')
