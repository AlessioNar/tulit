from unittest.mock import Mock, patch

import pytest

import tulit
from tulit.client.state.bulgaria import StateGazetteClient, iso_date
from tulit.parser.exceptions import FileLoadError
from tulit.parser.html.darzhaven_vestnik import DarzhavenVestnikParser, amendment_action

INDEX = '''<html><body><form id="_idJsp2" name="_idJsp2" method="post" action="/DVWeb/index.faces">
<a href="#" onclick="return oamSubmitForm('_idJsp2','_idJsp2:_idJsp15',null,[['active_tab','3']]);">Търсене</a>
<input type="hidden" name="javax.faces.ViewState" value="state1"></form></body></html>'''
SEARCH_FORM = '''<html><body><form id="search_form" name="search_form" method="post" action="/DVWeb/searchDV.faces">
<input type="hidden" name="search_form_SUBMIT" value="1">
<input type="text" name="search_form:_idJsp63"><input type="text" name="search_form:_idJsp69">
<select name="search_form:_idJsp71"><option value="">Всички</option></select>
<input type="text" name="search_form:_idJsp79"><input type="text" name="search_form:_idJsp81">
<input type="text" name="search_form:_idJsp83">
<input type="text" name="search_form:from_date"><input type="text" name="search_form:to_date">
<input type="hidden" name="javax.faces.ViewState" value="state2"></form></body></html>'''
RESULTS = '''<html><body><table><tr><td>Брой 38, 20.5.2016<br>Народно събрание<br>Закон за електронната
идентификация<br><table><tr><td>стр. 2 <a href="showMaterialDV.jsp?idMat=103709">Преглед на материала</a></td></tr>
</table></td></tr>
<tr><td>Брой 95, 16.10.2026<br>Народно събрание<br>Закон за изменение и допълнение на Закона за електронната
идентификация<br><table><tr><td>стр. 2 <a href="showMaterialDV.jsp?idMat=246270">Преглед на материала</a></td></tr>
</table></td></tr></table></body></html>'''


@pytest.fixture
def bulgaria(data_root):
    return data_root / 'sources' / 'member_states' / 'bulgaria'


@pytest.mark.parametrize('instruction, action', [
    ('Член 33 се изменя така:', 'replace'),
    ('В чл. 9 ал. 4 се отменя.', 'delete'),
    ('В чл. 18 думите „министъра“ се заличават.', 'delete'),
    ('Създава се ал. 5:', 'add'),
    ('В чл. 24 се правят следните изменения и допълнения:', 'amend'),
    ('Този закон урежда обществените отношения.', None),
])
def test_amendment_action(instruction, action):
    assert amendment_action(instruction) == action


