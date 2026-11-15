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


PAGE = '<html><head><title>Akt</title></head><body><div class="sl-content">%s</div></body></html>'


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

    def test_labelled_divisions_annexes_and_continued_sentences(self, tmp_path):
        # Trimmed from the Zakon o obveznim odnosima (NN 35/2005) and a pravilnik with annexes
        page = tmp_path / 'item.html'
        page.write_text(PAGE % '''
            <p class="brojdesno2">707</p>
            <p class="nas-129licht">Dio prvi</p><p class="nas-129fett">OPĆI DIO</p>
            <p class="nas-119licht">Glava I.</p><p class="nas-119fett">OSNOVNA NAČELA</p>
            <p class="nas-98fett">Cilj i sadržaj zakona</p><p class="Clanak">Članak 1.</p>
            <p class="T-98-2">Ovim se Zakonom uređuju osnove obveznih odnosa.</p>
            <p class="nas-119licht">Odjeljak 1.</p><p class="nas-119licht">NOVČANE OBVEZE</p>
            <p class="nas-98fett">I. FAKULTATIVNE OBVEZE</p><p class="nas-98fett">Pojam</p>
            <p class="Clanak">Članak 2.</p>
            <p class="T-98-2">(1) Tko:</p><p class="T-98-2">1. ne plati,</p>
            <p class="T-98-2">kaznit će se novčanom kaznom.</p>
            <p class="Klasa2">Zagreb, 25. veljače 2005.</p><p class="TB-PA-2">Predsjednik, v. r.</p>
            <p class="prilog pcenter">PRILOG 1.</p><p class="T-9-8-sredina pcenter">Program izobrazbe</p>
            <p class="T-9-8">Ljudski faktor</p>''', encoding='utf-8')
        parser = NarodneNovineParser().parse(str(page))
        assert [(c['eId'], c['num'], c['heading'], c['parent']) for c in parser.chapters] == [
            ('prt_1', 'Dio prvi', 'OPĆI DIO', None),
            ('cpt_I', 'Glava I.', 'OSNOVNA NAČELA', 'prt_1'),
            ('sct_1', 'Odjeljak 1.', 'NOVČANE OBVEZE', 'cpt_I'),
            ('div_I', 'I. FAKULTATIVNE OBVEZE', None, 'sct_1')]
        first, second = parser.articles
        assert (first['heading'], first['parent'], second['heading'], second['parent']) == (
            'Cilj i sadržaj zakona', 'cpt_I', 'Pojam', 'div_I')
        assert [c['text'] for c in second['children']] == ['(1) Tko: 1. ne plati, kaznit će se novčanom kaznom.']
        assert parser.annexes == [{'eId': 'anx_1', 'num': 'PRILOG 1.', 'heading': 'Program izobrazbe',
                                   'children': [{'eId': 'unp_1', 'text': 'Ljudski faktor', 'amendment': None}]}]
        assert parser.formula is None and parser.citations == []

    def test_scanned_constitution(self, tmp_path):
        # Trimmed from the Ustav of 1990 (NN 56/1990): no typographic classes, '1' read as 'I'
        page = tmp_path / 'item.html'
        page.write_text(PAGE % '''
            <p class="MsoNormal">1092<o:p></o:p></p>
            <p class="MsoNormal">I. IZVORIŠNE OSNOVE</p><p class="MsoNormal">Izražavajući samobitnost.</p>
            <p class="MsoNormal">II. TEMELJNE ODREDBE</p><p class="MsoNormal">Članak 1I.</p>
            <p class="MsoNormal">Republika Hrvatska jedinstvena je država.</p>
            <p class="MsoNormal">2. Udruživanje i odcjepljenje</p><p class="MsoNormal">Članak I35.</p>
            <p class="MsoNormal">Pravo da pokrenu postupak udruživanja.</p>''', encoding='utf-8')
        parser = NarodneNovineParser().parse(str(page))
        assert [(c['eId'], c['parent']) for c in parser.chapters] == [
            ('cpt_I', None), ('cpt_II', None), ('sct_2', 'cpt_II')]
        assert [(a['eId'], a['num'], a['parent']) for a in parser.articles] == [
            ('art_11', 'Članak 1I.', 'cpt_II'), ('art_135', 'Članak I35.', 'sct_2')]
        # The text before the first article is the preamble
        assert parser.recitals == [{'eId': 'rct_1', 'text': 'Izražavajući samobitnost.'}]

    def test_amendment_instruction_keeps_gazette_citation(self, tmp_path):
        page = tmp_path / 'item.html'
        page.write_text(PAGE % '''
            <p class="Clanak">Članak 381.</p>
            <p class="T-9-8">(2) U Zakonu o energiji (»Narodne novine«, br. 68/01.) u članku 33. riječi:
            »bez mjernih uređaja« brišu se.</p>''', encoding='utf-8')
        amendment = NarodneNovineParser().parse(str(page)).articles[0]['children'][0]['amendment']
        assert amendment['action'] == 'delete'
        assert amendment['instruction'] == ('(2) U Zakonu o energiji (»Narodne novine«, br. 68/01.) '
                                            'u članku 33. riječi:')

    def test_quoted_article_stays_in_the_amendment(self, tmp_path):
        # Trimmed from a pravilnik amending another (NN 30/2025, 310)
        page = tmp_path / 'item.html'
        page.write_text(PAGE % '''
            <p class="Clanak">Članak 2.</p>
            <p class="T-9-8">Iza članka 3. dodaje se novi članak 3.a s naslovom iznad njega koji glasi:</p>
            <p class="T-10-9-kurz-S">»Obustava ribolova</p><p class="Clanak--">Članak 3.a</p>
            <p class="T-9-8">(1) Ministarstvo obustavlja ribolov.</p>
            <p class="T-9-8">(2) Objavu objavljuje na mrežnoj stranici.«.</p>
            <p class="Clanak">Članak 3.</p><p class="T-9-8">U članku 5. stavak 2. briše se.</p>''', encoding='utf-8')
        parser = NarodneNovineParser().parse(str(page))
        assert [a['eId'] for a in parser.articles] == ['art_2', 'art_3']
        amendment = parser.articles[0]['children'][0]['amendment']
        assert amendment['action'] == 'insert'
        assert [q['text'] for q in amendment['quoted']] == [
            'Obustava ribolova', 'Članak 3.a', '(1) Ministarstvo obustavlja ribolov.',
            '(2) Objavu objavljuje na mrežnoj stranici.']

    def test_pdf_only_page(self, tmp_path):
        page = tmp_path / 'page.html'
        page.write_text('<html><head><title>Uredba</title></head><body><iframe src="x/pdf"></iframe></body></html>')
        with pytest.raises(FileLoadError, match='only as PDF'):
            NarodneNovineParser().parse(str(page))


def test_adoption_date(croatia):
    assert adoption_date(str(croatia / '2018_118_2347.html')) == '2018-12-14'


def test_adoption_date_needs_a_signature(tmp_path):
    # The Ustav of 1990 is not signed in its own item; its last date is a historical one
    page = tmp_path / 'item.html'
    page.write_text(PAGE % '<p>u odluci od 3. listopada 1929. godine</p>', encoding='utf-8')
    assert adoption_date(str(page)) is None


class TestCroatiaSource:
    def test_fetch(self, croatia, tmp_path):
        page = str(croatia / '2018_42_805.html')
        with patch.object(NarodneNovineClient, 'download', return_value=page) as download, \
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
