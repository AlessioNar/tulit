from unittest.mock import Mock, patch

import pytest

import tulit
from tulit.client.state.lithuania import EseimasClient
from tulit.parser.exceptions import FileLoadError
from tulit.parser.html.etar import TARParser, amendment_action

SEARCH_FORM = '''<html><body>
<form id="searchCompositeComponent:contentForm" action="/portal/legalActSearch/lt?jfwid=x" method="post">
<input type="hidden" name="javax.faces.ViewState" value="state">
<input type="text" name="searchCompositeComponent:contentForm:searchParamPane:j_id_31:paramAdoptionNo" value="">
<input type="radio" name="option" value="ALL_WORDS" checked="checked"><input type="radio" name="option" value="ANY">
<select name="searchCompositeComponent:contentForm:searchParamPane:j_id_31:paramLanguage_input">
<option value="" selected="selected"></option><option value="clsDHSLanguage.1">Lietuvių</option></select>
<button type="submit" name="searchCompositeComponent:contentForm:searchParamPane:searchButton">Ieškoti</button>
</form></body></html>'''
SEARCH_RESULTS = '''<html><body><table>
<tr><td><a href="/portal/legalAct/lt/TAD/bc0837f27f9511e89188e16a6495e98c?positionInSearchResults=0&amp;s=1">
Lietuvos Respublikos asmens duomenų teisinės apsaugos įstatymo Nr. I-1374 pakeitimo įstatymas</a>
<a href="/portal/legalAct/lt/TAD/TAIS.29193/asr?positionInSearchResults=0">Galiojanti suvestinė redakcija</a></td></tr>
</table></body></html>'''
CARD = '''<html><body><table><tr><td>Rūšis:</td><td>Įstatymas</td><td>Priėmimo data:</td><td>2018-06-30</td></tr>
<tr><td>Registravimo duomenys:</td><td><span> 2018-07-11 Nr. 2018-11733 </span></td><td>Dokumento Nr.:</td>
<td>XIII-1426</td></tr><tr><td>Priėmė:</td><td>Lietuvos Respublikos Seimas $(function(){PrimeFaces.cw()});</td>
<td>Paskelbta:</td><td>TAR, 2018-07-11, Nr. 11733</td></tr></table>
<span>2018-07-11Paskelbta TAR</span> Įsigalioja 2018-07-16</body></html>'''
EDITIONS = '''<html><body>
<a href="/portal/legalAct/lt/TAD/TAIS.29193/asr">2026-06-30 -</a>
<a href="/portal/legalAct/lt/TAD/TAIS.29193/qgBNfUKDSx">Suvestinė nuo 2026-06-30</a>
<a href="/portal/legalAct/lt/TAD/TAIS.29193/qnMKeETDWs">Suvestinė nuo 2019-01-01</a>
<a href="/portal/legalAct/lt/TAD/TAIS.29193/VyZBDnEXYP">Suvestinė nuo 1998-04-01</a>
</body></html>'''


@pytest.fixture
def lithuania(data_root):
    return data_root / 'sources' / 'member_states' / 'lithuania'


@pytest.mark.parametrize('instruction, action', [
    ('Pakeisti 35 straipsnio 2 dalį ir ją išdėstyti taip:', 'replace'),
    ('Papildyti 1 straipsnį nauja 5 dalimi:', 'add'),
    ('Pripažinti netekusiu galios 9 straipsnį.', 'delete'),
    ('Šis įstatymas įsigalioja 2026 m. birželio 30 d.', None),
])
def test_amendment_action(instruction, action):
    assert amendment_action(instruction) == action


