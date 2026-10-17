from unittest.mock import Mock, patch

import pytest

import tulit
from tulit.client.state.croatia import NarodneNovineClient
from tulit.parser.exceptions import FileLoadError
from tulit.parser.html.narodne_novine import NarodneNovineParser, amendment_action
from tulit.sources.hr import adoption_date, item_reference

RDF = '''<?xml version="1.0" encoding="utf-8" ?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:eli="http://data.europa.eu/eli/ontology#">
  <rdf:Description rdf:about="https://narodne-novine.nn.hr/eli/sluzbeni/2018/42/805">
    <eli:date_document rdf:datatype="http://www.w3.org/2001/XMLSchema#date">2018-04-27</eli:date_document>
    <eli:date_publication rdf:datatype="http://www.w3.org/2001/XMLSchema#date">2018-05-09</eli:date_publication>
    <eli:repeals rdf:resource="https://narodne-novine.nn.hr/eli/sluzbeni/2003/103/1364"/>
  </rdf:Description>
  <eli:LegalExpression rdf:about="https://narodne-novine.nn.hr/eli/sluzbeni/2018/42/805/hrv">
    <eli:title xml:lang="hrv">Zakon o provedbi Opće uredbe o zaštiti podataka</eli:title>
  </eli:LegalExpression>
</rdf:RDF>'''.encode('utf-8')


@pytest.fixture
def croatia(data_root):
    return data_root / 'sources' / 'member_states' / 'croatia'


@pytest.mark.parametrize('identifier', [
    '2018/42/805', 'https://narodne-novine.nn.hr/eli/sluzbeni/2018/42/805',
    'https://narodne-novine.nn.hr/clanci/sluzbeni/2018_05_42_805.html', 'NN 42/2018, 805', 'NN 42/18 (805)',
])
def test_item_reference(identifier):
    assert item_reference(identifier) == ('2018', '42', '805')


def test_item_reference_rejects_issue_only():
    with pytest.raises(ValueError):
        item_reference('NN 42/18')


@pytest.mark.parametrize('instruction, action', [
    ('Članak 5. mijenja se i glasi:', 'replace'),
    ('U članku 6. riječi: »a« zamjenjuju se riječima: »b«.', 'replace'),
    ('Iza članka 5. dodaje se članak 5.a koji glasi:', 'insert'),
    ('U članku 7. stavak 2. briše se.', 'delete'),
])
def test_amendment_action(instruction, action):
    assert amendment_action(instruction) == action


class TestNarodneNovineParser:
    def test_law(self, croatia):
        parser = NarodneNovineParser().parse(str(croatia / '2018_42_805.html'))
        assert parser.preface == 'Zakon o provedbi Opće uredbe o zaštiti podataka'
        assert parser.formula.startswith('Na temelju članka 89. Ustava Republike Hrvatske, donosim')
        chapter = parser.chapters[0]
        assert (chapter['eId'], chapter['type'], chapter['num']) == ('cpt_I', 'chapter', 'I. OPĆE ODREDBE')
        first = parser.articles[0]
        assert (first['eId'], first['num'], first['heading'], first['parent']) == (
            'art_1', 'Članak 1.', 'Predmet Zakona', 'cpt_I')
        assert [c['eId'] for c in first['children']] == ['par_1', 'par_2']
        assert parser.conclusions['signature'].startswith('Predsjednik Hrvatskoga sabora')

    def test_amending_law(self, croatia):
        parser = NarodneNovineParser().parse(str(croatia / '2018_118_2347.html'))
        second = parser.articles[1]['children'][0]
        assert second['amendment']['action'] == 'replace'
        assert second['amendment']['amended_act'].startswith('Zakonu o provedbi Uredbe (EU) 2015/757')
        # The article on entry into force amends nothing
        assert parser.articles[-1]['children'][0]['amendment'] is None

    def test_pdf_only_page(self, tmp_path):
        page = tmp_path / 'page.html'
        page.write_text('<html><head><title>Uredba</title></head><body><iframe src="x/pdf"></iframe></body></html>')
        with pytest.raises(FileLoadError, match='only as PDF'):
            NarodneNovineParser().parse(str(page))


def test_adoption_date(croatia):
    assert adoption_date(str(croatia / '2018_118_2347.html')) == '2018-12-14'


class TestCroatiaSource:
    def test_fetch(self, croatia, tmp_path):
        with patch.object(NarodneNovineClient, 'download', return_value=str(croatia / '2018_42_805.html')) as download, \
                patch.object(NarodneNovineClient, '_get', return_value=Mock(content=RDF)):
            doc = tulit.fetch('NN 42/2018, 805', jurisdiction='HR', download_dir=str(tmp_path))
        download.assert_called_once_with('2018', '42', '805')
        meta = doc['meta']
        assert (meta['jurisdiction'], meta['version'], meta['version_date']) == ('HR', 'original', '2018-04-27')
        assert meta['eli'] == 'https://narodne-novine.nn.hr/eli/sluzbeni/2018/42/805'
        assert meta['repeals'] == ['https://narodne-novine.nn.hr/eli/sluzbeni/2003/103/1364']

    def test_no_consolidated_version(self, tmp_path):
        with pytest.raises(ValueError, match='does not publish the consolidated version'):
            tulit.fetch('2018/42/805', jurisdiction='HR', version='consolidated', download_dir=str(tmp_path))


class TestNarodneNovineClient:
    def test_pdf_only_item(self, tmp_path):
        client = NarodneNovineClient(download_dir=str(tmp_path))
        page = Mock(status_code=200, url='https://narodne-novine.nn.hr/clanci/sluzbeni/x.html',
                    text='<html>Uredba</html>', content=b'<html><iframe/></html>')
        with patch.object(client.session, 'get', return_value=page):
            with pytest.raises(FileLoadError, match='only as PDF'):
                client.download('2026', '118', '1405')

    def test_missing_rdf_gives_no_metadata(self, tmp_path):
        client = NarodneNovineClient(download_dir=str(tmp_path))
        moved = Mock(status_code=200, url='https://narodne-novine.nn.hr/stranica404.aspx')
        with patch.object(client.session, 'get', return_value=moved):
            assert client.metadata('2011', '125', '2498') == {}
