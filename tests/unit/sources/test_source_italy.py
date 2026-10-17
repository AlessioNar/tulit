from unittest.mock import Mock, patch

import pytest

import tulit
from tulit.client.state.italy import NormattivaAKNClient
from tulit.parser.exceptions import FileLoadError
from tulit.parser.xml.akomantoso.normattiva import NormattivaAKNParser, amendment_action
from tulit.sources.it import act_reference

ACT_PAGE = ('<html><head><title>DECRETO LEGISLATIVO 10 agosto 2018, n. 101 - Normattiva</title></head><body>'
            '<a href="/do/atto/caricaAKN?dataGU=20180904&amp;codiceRedaz=18G00129&amp;dataVigenza=20261017">AKN</a>'
            '</body></html>')


@pytest.fixture
def italy(data_root):
    return data_root / 'sources' / 'member_states' / 'italy'


@pytest.mark.parametrize('identifier, expected', [
    ('decreto legislativo 10 agosto 2018, n. 101', {'urn': 'urn:nir:stato:decreto.legislativo:2018-08-10;101'}),
    ('D.Lgs. 101/2018', {'urn': 'urn:nir:stato:decreto.legislativo:2018;101'}),
    ('d.lgs. n. 101/2018', {'urn': 'urn:nir:stato:decreto.legislativo:2018;101'}),
    ('legge 27 dicembre 2019, n. 160', {'urn': 'urn:nir:stato:legge:2019-12-27;160'}),
    ('L. 160/2019', {'urn': 'urn:nir:stato:legge:2019;160'}),
    ('decreto-legge 17 marzo 2020, n. 18', {'urn': 'urn:nir:stato:decreto.legge:2020-03-17;18'}),
    ('D.P.R. 445/2000', {'urn': 'urn:nir:stato:decreto.del.presidente.della.repubblica:2000;445'}),
    ('Costituzione', {'urn': 'urn:nir:stato:costituzione:1947-12-27'}),
    ('urn:nir:stato:legge:1941-04-22;633', {'urn': 'urn:nir:stato:legge:1941-04-22;633'}),
    ('https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:legge:2019;160',
     {'urn': 'urn:nir:stato:legge:2019;160'}),
    ('https://www.gazzettaufficiale.it/eli/id/2018/09/04/18G00129/sg', {'date': '2018-09-04', 'code': '18G00129'}),
    ('https://www.normattiva.it/eli/id/2018/09/04/18G00129/CONSOLIDATED', {'date': '2018-09-04', 'code': '18G00129'}),
    ('2018-09-04/18G00129', {'date': '2018-09-04', 'code': '18G00129'}),
])
def test_act_reference(identifier, expected):
    assert act_reference(identifier) == expected


@pytest.mark.parametrize('identifier', ['codice privacy', 'decreto legislativo 10 agostino 2018, n. 101'])
def test_act_reference_rejects(identifier):
    with pytest.raises(ValueError):
        act_reference(identifier)


@pytest.mark.parametrize('instruction, action', [
    ("All'articolo 2 sono aggiunte, in fine, le seguenti parole:", 'add'),
    ("l'articolo 1 e' sostituito dal seguente:", 'replace'),
    ("prima dell'articolo 1 e' inserito il seguente Capo:", 'insert'),
    ("L'articolo 13 e' abrogato.", 'delete'),
    ('alla legge 11 gennaio 2018, n. 5, sono apportate le seguenti modificazioni:', 'amend'),
    ('La presente legge entra in vigore il giorno successivo a quello della sua pubblicazione.', None),
])
def test_amendment_action(instruction, action):
    assert amendment_action(instruction) == action


class TestNormattivaAKNParser:
    def test_decree(self, italy):
        parser = NormattivaAKNParser().parse(str(italy / 'normattiva' / '18G00129_2018-09-04.xml'))
        assert parser.preface.startswith('DECRETO LEGISLATIVO 10 agosto 2018, n. 101 - Disposizioni per '
                                         "l'adeguamento della normativa nazionale")
        assert not parser.preface.endswith('(18G00129)')
        assert parser.formula == 'IL PRESIDENTE DELLA REPUBBLICA'
        assert parser.citations[0]['text'] == 'Visti gli articoli 76 e 87 della Costituzione;'
        # Paragraphs among the citations are kept in order
        assert parser.citations[-1]['text'].startswith('Sulla proposta del Presidente del Consiglio')
        assert parser.preamble_final == 'E M A N A il seguente decreto legislativo:'
        assert [(c['eId'], c['num']) for c in parser.chapters] == [('cpt_I', 'Capo I'), ('cpt_V', 'Capo V'),
                                                                   ('cpt_VI', 'Capo VI')]
        first = parser.articles[0]
        assert (first['eId'], first['num'], first['parent']) == ('art_1', 'Art. 1.', 'cpt_I')
        # The editorial notes are left out
        texts = ' '.join(c['text'] for a in parser.articles for c in a['children'])
        assert 'N O T E' not in texts and "Note all'art." not in texts
        amendment = first['children'][0]['amendment']
        assert amendment['action'] == 'add'
        assert amendment['amended_act'] == 'decreto legislativo 30 giugno 2003, n. 196'
        assert amendment['quoted'][0]['text'] == 'dati personali'
        assert parser.conclusions['conclusion_text'].endswith("Dato a Roma, addi' 10 agosto 2018")
        assert parser.conclusions['signature'].startswith('MATTARELLA')

    def test_law_with_attachments(self, italy):
        parser = NormattivaAKNParser().parse(
            str(italy / 'gazzetta_ufficiale' / '20240527_24G00083_VIGENZA_20240902.xml'))
        assert parser.preface.startswith('LEGGE 14 maggio 2024, n. 66 - Ratifica ed esecuzione')
        assert parser.preamble_final == 'Promulga la seguente legge:'
        assert [a['eId'] for a in parser.articles] == ['art_1', 'art_2', 'art_3', 'art_4']
        # The ratified Agreement, article by article
        assert len(parser.annexes) == 21
        assert parser.annexes[0]['num'] == 'Accordo-art. 1'
        assert parser.annexes[0]['children'][0]['text'].startswith('ACCORDO IN MATERIA DI COPRODUZIONE')

    def test_code_with_titles(self, italy):
        parser = NormattivaAKNParser().parse(
            str(italy / 'gazzetta_ufficiale' / '19410716_041U0633_VIGENZA_20241222.xml'))
        assert parser.preface == ("LEGGE 22 aprile 1941, n. 633 - Protezione del diritto d'autore e di altri "
                                  "diritti connessi al suo esercizio.")
        assert parser.chapters[0]['num'] == 'TITOLO I'
        assert len(parser.articles) > 300


