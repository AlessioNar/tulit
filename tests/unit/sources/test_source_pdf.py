from unittest.mock import patch

import pytest

pytest.importorskip('pdfplumber')

import tulit  # noqa: E402
from tulit.client.state.malta import MaltaLegislationClient  # noqa: E402
from tulit.client.state.portugal import PortugalDREClient  # noqa: E402
from tulit.parser.pdf.layout import join_lines  # noqa: E402
from tulit.parser.pdf.malta import MaltaPDFParser  # noqa: E402
from tulit.parser.pdf.portugal import DiarioRepublicaParser, amendment_action  # noqa: E402
from tulit.sources.mt import eli_path, roman  # noqa: E402
from tulit.sources.pt import act_reference  # noqa: E402


@pytest.fixture
def malta(data_root):
    return data_root / 'sources' / 'member_states' / 'malta'


@pytest.fixture
def portugal(data_root):
    return data_root / 'sources' / 'member_states' / 'portugal'


def test_join_lines():
    assert join_lines(['território na-', 'cional']) == 'território nacional'
    assert join_lines(['aplica -', 'se aos']) == 'aplica -se aos'
    assert join_lines(['of the', 'Council']) == 'of the Council'


@pytest.mark.parametrize('identifier, path', [
    ('Cap. 586', 'cap/586'), ('Chapter 586', 'cap/586'), ('586', 'cap/586'),
    ('Act XII of 2018', 'act/2018/12'), ('L.N. 212 of 2023', 'ln/2023/212'),
    ('https://legislation.mt/eli/cap/586/eng/pdf', 'cap/586'),
])
def test_malta_eli_path(identifier, path):
    assert eli_path(identifier) == path


def test_roman():
    assert (roman('XII'), roman('XX'), roman('XIV')) == (12, 20, 14)


@pytest.mark.parametrize('identifier', [
    'Lei n.º 58/2019, de 8 de agosto', 'lei/58/2019/08/08',
    'https://data.dre.pt/eli/lei/58/2019/08/08/p/dre/pt/html',
])
def test_portugal_act_reference(identifier):
    assert act_reference(identifier) == {'type': 'lei', 'number': '58', 'year': '2019', 'month': '08',
                                         'day': '08', 'region': 'p'}


def test_portugal_citation_without_date():
    # Enough for the consolidated version; the act as published needs its date
    assert (act_reference('Lei n.º 58/2019')['month'], act_reference('Lei n.º 58/2019')['day']) == (None, None)
    with pytest.raises(ValueError):
        act_reference('Lei n.º 58/2019, de 8 de agostro')


def test_portugal_amendment_action():
    assert amendment_action('O artigo 6.º passa a ter a seguinte redação:') == 'replace'
    assert amendment_action('É revogada a Lei n.º 67/98') == 'delete'


class TestMaltaPDFParser:
    def test_chapter(self, malta):
        parser = MaltaPDFParser().parse(str(malta / 'cap_586_eng.pdf'))
        assert parser.preface == 'DATA PROTECTION ACT'
        assert parser.recitals[0]['text'] == 'AN ACT to repeal and to replace the Data Protection Act, Cap. 440.'
        assert (parser.chapters[0]['num'], parser.chapters[0]['heading']) == ('PART I', 'Preliminary')
        first = parser.articles[0]
        assert (first['eId'], first['num'], first['heading'], first['parent']) == (
            'art_1', '1.', 'Short title.', 'prt_I')
        interpretation = parser.articles[2]
        assert interpretation['heading'] == 'Interpretation.'
        assert [c['eId'] for c in interpretation['children']][:2] == ['par_1', 'par_2']
        assert [a['num'] for a in parser.annexes] == ['FIRST SCHEDULE', 'SECOND SCHEDULE']


class TestDiarioRepublicaParser:
    def test_current_layout(self, portugal):
        parser = DiarioRepublicaParser(number='58/2019').parse(str(portugal / 'lei_58_2019_extract.pdf'))
        assert parser.preface == 'Lei n.º 58/2019 de 8 de agosto'
        assert parser.formula.startswith('A Assembleia da República decreta')
        first = parser.articles[0]
        assert (first['eId'], first['num'], first['heading'], first['parent']) == (
            'art_1', 'Artigo 1.º', 'Objeto', 'cpt_I')
        second = parser.articles[1]
        assert [c['eId'] for c in second['children']][:2] == ['par_1', 'par_2']
        amended = next(a for a in parser.articles if a['eId'] == 'art_65')
        assert amended['children'][0]['amendment']['action'] == 'replace'
        assert amended['children'][0]['amendment']['quoted']
        assert parser.conclusions['signature'].startswith('Pelo Primeiro -Ministro')
        assert [a['num'] for a in parser.annexes] == ['ANEXO']

    def test_two_column_layout(self, portugal):
        parser = DiarioRepublicaParser(number='7/2004').parse(str(portugal / 'dec_lei_7_2004_extract.pdf'))
        assert parser.preface == 'Decreto-Lei n.o 7/2004 de 7 de Janeiro'
        assert parser.formula.endswith('o Governo decreta o seguinte:')
        assert (parser.articles[0]['num'], parser.articles[0]['heading']) == ('Artigo 1.o', 'Objecto')
        # A point continuing into the next column stays in its paragraph
        assert [c['eId'] for c in parser.articles[1]['children']] == ['par_1', 'par_2']