class TestTARParser:
    def test_original_law(self, lithuania):
        parser = TARParser().parse(str(lithuania / 'TAIS.29193.html'))
        assert parser.preface == ('LIETUVOS RESPUBLIKOS ASMENS DUOMENŲ TEISINĖS APSAUGOS ĮSTATYMAS '
                                  '1996 m. birželio 11 d. Nr. I-1374 Vilnius')
        assert [(c['eId'], c['num'], c['heading']) for c in parser.chapters][0] == (
            'sct_1', 'PIRMASIS SKIRSNIS', 'BENDROSIOS NUOSTATOS')
        first = parser.articles[0]
        assert (first['eId'], first['num'], first['heading'], first['parent']) == (
            'art_1', '1 straipsnis', 'Įstatymo reguliuojami santykiai ir įstatymo tikslas', 'sct_1')
        assert [c['eId'] for c in first['children']] == ['par_1', 'par_2']
        assert len(parser.articles) == 14
        assert parser.conclusions == {'conclusion_text': 'Skelbiu šį Lietuvos Respublikos Seimo priimtą įstatymą.',
                                      'signature': 'RESPUBLIKOS PREZIDENTAS ALGIRDAS BRAZAUSKAS'}

    def test_consolidated_version(self, lithuania):
        parser = TARParser().parse(str(lithuania / 'TAIS.29193_qgBNfUKDSx.html'))
        assert len(parser.chapters) == 9 and len(parser.articles) == 40
        # An article inserted later, with its superscript number
        inserted = next(a for a in parser.articles if a['num'] == '7¹ straipsnis')
        assert inserted['eId'] == 'art_7-1'
        # The editorial notes of the consolidated version are left out
        texts = ' '.join(c['text'] for a in parser.articles for c in a['children'])
        assert 'pakeitimai:' not in texts and 'paskelbta TAR' not in texts
        assert 'Suvestinė redakcija' not in (parser.preface or '')
        annex = parser.annexes[0]
        assert annex['num'] == 'Lietuvos Respublikos asmens duomenų teisinės apsaugos įstatymo priedas'
        assert annex['heading'] == 'ĮGYVENDINAMI EUROPOS SĄJUNGOS TEISĖS AKTAI'

    def test_amending_law(self, lithuania):
        parser = TARParser().parse(str(lithuania / 'e541a262128c11ef8e4be9fad87afa59.html'))
        first = parser.articles[0]
        assert first['heading'] == '1 straipsnio pakeitimas'
        amendment = first['children'][0]['amendment']
        assert amendment['action'] == 'replace'
        assert amendment['amended_act'] == 'LIETUVOS RESPUBLIKOS ASMENS DUOMENŲ TEISINĖS APSAUGOS ĮSTATYMO NR. I-1374'
        assert first['children'][1]['amendment']['action'] == 'add'
        # Quoted text stays in the amending article, with the quoted article in it
        added = parser.articles[3]['children'][0]
        assert added['amendment']['action'] == 'add'
        assert '7¹ straipsnis. Kitų tiesiogiai taikomų' in added['text']
        assert parser.articles[-1]['heading'] == 'Įstatymo įsigaliojimas, įgyvendinimas ir taikymas'

    def test_short_amending_law(self, lithuania):
        parser = TARParser().parse(str(lithuania / '3488a5e24e8a11f18091f24c9e0d719a.html'))
        assert [a['num'] for a in parser.articles] == ['1 straipsnis', '2 straipsnis']
        amendment = parser.articles[0]['children'][0]['amendment']
        assert amendment['instruction'] == 'Pakeisti 35 straipsnio 2 dalį ir ją išdėstyti taip:'
        assert amendment['quoted'][0]['text'].startswith('2. Priežiūros institucijos sprendimas')

    def test_order_with_approved_rules(self, lithuania):
        parser = TARParser().parse(str(lithuania / '34647680840811f19be4e4d226bee2f8.html'))
        assert parser.recitals[0]['text'].startswith('Vadovaudamasi Lietuvos Respublikos vietos savivaldos')
        assert [a['num'] for a in parser.articles] == ['1.']
        assert parser.conclusions['conclusion_text'] == 'Administracijos direktorė Lina Leinartienė'
        rules = parser.annexes[0]
        assert rules['num'].startswith('PATVIRTINTA Telšių rajono savivaldybės administracijos direktoriaus')
        assert rules['heading'] == 'KIBERNETINIO SAUGUMO REIKALAVIMŲ VEIKSMINGUMO VERTINIMO TVARKOS APRAŠAS'
        assert [a['num'] for a in parser.annexes[1:]] == ['1 priedas', '2 priedas']

    def test_government_resolution(self, lithuania):
        parser = TARParser().parse(str(lithuania / '3c00f5a0b24811efbb3fe9794b4a33e2.html'))
        assert parser.formula == 'Lietuvos Respublikos Vyriausybė nutaria:'
        assert [a['num'] for a in parser.articles] == ['1.', '2.']
        point = parser.articles[0]['children']
        assert point[0]['amendment']['action'] == 'replace'
        assert point[1]['eId'] == 'par_1-1'
        assert parser.conclusions['conclusion_text'].startswith('Laikinai einanti Ministro Pirmininko pareigas')

    @staticmethod
    def _act(tmp_path, *lines):
        """An act from its lines; a line starting with '^' is centred."""
        paragraphs = ''.join(
            f'<p class="MsoNormal" style="text-align:center">{line[1:]}</p>' if line.startswith('^')
            else f'<p class="MsoNormal">{line}</p>' for line in lines)
        page = tmp_path / 'act.html'
        page.write_text(f'<html><body>{paragraphs}</body></html>', encoding='utf-8')
        return TARParser().parse(str(page))

    def test_code_after_approval_law(self, tmp_path):
        parser = self._act(
            tmp_path, '^LIETUVOS RESPUBLIKOS DARBO KODEKSO PATVIRTINIMO ĮSTATYMAS',
            '^2016 m. rugsėjo 14 d. Nr. XII-2603',
            '1 straipsnis. Lietuvos Respublikos darbo kodekso patvirtinimas',
            'Patvirtinti Lietuvos Respublikos darbo kodeksą (pridedama).',
            'Skelbiu šį Lietuvos Respublikos Seimo priimtą įstatymą.', 'Respublikos Prezidentė Dalia Grybauskaitė',
            'PATVIRTINTA', '2016 m. rugsėjo 14 d.', 'įstatymu Nr. XII-2603',
            '^LIETUVOS RESPUBLIKOS DARBO KODEKSAS', '^I dalis',
            '^<span style="text-transform: uppercase">Bendrosios nuostatos</span>',
            '1 straipsnis. Kodekso paskirtis',
            '1. Pakeisti būtinąsias darbo sutarties sąlygas galima tik šalių susitarimu.',
            '4 skirsnis. Neteko galios nuo 2017-07-01',
            '^Pirmasis SKIRSNIS', '^Darbo sutartis',
            '2 straipsnis. Darbo sutartis', 'Darbo sutartis sudaroma raštu.')
        # The code keeps its own eIds; the approval law's article comes first
        assert [(a['eId'], a['num']) for a in parser.articles] == [
            ('art_1_2', '1 straipsnis'), ('art_1', '1 straipsnis'), ('art_2', '2 straipsnis')]
        assert [(c['eId'], c['num'], c['heading'], c['parent']) for c in parser.chapters] == [
            ('prt_I', 'I dalis', 'BENDROSIOS NUOSTATOS', None),
            ('sct_1', 'Pirmasis SKIRSNIS', 'Darbo sutartis', 'prt_I')]
        assert parser.conclusions['signature'] == 'Respublikos Prezidentė Dalia Grybauskaitė'
        # Not an amending act: a provision using an amending verb holds no amendment; a repealed section is left out
        assert [c['text'] for c in parser.articles[1]['children']] == [
            '1. Pakeisti būtinąsias darbo sutarties sąlygas galima tik šalių susitarimu.']
        assert parser.articles[1]['children'][0]['amendment'] is None

    def test_constitution(self, tmp_path):
        parser = self._act(
            tmp_path, '^LIETUVOS RESPUBLIKOS', '^K O N S T I T U C I J A', 'LIETUVIŲ TAUTA',
            '^I SKIRSNIS', '^LIETUVOS VALSTYBĖ', '1 straipsnis', 'Lietuvos valstybė yra nepriklausoma.',
            '^VI SKIRSNIS', '^RESPUBLIKOS PREZIDENTAS',
            '77 straipsnis', 'Respublikos Prezidentas yra valstybės vadovas.',
            'Respublikos Prezidentas negali skelbti pirmalaikių Seimo rinkimų.',
            'LIETUVOS RESPUBLIKOS', 'AUKŠČIAUSIOSIOS TARYBOS', 'PIRMININKAS VYTAUTAS LANDSBERGIS')
        assert parser.preface == 'LIETUVOS RESPUBLIKOS KONSTITUCIJA'
        assert [(a['eId'], a['heading'], len(a['children'])) for a in parser.articles] == [
            ('art_1', None, 1), ('art_77', None, 2)]
        assert parser.chapters[1]['heading'] == 'RESPUBLIKOS PREZIDENTAS'
        assert parser.conclusions == {'conclusion_text': 'LIETUVOS RESPUBLIKOS',
                                      'signature': 'AUKŠČIAUSIOSIOS TARYBOS PIRMININKAS VYTAUTAS LANDSBERGIS'}

    def test_letter_spaced_word(self, tmp_path):
        parser = self._act(tmp_path, '^ĮSAKYMAS', '1. T v i r t i n u aprašą (pridedama).')
        assert parser.articles[0]['children'][0]['text'] == 'Tvirtinu aprašą (pridedama).'

    def test_page_without_text(self, tmp_path):
        page = tmp_path / 'page.html'
        page.write_text('<html><body><div></div></body></html>')
        with pytest.raises(FileLoadError, match='no act text'):
            TARParser().parse(str(page))