class TestNormattivaAKNClient:
    def test_resolve(self, tmp_path):
        client = NormattivaAKNClient(download_dir=str(tmp_path))
        page = Mock(status_code=200, text=ACT_PAGE)
        with patch.object(client.session, 'get', return_value=page) as get:
            found = client.resolve('urn:nir:stato:decreto.legislativo:2018;101')
        assert get.call_args.args[0] == ('https://www.normattiva.it/uri-res/N2Ls?'
                                         'urn:nir:stato:decreto.legislativo:2018;101')
        assert found == {'date': '2018-09-04', 'code': '18G00129',
                         'title': 'DECRETO LEGISLATIVO 10 agosto 2018, n. 101'}
        # Normattiva only answers browser-like clients
        assert client.session.headers['User-Agent'].startswith('Mozilla/5.0')

    def test_unknown_act(self, tmp_path):
        client = NormattivaAKNClient(download_dir=str(tmp_path))
        error = Mock(status_code=200, text='<html><title>Normattiva - Errore</title></html>')
        with patch.object(client.session, 'get', return_value=error):
            with pytest.raises(FileLoadError, match='no act'):
                client.resolve('urn:nir:stato:decreto.legislativo:2018;999999')

    def test_download(self, italy, tmp_path):
        client = NormattivaAKNClient(download_dir=str(tmp_path))
        export = Mock(status_code=200, content=(italy / 'normattiva' / '18G00129_2018-09-04.xml').read_bytes())
        with patch.object(client.session, 'get', return_value=export) as get:
            path = client.download('2018-09-04', '18G00129', '2020-01-01')
        assert get.call_args.args[0] == ('https://www.normattiva.it/do/atto/caricaAKN?dataGU=20180904'
                                         '&codiceRedaz=18G00129&dataVigenza=20200101')
        assert path.endswith('18G00129_2020-01-01.xml')

    def test_export_without_session(self, tmp_path):
        client = NormattivaAKNClient(download_dir=str(tmp_path))
        error = Mock(status_code=200, content=b'<!DOCTYPE html><html>Errore nel caricamento</html>')
        with patch.object(client.session, 'get', return_value=error):
            with pytest.raises(FileLoadError, match='did not export'):
                client.download('2018-09-04', '18G00129')


class TestItalySource:
    def test_original(self, italy, tmp_path):
        fixture = str(italy / 'normattiva' / '18G00129_2018-09-04.xml')
        with patch.object(NormattivaAKNClient, 'resolve',
                          return_value={'date': '2018-09-04', 'code': '18G00129', 'title': None}), \
                patch.object(NormattivaAKNClient, 'download', return_value=fixture) as download:
            doc = tulit.fetch('D.Lgs. 101/2018', jurisdiction='IT', download_dir=str(tmp_path))
        download.assert_called_once_with('2018-09-04', '18G00129', '2018-09-04')
        meta = doc['meta']
        assert (meta['jurisdiction'], meta['version'], meta['language'], meta['version_date']) == (
            'IT', 'original', 'ita', '2018-09-04')
        assert meta['eli'] == 'https://www.gazzettaufficiale.it/eli/id/2018/09/04/18G00129/sg'
        assert meta['source'] == 'https://www.normattiva.it/eli/id/2018/09/04/18G00129/ORIGINAL'
        assert len(doc['articles']) == 12

    def test_consolidated_from_gazzetta_link(self, italy, tmp_path):
        fixture = str(italy / 'normattiva' / '18G00129_2018-09-04.xml')
        with patch.object(NormattivaAKNClient, 'open_act') as open_act, \
                patch.object(NormattivaAKNClient, 'download', return_value=fixture) as download:
            doc = tulit.fetch('https://www.gazzettaufficiale.it/eli/id/2018/09/04/18G00129/sg',
                              version='consolidated', date='2020-01-01', download_dir=str(tmp_path))
        open_act.assert_called_once_with('2018-09-04', '18G00129')
        download.assert_called_once_with('2018-09-04', '18G00129', '2020-01-01')
        # The date the exported text is in force from
        assert doc['meta']['version_date'] == '2018-09-19'
        assert doc['meta']['jurisdiction'] == 'IT'

    def test_date_before_publication(self, tmp_path):
        with patch.object(NormattivaAKNClient, 'open_act'):
            with pytest.raises(FileLoadError, match='published on 2018-09-04'):
                tulit.fetch('2018-09-04/18G00129', jurisdiction='IT', version='consolidated', date='2018-01-01',
                            download_dir=str(tmp_path))
