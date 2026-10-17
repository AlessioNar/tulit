import pytest

from tulit.parser.parser import LegalJSONValidator
from tulit.parser.registry import get_parser
from tulit.parser.xml.irish import IrishActParser


@pytest.fixture(scope='module')
def folder(data_root):
    return data_root / 'sources' / 'member_states' / 'ireland' / 'isb'


@pytest.fixture(scope='module')
def enacted(folder):
    return IrishActParser().parse(str(folder / '2018_act_7_enacted.xml')).to_dict()


@pytest.fixture(scope='module')
def revised(folder):
    return IrishActParser().parse(str(folder / '2018_act_7_revised.xml')).to_dict()


def test_registered():
    assert isinstance(get_parser('ie-act'), IrishActParser)


def test_front_matter(enacted):
    assert enacted['preface'] == 'DATA PROTECTION ACT 2018'
    assert enacted['preamble']['formula'] == 'Be it enacted by the Oireachtas as follows:'
    # characters encoded as elements are restored
    assert enacted['preamble']['recitals'][0]['text'].startswith(
        'An Act to establish a body to be known as An Coimisiún um Chosaint Sonraí')


def test_parts_and_chapters(enacted):
    assert enacted['chapters'][0] == {'eId': 'prt_1', 'type': 'part', 'num': 'PART 1',
                                      'heading': 'Preliminary and General', 'parent': None}
    assert all(c['parent'] is not None for c in enacted['chapters'] if c['type'] == 'chapter')


def test_sections_and_subsections(enacted):
    section = next(a for a in enacted['articles'] if a['eId'] == 'art_1')
    assert (section['num'], section['heading'], section['parent']) == (
        'Section 1', 'Short title, citation and commencement', 'prt_1')
    assert [c['eId'] for c in section['children']] == ['par_1', 'par_2', 'par_3']
    # the section number opening the first subsection is not repeated in the text
    assert section['children'][0]['text'] == '(1) This Act may be cited as the Data Protection Act 2018.'


def test_footnotes_and_annotations_left_out(enacted, revised):
    texts = ' '.join(c['text'] for doc in (enacted, revised) for a in doc['articles'] for c in a['children'])
    assert 'OJ No. L 119' not in texts
    assert 'Editorial Notes' not in texts and 'Annotations' not in texts


def test_revised_has_the_same_structure(enacted, revised):
    assert [c['eId'] for c in revised['chapters']] == [c['eId'] for c in enacted['chapters']]
    assert revised['preface'] == 'Data Protection Act 2018'


def test_schedule(enacted):
    assert enacted['annexes'][0]['eId'] == 'anx_1'
    assert enacted['annexes'][0]['heading'] == 'Statutory Instruments Revoked'


def test_valid(enacted, revised):
    assert LegalJSONValidator().validate(enacted)
    assert LegalJSONValidator().validate(revised)