class TestDarzhavenVestnikParser:
    def test_law(self, bulgaria):
        parser = DarzhavenVestnikParser().parse(str(bulgaria / '103709.html'))
        assert parser.recitals_init.startswith('УКАЗ № 139 На основание чл. 98, т. 4 от Конституцията')
        assert parser.preface == 'ЗАКОН за електронната идентификация'
        chapter = parser.chapters[0]
        assert (chapter['eId'], chapter['num'], chapter['heading']) == ('cpt_1', 'Глава първа', 'ОБЩИ ПОЛОЖЕНИЯ')
        section = next(c for c in parser.chapters if c['num'] == 'Раздел I')
        assert (section['heading'], section['parent']) == ('Принудителни административни мерки', 'cpt_9')
        article = parser.articles[1]
        assert (article['eId'], article['num'], article['heading'], article['parent']) == (
            'art_2', 'Чл. 2.', 'Електронен идентификатор', 'cpt_1')
        assert [c['eId'] for c in article['children']] == ['par_1', 'par_2', 'par_3']
        # Points are folded into their paragraph
        assert ' 1. приемане на писмени заявления' in parser.articles[7]['children'][2]['text']
        # Supplementary provisions: top-level divisions, their paragraphs § N
        provisions = [c for c in parser.chapters if c['type'] == 'provisions']
        assert [(c['heading'], c['parent']) for c in provisions] == [
            ('ДОПЪЛНИТЕЛНИ РАЗПОРЕДБИ', None), ('ПРЕХОДНИ И ЗАКЛЮЧИТЕЛНИ РАЗПОРЕДБИ', None)]
        last = parser.articles[-1]
        assert (last['eId'], last['num'], last['parent']) == ('art_p6', '§ 6.', provisions[1]['eId'])
        # The articles quoted by § 5 stay in it
        assert not any(a['num'] == 'Чл. 28.' and a['parent'] == provisions[1]['eId'] for a in parser.articles)
        amending = parser.articles[-2]['children'][0]
        assert amending['amendment']['amended_act'] == 'Закона за електронното управление'
        assert 'Чл. 5. (1) Задълженията по тази глава' in amending['text']
        assert parser.conclusions == {
            'conclusion_text': 'Законът е приет от 43-то Народно събрание на 11 май 2016 г. и е подпечатан с '
                               'официалния печат на Народното събрание.',
            'signature': 'Председател на Народното събрание: Цецка Цачева'}

    def test_amending_law(self, bulgaria):
        parser = DarzhavenVestnikParser().parse(str(bulgaria / '246270.html'))
        assert parser.preface == 'ЗАКОН за изменение и допълнение на Закона за електронната идентификация'
        assert parser.recitals[0]['text'].startswith('(обн., ДВ, бр. 38 от 2016 г.;')
        assert [a['eId'] for a in parser.articles] == [f'art_p{n}' for n in range(1, 6)]
        first = parser.articles[0]['children'][0]['amendment']
        assert first == {'action': 'delete', 'instruction': 'В чл. 9 ал. 4 се отменя.',
                         'amended_act': 'Закона за електронната идентификация', 'quoted': []}
        replace = parser.articles[4]['children'][0]
        assert replace['amendment']['action'] == 'replace'
        assert replace['amendment']['quoted'] == [
            {'kind': 'text', 'text': 'Чл. 33. Удостоверения за овластяване се издават само по електронен път.'}]

    def test_order_with_appendix(self, bulgaria):
        parser = DarzhavenVestnikParser().parse(str(bulgaria / '246423.html'))
        assert parser.recitals_init == 'МИНИСТЕРСТВО НА ТРАНСПОРТА И СЪОБЩЕНИЯТА'
        assert parser.preface.startswith('НАРЕДБА № 33 от 6 октомври 2026 г. за извършване на услуги')
        assert (parser.chapters[0]['num'], parser.chapters[0]['heading']) == ('Раздел I', 'Общи разпоредби')
        annex = parser.annexes[0]
        assert annex['num'] == 'Приложение към чл. 16, ал. 1, т. 9'
        assert annex['heading'].startswith('МИНИМАЛНИ СТАНДАРТИ ЗА КАЧЕСТВО')
        assert parser.conclusions == {'conclusion_text': None, 'signature': 'Министър: Георги Пеев'}

    def test_decree_adopting_rules(self, bulgaria):
        parser = DarzhavenVestnikParser().parse(str(bulgaria / '246530.html'))
        assert parser.formula == 'МИНИСТЕРСКИЯТ СЪВЕТ ПОСТАНОВИ:'
        assert [a['num'] for a in parser.articles][:2] == ['Чл. 1.', '§ 1.']
        # A quotation closed by one mark for two („... „Държавен вестник“.) does not run on
        assert parser.articles[-1]['num'] == '§ 11.'
        assert parser.annexes[0]['num'].startswith('УСТРОЙСТВЕН ПРАВИЛНИК на Изпълнителната агенция')
        assert parser.conclusions['signature'].startswith('Министър-председател: Румен Радев')

    def test_page_without_material(self, tmp_path):
        page = tmp_path / 'page.html'
        page.write_text('<html><body><p>Държавен вестник</p></body></html>', encoding='utf-8')
        with pytest.raises(FileLoadError, match='no State Gazette material'):
            DarzhavenVestnikParser().parse(str(page))


