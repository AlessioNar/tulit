import importlib


class TestArticleExtraction:
    def test_import(self):
        importlib.import_module('tulit.parser.strategies.article_extraction')


class TestFormexTextExtraction:
    @staticmethod
    def extract(xml):
        from lxml import etree
        from tulit.parser.strategies.article_extraction import FormexArticleStrategy
        return FormexArticleStrategy()._extract_text(etree.fromstring(xml))

    def test_paragraph_number_separated_from_text(self):
        xml = '<PARAG><NO.PARAG>1.</NO.PARAG><ALINEA>This Regulation applies.</ALINEA></PARAG>'
        assert self.extract(xml) == '1. This Regulation applies.'

    def test_list_items_separated(self):
        xml = ('<ALINEA><P>The following apply:</P><LIST><ITEM><NP><NO.P>(a)</NO.P>'
               '<TXT>first;</TXT></NP></ITEM><ITEM><NP><NO.P>(b)</NO.P><TXT>second.</TXT></NP></ITEM></LIST></ALINEA>')
        assert self.extract(xml) == 'The following apply: (a) first; (b) second.'

    def test_inline_markup_not_split(self):
        xml = '<ALINEA>an <HT TYPE="ITALIC">ad hoc</HT>-group of <DATE ISO="20240313">13 March</DATE> 2024</ALINEA>'
        assert self.extract(xml) == 'an ad hoc-group of 13 March 2024'

    def test_no_space_before_closing_punctuation(self):
        xml = '<ALINEA><P>see <TXT>point 1</TXT>, below</P></ALINEA>'
        assert self.extract(xml) == 'see point 1, below'