class TestPDFSources:
    def test_malta_chapter(self, malta, tmp_path):
        with patch.object(MaltaLegislationClient, 'download', return_value=str(malta / 'cap_586_eng.pdf')) as download:
            doc = tulit.fetch('Cap. 586', jurisdiction='MT', download_dir=str(tmp_path))
        download.assert_called_once_with('cap/586', lang='eng', fmt='pdf')
        assert (doc['meta']['version'], doc['meta']['eli']) == ('consolidated', 'https://legislation.mt/eli/cap/586')

    def test_malta_chapter_original_is_its_act(self, malta, tmp_path):
        with patch.object(MaltaLegislationClient, 'download', return_value=str(malta / 'cap_586_eng.pdf')) as download:
            doc = tulit.fetch('Cap. 586', jurisdiction='MT', version='original', download_dir=str(tmp_path))
        assert download.call_args_list[1].args[0] == 'act/2018/20'
        assert doc['meta']['eli'] == 'https://legislation.mt/eli/act/2018/20'

    def test_malta_acts_in_maltese_are_bilingual(self, tmp_path):
        with pytest.raises(ValueError, match="language='eng'"):
            tulit.fetch('Act XII of 2018', jurisdiction='MT', language='mlt', download_dir=str(tmp_path))

    def test_portugal(self, portugal, tmp_path):
        with patch.object(PortugalDREClient, 'download',
                          return_value=str(portugal / 'lei_58_2019_extract.pdf')) as download:
            doc = tulit.fetch('Lei n.º 58/2019, de 8 de agosto', jurisdiction='PT', download_dir=str(tmp_path))
        assert download.call_args.kwargs['act_type'] == 'lei'
        meta = doc['meta']
        assert (meta['version'], meta['version_date']) == ('original', '2019-08-08')
        assert meta['eli'] == 'https://data.dre.pt/eli/lei/58/2019/08/08/p'


def _lines(texts):
    from tulit.parser.pdf.layout import Line
    return [Line(page=page, text=text, x0=70, x1=400, top=100 + 12 * n, size=10)
            for n, (page, text) in enumerate(texts)]


def test_malta_code_with_long_arrangement_and_books():
    # Civil Code (Cap. 16), trimmed: a multi-page arrangement listing schedules, BOOK and Title headings
    from tulit.parser.pdf.malta import MaltaPDFParser
    lines = _lines([(0, 'CHAPTER 16'), (0, 'CIVIL CODE'), (1, 'ARRANGEMENT OF CODE'),
                    (1, 'Title I. Of the Rights and Duties Arising from Marriage 2-66N'),
                    (2, 'FIRST SCHEDULE'), (3, '1. The title of this Code is the Civil Code.'),
                    (3, 'BOOK FIRST'), (3, 'OF PERSONS'), (3, 'Title I'), (3, 'OF THE RIGHTS AND DUTIES'),
                    (3, 'Sub-title I A'), (3, 'OF GUARDIANSHIP'), (3, '2. (1) Spouses owe each other fidelity.'),
                    (4, 'FIRST SCHEDULE'), (4, 'Fees for acts.')])
    with patch('tulit.parser.pdf.malta.read_lines', return_value=(lines, [], None)):
        doc = MaltaPDFParser().parse('cap_16.pdf').to_dict()
    assert doc['preface'] == 'CIVIL CODE'
    assert [(c['type'], c['num'], c['parent']) for c in doc['chapters']] == [
        ('book', 'BOOK FIRST', None), ('title', 'Title I', 'div_first'), ('chapter', 'Sub-title I A', 'tit_I')]
    assert [a['num'] for a in doc['articles']] == ['1.', '2.']
    assert doc['articles'][1]['parent'] == 'cpt_IA'
    assert [a['num'] for a in doc['annexes']] == ['FIRST SCHEDULE']


def test_malta_legal_notice_title_and_formula():
    from tulit.parser.pdf.malta import MaltaPDFParser
    lines = _lines([(0, 'L.N. 1 of 2026'), (0, 'DEVELOPMENT PLANNING ACT'), (0, '(CAP. 552)'),
                    (0, 'Development Planning (Procedure for Applications and their'),
                    (0, 'Determination) (Amendment) Regulations, 2026'),
                    (0, 'IN EXERCISE of the powers conferred by articles 84 and 85 of'),
                    (0, 'the Development Planning Act, the Minister has made the following regulations:-'),
                    (0, '1. The title of these regulations is the Development Planning Regulations.')])
    with patch('tulit.parser.pdf.malta.read_lines', return_value=(lines, [], None)):
        doc = MaltaPDFParser().parse('ln_2026_1.pdf').to_dict()
    assert doc['preface'] == ('Development Planning (Procedure for Applications and their Determination) '
                              '(Amendment) Regulations, 2026')
    assert doc['preamble']['formula'].startswith('IN EXERCISE of the powers')
    assert len(doc['articles']) == 1
