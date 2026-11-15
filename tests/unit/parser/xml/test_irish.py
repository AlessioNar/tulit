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
    # the date of passing, '[24th May, 2018]', is not part of the long title
    assert len(enacted['preamble']['recitals']) == 1


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


def _parse(tmp_path, body, front=''):
    path = tmp_path / 'act.xml'
    path.write_text(f'<act><metadata><title>Test Act</title></metadata><frontmatter>{front}</frontmatter>'
                    f'<body>{body}</body></act>', encoding='utf-8')
    return IrishActParser().parse(str(path)).to_dict()


def test_amending_section_keeps_quoted_subsections(tmp_path):
    # Data Protection (Amendment) Act 2003, section 3 (trimmed)
    doc = _parse(tmp_path, '<sect id="SEC3"><number>3</number>'
                 '<p><b>3.</b><emdash/>Section 2 of the Principal Act is amended<emdash/></p>'
                 '<p>(<i>a</i>) by the substitution of the following subsection for subsection (1):</p>'
                 '<p><odq/>(1) A data controller shall comply with the following provisions.</p>'
                 '<p>(2) Data shall be accurate.<cdq/>,</p>'
                 '<p>(<i>b</i>) by the deletion of subsection (6).</p></sect>')
    [child] = doc['articles'][0]['children']
    assert child['text'].startswith('Section 2 of the Principal Act is amended—')
    assert child['amendment']['action'] == 'amend'
    assert child['amendment']['amended_act'] == 'Principal Act'
    assert child['amendment']['quoted'] == [
        {'kind': 'text', 'text': '(1) A data controller shall comply with the following provisions. '
                                 '(2) Data shall be accurate.'}]


def test_amendment_names_the_amended_act(tmp_path):
    doc = _parse(tmp_path, '<sect id="SEC175"><number>175</number>'
                 '<p><b>175.</b><emdash/>Section 13A of the Electoral Act 1992 is amended by the insertion '
                 'of the following subsection after subsection (3B):</p><p><odq/>(3C) Text.<cdq/>.</p></sect>'
                 '<sect id="SEC1"><number>1</number><p><b>1.</b><emdash/>(1) This Act may be cited as the '
                 'Test Act.</p></sect>')
    amending, ordinary = doc['articles']
    assert amending['children'][0]['amendment']['amended_act'] == 'Electoral Act 1992'
    assert ordinary['children'][0]['eId'] == 'par_1' and ordinary['children'][0]['amendment'] is None


def test_section_without_number_element_and_repealed_section(tmp_path):
    # Revised Acts: an inserted section has no <number>; a repealed one only '9.—'
    doc = _parse(tmp_path, '<sect id="SEC32K"><p><b>32K.</b><emdash/>A person shall not question it;&amp;nbsp;</p>'
                 '</sect><sect id="SEC9"><number>9</number><p><b>9.</b><emdash/></p></sect>')
    inserted, repealed = doc['articles']
    assert inserted['num'] == 'Section 32K'
    assert inserted['children'][0]['text'] == 'A person shall not question it;'
    assert repealed['children'] == []


def test_early_act_sections_are_paragraphs(tmp_path):
    # Constitution of the Irish Free State (Saorstát Eireann) Act, 1922
    doc = _parse(tmp_path, '<p>DÁIL EIREANN sitting as a Constituent Assembly hereby proclaims:</p>'
                 '<p>1. The Constitution set forth in the First Schedule shall be the Constitution.</p>'
                 '<p>2. The said Constitution shall be construed with reference to the Treaty.</p>',
                 front='<p>AN ACT TO ENACT A CONSTITUTION FOR THE IRISH FREE STATE.</p>')
    assert [(a['num'], a['children'][0]['text']) for a in doc['articles']] == [
        ('Section 1', 'The Constitution set forth in the First Schedule shall be the Constitution.'),
        ('Section 2', 'The said Constitution shall be construed with reference to the Treaty.')]
    assert doc['preamble']['formula'].startswith('DÁIL EIREANN')
    assert doc['preamble']['recitals'][0]['text'].startswith('AN ACT TO ENACT')