class TestEseimasClient:
    def test_search(self, tmp_path):
        client = EseimasClient(download_dir=str(tmp_path))
        with patch.object(client.session, 'request', side_effect=[
                Mock(status_code=200, content=SEARCH_FORM.encode('utf-8')),
                Mock(status_code=200, content=SEARCH_RESULTS.encode('utf-8'))]) as request:
            found = client.find('number', 'XIII-1426')
        posted = request.call_args_list[1].kwargs['data']
        assert posted['searchCompositeComponent:contentForm:searchParamPane:j_id_31:paramAdoptionNo'] == 'XIII-1426'
        # In Lithuanian, not the translations
        assert posted['searchCompositeComponent:contentForm:searchParamPane:j_id_31:paramLanguage_input'] == \
            'clsDHSLanguage.1'
        assert posted['javax.faces.ViewState'] == 'state' and posted['option'] == 'ALL_WORDS'
        assert found == {'id': 'bc0837f27f9511e89188e16a6495e98c',
                         'title': 'Lietuvos Respublikos asmens duomenų teisinės apsaugos įstatymo Nr. I-1374 '
                                  'pakeitimo įstatymas', 'consolidated': 'TAIS.29193'}

    def test_metadata(self, tmp_path):
        client = EseimasClient(download_dir=str(tmp_path))
        with patch.object(client.session, 'request', return_value=Mock(status_code=200, content=CARD.encode('utf-8'))):
            meta = client.metadata('bc0837f27f9511e89188e16a6495e98c')
        assert meta == {'type': 'Įstatymas', 'date_document': '2018-06-30', 'number': 'XIII-1426',
                        'issuer': 'Lietuvos Respublikos Seimas', 'publication': 'TAR, 2018-07-11, Nr. 11733',
                        'tar': '2018-11733', 'date_in_force': '2018-07-16'}

    def test_versions(self, tmp_path):
        client = EseimasClient(download_dir=str(tmp_path))
        with patch.object(client.session, 'request',
                          return_value=Mock(status_code=200, content=EDITIONS.encode('utf-8'))):
            assert client.versions('TAIS.29193') == [('1998-04-01', 'VyZBDnEXYP'), ('2019-01-01', 'qnMKeETDWs'),
                                                     ('2026-06-30', 'qgBNfUKDSx')]

    def test_missing_document(self, tmp_path):
        client = EseimasClient(download_dir=str(tmp_path))
        with patch.object(client.session, 'request', return_value=Mock(status_code=404, content=b'')):
            with pytest.raises(FileLoadError, match='no document'):
                client.download('TAIS.1')


