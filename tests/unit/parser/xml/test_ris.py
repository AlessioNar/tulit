import pytest

from tulit.parser.parser import LegalJSONValidator
from tulit.parser.registry import get_parser
from tulit.parser.xml.ris import RISParser, classify_division, german_ordinal


@pytest.fixture(scope='module')
def dsg(data_root):
    folder = data_root / 'sources' / 'member_states' / 'austria' / 'ris' / '10001597'
    return RISParser().parse(str(folder)).to_dict()


@pytest.mark.parametrize('word, number', [
    ('Erstes', 1), ('Zweytes', 2), ('Drittes', 3), ('Eilftes', 11), ('Sechzehntes', 16),
    ('Zwanzigstes', 20), ('Zwey u. zwanzigstes', 22), ('Dreyßigstes', 30), ('Erste', 1),
])
def test_german_ordinal(word, number):
    assert german_ordinal(word) == number


@pytest.mark.parametrize('text, expected', [
    ('5. Abschnitt', ('section', '5')),
    ('1. Hauptstück', ('chapter', '1')),
    ('Erster Theil', ('part', '1')),
    ('Zweyte Abtheilung', ('title', '2')),
    ('Sechs u. zwanzigstes Hauptstück.', ('chapter', '26')),
    ('2. Unterabschnitt', ('subsection', '2')),
    ('Artikel 2', ('part', '2')),
    ('Einleitung.', ('part', 'einleitung')),
    ('Von dem Sachenrechte.', None),
])
def test_classify_division(text, expected):
    assert classify_division(text) == expected


def test_registered_as_ris():
    assert isinstance(get_parser('ris'), RISParser)


def test_preface_and_formula(dsg):
    assert dsg['preface'].startswith('Bundesgesetz zum Schutz natürlicher Personen')
    assert dsg['preamble']['formula'] == 'Der Nationalrat hat beschlossen:'


def test_divisions_are_typed_and_nested(dsg):
    chapters = {c['eId']: c for c in dsg['chapters']}
    assert chapters['prt_1']['heading'] == '(Verfassungsbestimmung)'
    assert chapters['cpt_1'] == {
        'eId': 'cpt_1', 'type': 'chapter', 'num': '1. Hauptstück',
        'heading': 'Durchführung der Datenschutz-Grundverordnung und ergänzende Regelungen',
        'parent': 'prt_2'}
    assert chapters['sct_1']['parent'] == 'cpt_1'


def test_articles_and_paragraphs(dsg):
    articles = {a['eId']: a for a in dsg['articles']}
    assert list(articles) == ['art_1', 'art_4', 'art_5', 'art_14', 'art_34', 'art_35', 'art_35a']
    art1 = articles['art_1']
    assert art1['num'] == '§ 1'
    assert art1['heading'] == 'Grundrecht auf Datenschutz'
    assert art1['parent'] == 'prt_1'
    assert art1['children'][0]['eId'] == 'par_1'
    # the § number is the article num, not part of the paragraph text
    assert art1['children'][0]['text'].startswith('(1) Jedermann')


def test_lists_fold_into_their_paragraph(dsg):
    art34 = next(a for a in dsg['articles'] if a['eId'] == 'art_34')
    paragraph = next(c for c in art34['children'] if c['eId'] == 'par_2')
    assert '1. spezielle Verfahren' in paragraph['text']


def test_structure_tree(dsg):
    part2 = dsg['structure'][1]
    assert part2['eId'] == 'prt_2'
    assert part2['children'][0]['eId'] == 'cpt_1'


def test_output_is_valid_legaljson(dsg):
    assert LegalJSONValidator().validate(dsg)
