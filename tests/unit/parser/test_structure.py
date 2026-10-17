import pytest
from lxml import etree

from tulit.parser.structure import BodyBuilder, ChildrenBuilder, eid_token, element_text


@pytest.mark.parametrize('num, token', [
    ('5. Abschnitt', '5'),
    ('Chapter III', 'III'),
    ('§ 35a', '35a'),
    ('Art. 2', '2'),
    ('(1a)', '1a'),
    ('(b)', 'b'),
    ('Erster Teil', None),
    (None, None),
])
def test_eid_token(num, token):
    assert eid_token(num) == token


def test_element_text_separates_blocks_only():
    xml = '<a><n>1.</n><p>First <i>in</i>line</p><p>second</p>, end</a>'
    assert element_text(etree.fromstring(xml), block_tags=('n', 'p')) == '1. First inline second, end'


def test_element_text_skips_tags_but_keeps_tail():
    xml = '<a><num>§ 6.</num> (1) Text</a>'
    assert element_text(etree.fromstring(xml), block_tags=(), skip_tags=('num',)) == '(1) Text'


def test_children_builder_numbers_and_extends():
    children = ChildrenBuilder()
    children.add('(1) First', number='1')
    children.extend('1. item')
    children.add('Unnumbered')
    children.add('(1) Repeated number', number='1')
    assert [c['eId'] for c in children.children] == ['par_1', 'unp_1', 'par_1_2']
    assert children.children[0]['text'] == '(1) First 1. item'


def test_body_builder_nests_divisions_and_articles():
    body = BodyBuilder()
    body.division('part', 'Part 1')
    body.division('chapter', 'Chapter 1', heading='General')
    body.article('Article 1', 'Scope', [])
    body.division('chapter', 'Chapter 2')
    body.article('Article 2', None, [])
    body.division('part', 'Part 2')
    body.division('chapter', 'Chapter 1')

    assert [(c['eId'], c['parent']) for c in body.chapters] == [
        ('prt_1', None), ('cpt_1', 'prt_1'), ('cpt_2', 'prt_1'), ('prt_2', None), ('cpt_1_2', 'prt_2')]
    assert [(a['eId'], a['parent']) for a in body.articles] == [('art_1', 'cpt_1'), ('art_2', 'cpt_2')]
    assert body.structure[0]['children'][0]['children'] == [{'eId': 'art_1', 'type': 'article'}]


def test_body_builder_token_override_and_top_level_articles():
    body = BodyBuilder()
    body.article('§ 1', None, [])
    body.division('part', 'Erster Theil', token='1')
    body.close_divisions()
    body.article('§ 2', None, [], token='2')
    assert body.chapters[0]['eId'] == 'prt_1'
    assert [a['parent'] for a in body.articles] == [None, None]
    assert body.structure[-1] == {'eId': 'art_2', 'type': 'article'}
