import pytest

from tulit.parser.parser import LegalJSONValidator
from tulit.parser.registry import get_parser
from tulit.parser.xml.metalex import MetaLexParser


@pytest.fixture(scope='module')
def folder(data_root):
    return data_root / 'sources' / 'member_states' / 'slovakia' / 'slovlex'


@pytest.fixture(scope='module')
def act(folder):
    return MetaLexParser().parse(str(folder / '18_2018_20260818.xml'))


@pytest.fixture(scope='module')
def constitution(folder):
    return MetaLexParser().parse(str(folder / '460_1992_vyhlasene_znenie.xml')).to_dict()


def test_registered():
    assert isinstance(get_parser('metalex'), MetaLexParser)


def test_preface_formula_and_metadata(act):
    doc = act.to_dict()
    assert doc['preface'] == ('ZÁKON z 29. novembra 2017 o ochrane osobných údajov '
                              'a o zmene a doplnení niektorých zákonov')
    assert doc['preamble']['formula'] == 'Národná rada Slovenskej republiky sa uzniesla na tomto zákone:'
    assert act.metadata('slovlex-owl:schvaleny') == '2017-11-29'
    assert act.metadata('slovlex-owl:vyhlaseny') == '2018-01-30'


def test_article_wrapping_the_act_is_transparent(act):
    doc = act.to_dict()
    # Čl. I holds the act itself: its parts are top-level divisions
    assert doc['chapters'][0] == {'eId': 'prt_1', 'type': 'part', 'num': 'PRVÁ ČASŤ',
                                  'heading': 'ZÁKLADNÉ USTANOVENIA', 'parent': None}
    # the amending articles that follow are articles outside any division
    amending = [a for a in doc['articles'] if a['num'].startswith('Čl.')]
    assert [a['eId'] for a in amending] == ['art_IX', 'art_XVI']
    assert all(a['parent'] is None for a in amending)


def test_paragraphs_and_subsections(act):
    paragraph = next(a for a in act.to_dict()['articles'] if a['eId'] == 'art_3')
    assert (paragraph['num'], paragraph['heading'], paragraph['parent']) == ('§ 3', 'Pôsobnosť', 'prt_1')
    assert paragraph['children'][0]['eId'] == 'par_1'
    assert paragraph['children'][0]['text'].startswith('(1) Tento zákon sa vzťahuje')


def test_quoted_annexes_belong_to_the_amending_article(act):
    doc = act.to_dict()
    assert [a['eId'] for a in doc['annexes']] == ['anx_1']
    assert doc['annexes'][0]['num'].startswith('Príloha k zákonu č. 18/2018')


def test_signatories(act):
    assert act.to_dict()['conclusions']['signature']['signatories'] == [
        'Andrej Kiska v. r.', 'Andrej Danko v. r.', 'Robert Fico v. r.']


def test_constitution(constitution):
    assert constitution['preamble']['formula'].startswith('PREAMBULA My, národ slovenský,')
    assert constitution['chapters'][:2] == [
        {'eId': 'tit_1', 'type': 'title', 'num': 'PRVÁ HLAVA', 'heading': None, 'parent': None},
        {'eId': 'sct_1', 'type': 'section', 'num': 'Prvý oddiel', 'heading': 'ZÁKLADNÉ USTANOVENIA',
         'parent': 'tit_1'},
    ]
    article = constitution['articles'][0]
    assert (article['eId'], article['num'], article['parent']) == ('art_1', 'Čl. 1', 'sct_1')


def test_valid(act, constitution):
    assert LegalJSONValidator().validate(act.to_dict())
    assert LegalJSONValidator().validate(constitution)