class TestStateGazetteClient:
    def test_metadata(self, bulgaria):
        assert StateGazetteClient.metadata(str(bulgaria / '103709.html')) == {
            'title': 'Закон за електронната идентификация', 'issue': '38', 'date_publication': '2016-05-20',
            'section': 'Официален раздел / НАРОДНО СЪБРАНИЕ', 'page': '2'}

    def test_iso_date(self):
        assert iso_date('20.5.2016') == '2016-05-20'

    def test_search(self, tmp_path):
        client = StateGazetteClient(download_dir=str(tmp_path))
        pages = [Mock(status_code=200, content=page.encode('utf-8')) for page in (INDEX, SEARCH_FORM, RESULTS)]
        with patch.object(client.session, 'request', side_effect=pages) as request:
            found = client.search(title='електронната идентификация', issue='38', year=2016)
        tab = request.call_args_list[1].kwargs['data']
        assert (tab['_idJsp2:_idcl'], tab['active_tab'], tab['javax.faces.ViewState']) == (
            '_idJsp2:_idJsp15', '3', 'state1')
        form = request.call_args_list[2].kwargs['data']
        assert request.call_args_list[2].args[1].endswith('/DVWeb/searchDV.faces')
        assert (form['search_form:_idJsp69'], form['search_form:_idJsp83'], form['search_form:from_date']) == (
            '38', 'електронната идентификация', '01.01.2016')
        assert found[0] == {'material': '103709', 'issue': '38', 'date_publication': '2016-05-20',
                            'title': 'Народно събрание Закон за електронната идентификация'}
        assert found[1]['material'] == '246270'

    def test_missing_material(self, tmp_path):
        client = StateGazetteClient(download_dir=str(tmp_path))
        with patch.object(client.session, 'request', return_value=Mock(status_code=200, content=b'<html></html>')):
            with pytest.raises(FileLoadError, match='no material 1'):
                client.download('1')


class TestBulgariaSource:
    def test_material_link(self, bulgaria, tmp_path):
        with patch.object(StateGazetteClient, 'download', return_value=str(bulgaria / '103709.html')) as download:
            doc = tulit.fetch('https://dv.parliament.bg/DVWeb/showMaterialDV.jsp?idMat=103709',
                              download_dir=str(tmp_path))
        download.assert_called_once_with('103709')
        meta = doc['meta']
        assert (meta['jurisdiction'], meta['version'], meta['language'], meta['version_date']) == (
            'BG', 'original', 'bul', '2016-05-20')
        assert (meta['gazette_issue'], meta['title']) == ('38', 'Закон за електронната идентификация')
        assert len(doc['articles']) == 56

    @pytest.mark.parametrize('identifier, search', [
        ('ДВ, бр. 38 от 2016 г., Закон за електронната идентификация',
         {'title': 'Закон за електронната идентификация', 'issue': '38', 'year': 2016}),
        ('Закон за електронната идентификация', {'title': 'Закон за електронната идентификация'}),
    ])
    def test_issue_and_title(self, bulgaria, tmp_path, identifier, search):
        results = [{'material': '103709', 'issue': '38', 'date_publication': '2016-05-20',
                    'title': 'Народно събрание Закон за електронната идентификация'},
                   {'material': '246270', 'issue': '95', 'date_publication': '2026-10-16',
                    'title': 'Народно събрание Закон за изменение и допълнение на Закона за електронната '
                             'идентификация'}]
        with patch.object(StateGazetteClient, 'search', return_value=results) as found, \
                patch.object(StateGazetteClient, 'download', return_value=str(bulgaria / '103709.html')) as download:
            tulit.fetch(identifier, jurisdiction='BG', download_dir=str(tmp_path))
        found.assert_called_once_with(**search)
        download.assert_called_once_with('103709')

    def test_ambiguous_title(self, tmp_path):
        results = [{'material': str(n), 'issue': str(n), 'date_publication': f'20{n}-01-01',
                    'title': 'Народно събрание Закон за изменение и допълнение на Закона за защита на личните данни'}
                   for n in (10, 11)]
        with patch.object(StateGazetteClient, 'search', return_value=results):
            with pytest.raises(FileLoadError, match='matches several acts'):
                tulit.fetch('Закон за изменение и допълнение на Закона за защита на личните данни',
                            jurisdiction='BG', download_dir=str(tmp_path))

    def test_no_consolidated_version(self, tmp_path):
        with pytest.raises(ValueError, match='does not publish the consolidated version'):
            tulit.fetch('103709', jurisdiction='BG', version='consolidated', download_dir=str(tmp_path))