VERSIONS = [('1998-04-01', 'VyZBDnEXYP'), ('2019-01-01', 'qnMKeETDWs'), ('2026-06-30', 'qgBNfUKDSx')]
META = {'type': 'Įstatymas', 'date_document': '1996-06-11', 'number': 'I-1374',
        'publication': 'Valstybės žinios, 1996-07-03, Nr. 63-1479', 'date_in_force': '1996-07-03'}


class TestLithuaniaSource:
    def test_original_by_number(self, lithuania, tmp_path):
        with patch.object(EseimasClient, 'find', return_value={'id': 'TAIS.29193'}) as find, \
                patch.object(EseimasClient, 'metadata', return_value=META), \
                patch.object(EseimasClient, 'download', return_value=str(lithuania / 'TAIS.29193.html')):
            doc = tulit.fetch('I-1374', jurisdiction='LT', download_dir=str(tmp_path))
        find.assert_called_once_with('number', 'I-1374')
        meta = doc['meta']
        assert (meta['jurisdiction'], meta['version'], meta['language'], meta['version_date']) == (
            'LT', 'original', 'lit', '1996-06-11')
        assert (meta['date_publication'], meta['source']) == (
            '1996-07-03', 'https://e-seimas.lrs.lt/portal/legalAct/lt/TAD/TAIS.29193')
        assert len(doc['articles']) == 14

    def test_tar_code(self, lithuania, tmp_path):
        with patch.object(EseimasClient, 'find', return_value={'id': 'e541a262128c11ef8e4be9fad87afa59'}) as find, \
                patch.object(EseimasClient, 'metadata', return_value={}), \
                patch.object(EseimasClient, 'download',
                             return_value=str(lithuania / 'e541a262128c11ef8e4be9fad87afa59.html')):
            tulit.fetch('2024-09142', jurisdiction='LT', download_dir=str(tmp_path))
        find.assert_called_once_with('registration', '2024-09142')

    @pytest.mark.parametrize('date, version, start', [
        (None, 'qgBNfUKDSx', '2026-06-30'), ('2020-05-01', 'qnMKeETDWs', '2019-01-01')])
    def test_consolidated(self, lithuania, tmp_path, date, version, start):
        with patch.object(EseimasClient, 'metadata', return_value=META), \
                patch.object(EseimasClient, 'versions', return_value=VERSIONS), \
                patch.object(EseimasClient, 'download_version',
                             return_value=str(lithuania / 'TAIS.29193_qgBNfUKDSx.html')) as download:
            doc = tulit.fetch('TAIS.29193', jurisdiction='LT', version='consolidated', date=date,
                              download_dir=str(tmp_path))
        download.assert_called_once_with('TAIS.29193', version)
        assert (doc['meta']['version'], doc['meta']['version_date']) == ('consolidated', start)
        assert doc['meta']['source'].endswith(f'/TAIS.29193/{version}')

    def test_version_link(self, lithuania, tmp_path):
        with patch.object(EseimasClient, 'metadata', return_value=META), \
                patch.object(EseimasClient, 'versions', return_value=VERSIONS), \
                patch.object(EseimasClient, 'download_version',
                             return_value=str(lithuania / 'TAIS.29193_qgBNfUKDSx.html')) as download:
            doc = tulit.fetch('https://e-seimas.lrs.lt/portal/legalAct/lt/TAD/TAIS.29193/qnMKeETDWs',
                              download_dir=str(tmp_path))
        download.assert_called_once_with('TAIS.29193', 'qnMKeETDWs')
        assert (doc['meta']['jurisdiction'], doc['meta']['version'], doc['meta']['version_date']) == (
            'LT', 'consolidated', '2019-01-01')

    def test_date_before_first_version(self, tmp_path):
        with patch.object(EseimasClient, 'metadata', return_value=META), \
                patch.object(EseimasClient, 'versions', return_value=VERSIONS):
            with pytest.raises(FileLoadError, match='applies from 1998-04-01'):
                tulit.fetch('TAIS.29193', jurisdiction='LT', version='consolidated', date='1997-01-01',
                            download_dir=str(tmp_path))

    def test_amending_act_has_no_consolidated_version(self, tmp_path):
        with patch.object(EseimasClient, 'metadata', return_value={}), \
                patch.object(EseimasClient, 'versions', return_value=[]):
            with pytest.raises(FileLoadError, match='consolidated into the act it amends'):
                tulit.fetch('bc0837f27f9511e89188e16a6495e98c', jurisdiction='LT', version='consolidated',
                            download_dir=str(tmp_path))

    def test_bad_identifier(self, tmp_path):
        with pytest.raises(ValueError, match='not a Lithuanian act identifier'):
            tulit.fetch('data protection law', jurisdiction='LT', download_dir=str(tmp_path))
