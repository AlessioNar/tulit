from unittest.mock import Mock, patch

import pytest

import tulit
from tulit.client.state.poland import SejmELIClient
from tulit.parser.exceptions import FileLoadError
from tulit.parser.html.sejm import SejmELIParser, amendment_action
from tulit.sources.pl import act_eli

ACT = {'ELI': 'DU/2018/1000', 'displayAddress': 'Dz.U. 2018 poz. 1000', 'announcementDate': '2018-05-10',
       'promulgation': '2018-05-24', 'inForce': 'IN_FORCE', 'textHTML': True,
       'references': {'Inf. o tekście jednolitym': [{'id': 'DU/2019/1781'}, {'id': 'DU/2026/9'}],
                      'Akty zmieniające': [{'id': 'DU/2019/730'}]}}
CONSOLIDATED = {'ELI': 'DU/2019/1781', 'displayAddress': 'Dz.U. 2019 poz. 1781', 'announcementDate': '2019-08-30',
                'promulgation': '2019-09-19', 'inForce': 'IN_FORCE', 'textHTML': True,
                'references': {'Tekst jednolity dla aktu': [{'id': 'DU/2018/1000'}]}}
# A newer consolidated text not yet available as HTML
LATEST = {'ELI': 'DU/2026/9', 'displayAddress': 'Dz.U. 2026 poz. 9', 'announcementDate': '2025-12-20',
          'promulgation': '2026-01-05', 'textHTML': False,
          'references': {'Tekst jednolity dla aktu': [{'id': 'DU/2018/1000'}]}}
ACTS = {'DU/2018/1000': ACT, 'DU/2019/1781': CONSOLIDATED, 'DU/2026/9': LATEST}


@pytest.fixture
def poland(data_root):
    return data_root / 'sources' / 'member_states' / 'poland'


@pytest.mark.parametrize('identifier', [
    'DU/2018/1000', 'Dz.U. 2018 poz. 1000', 'Dz. U. z 2018 r. poz. 1000', 'WDU20180001000',
    'https://eli.gov.pl/eli/DU/2018/1000/ogl', 'https://api.sejm.gov.pl/eli/acts/DU/2018/1000/text.html',
    'https://isap.sejm.gov.pl/isap.nsf/DocDetails.xsp?id=WDU20180001000',
])
def test_act_eli(identifier):
    assert act_eli(identifier) == 'DU/2018/1000'


def test_act_eli_rejects_other_references():
    with pytest.raises(ValueError):
        act_eli('ustawa o ochronie danych osobowych')


@pytest.mark.parametrize('instruction, action', [
    ('w art. 18i § 12 otrzymuje brzmienie:', 'replace'),
    ('po art. 22¹ dodaje się art. 22² i art. 22³ w brzmieniu:', 'insert'),
    ('w art. 5 dodaje się ust. 3 w brzmieniu:', 'add'),
    ('w art. 7 uchyla się pkt 2;', 'delete'),
    ('wyrazy „Generalny Inspektor” zastępuje się wyrazami „Prezes Urzędu”', 'replace'),
])
def test_amendment_action(instruction, action):
    assert amendment_action(instruction) == action


class TestSejmELIParser:
    def test_act(self, poland):
        parser = SejmELIParser().parse(str(poland / 'DU_2018_1000.html'))
        assert parser.preface == 'Ustawa z dnia 10 maja 2018 r. o ochronie danych osobowych'
        chapter = parser.chapters[0]
        assert (chapter['eId'], chapter['type'], chapter['num'], chapter['heading']) == (
            'cpt_1', 'chapter', 'Rozdział 1', 'Przepisy ogólne')
        first = parser.articles[0]
        assert (first['eId'], first['num'], first['parent']) == ('art_1', 'Art. 1.', 'cpt_1')
        assert [c['eId'] for c in first['children']] == ['par_1', 'par_2']
        assert first['children'][1]['text'].startswith('2. Ustawa określa: 1) podmioty publiczne')
        # Footnotes are left out
        assert 'Niniejsza ustawa' not in parser.preface

    def test_amending_articles(self, poland):
        parser = SejmELIParser().parse(str(poland / 'DU_2018_1000.html'))
        article = next(a for a in parser.articles if a['eId'] == 'art_110')
        intro, first, second = article['children']
        assert intro['amendment'] is None
        assert first['amendment']['action'] == 'replace'
        assert first['amendment']['amended_act'].endswith('o postępowaniu egzekucyjnym w administracji')
        assert second['amendment']['quoted'][0]['text'].startswith('§ 12. Postępowanie w sprawie sprzeciwu')

    def test_consolidated_text(self, poland):
        parser = SejmELIParser().parse(str(poland / 'DU_2019_1781.html'))
        assert parser.preface == 'Tekst jednolity ustawy z dnia 10 maja 2018 r. o ochronie danych osobowych'
        assert 'art_5a' in [a['eId'] for a in parser.articles]
        # The announcement itself is not part of the act
        assert not any('ogłasza się' in c['text'] for a in parser.articles for c in a['children'])

    def test_regulation_divided_into_paragraphs(self, poland):
        parser = SejmELIParser().parse(str(poland / 'DU_2024_1973_trimmed.html'))
        # Each § of a regulation without articles is an article; the enacting formula is not
        assert [(a['eId'], a['num']) for a in parser.articles] == [('art_1', '§ 1.'), ('art_2', '§ 2.')]
        assert parser.articles[0]['children'][0]['text'] == (
            'Rozporządzenie określa: 1) wzory banderol; 2) wysokość kwot stanowiących wartość banderol.')
        assert [r['text'] for r in parser.recitals] == [
            'Na podstawie art. 125 ustawy z dnia 6 grudnia 2008 r. o podatku akcyzowym zarządza się, co następuje:']

    def test_annex_points_and_tables(self, poland):
        parser = SejmELIParser().parse(str(poland / 'DU_2024_1973_trimmed.html'))
        points, table = parser.annexes
        assert [c['text'] for c in points['children']] == [
            'Banderole są:', '1) pokrojone według ustalonych wymiarów;']
        # A table title and its rows are kept
        assert (table['num'], table['heading']) == (
            'Załącznik nr 2', 'Wysokość kwot stanowiących wartość banderol podatkowych')
        assert [c['text'] for c in table['children']] == [
            'Tabela 1. Wyroby tytoniowe Lp. Rodzaj wyrobów Kwota w zł', '1 Papierosy 0,15']

    def test_division_misplaced_inside_an_article(self, tmp_path):
        # Kodeks pracy: the repealed chapter II of dział XIII sits inside the last point of art. 283
        page = tmp_path / 'kp.html'
        page.write_text(
            '<html><body><section><h1><span>Ustawa</span><span>Kodeks pracy</span></h1><div class="block">'
            '<div class="unit unit_bran" data-id="bran_TRZYNASTY"><p>Dział TRZYNASTY</p>'
            '<div class="unit-inner">'
            '<div class="unit unit_arti" data-id="arti_283"><h3>Art. 283.</h3><div class="unit-inner">'
            '<div class="unit unit_pint" data-id="pint_9"><h3>9)</h3><div class="unit-inner">'
            '<div data-template="xText">dopuszcza dziecko do pracy.</div>'
            '<div class="unit unit_chpt" data-id="chpt_II"><h3></h3><p>Rozdział II</p><div class="unit-inner">'
            '<div data-template="xText">(uchylony)</div></div></div>'
            '</div></div></div></div>'
            '</div></div></div></section></body></html>', encoding='utf-8')
        parser = SejmELIParser().parse(str(page))
        article = parser.articles[0]
        assert [c['text'] for c in article['children']] == ['9) dopuszcza dziecko do pracy.']
        assert [(c['eId'], c['num'], c['parent']) for c in parser.chapters] == [
            ('sct_TRZYNASTY', 'Dział TRZYNASTY', None), ('cpt_II', 'Rozdział II', 'sct_TRZYNASTY')]

    def test_not_an_act(self, tmp_path):
        page = tmp_path / 'page.html'
        page.write_text('<html><body><p>Nothing</p></body></html>')
        with pytest.raises(FileLoadError):
            SejmELIParser().parse(str(page))


class TestPolandSource:
    def _fetch(self, poland, tmp_path, identifier, expected, **kwargs):
        files = {'DU/2018/1000': poland / 'DU_2018_1000.html', 'DU/2019/1781': poland / 'DU_2019_1781.html'}
        with patch.object(SejmELIClient, 'act', side_effect=lambda eli: ACTS[eli]), \
                patch.object(SejmELIClient, 'download_text', side_effect=lambda eli: str(files[eli])) as download:
            doc = tulit.fetch(identifier, download_dir=str(tmp_path), **kwargs)
        download.assert_called_once_with(expected)
        return doc

    def test_act_as_published(self, poland, tmp_path):
        doc = self._fetch(poland, tmp_path, 'Dz.U. 2018 poz. 1000', 'DU/2018/1000', jurisdiction='PL')
        meta = doc['meta']
        assert (meta['version'], meta['version_date'], meta['in_force']) == ('original', '2018-05-10', True)
        assert meta['eli'] == 'https://eli.gov.pl/eli/DU/2018/1000/ogl'

    def test_latest_consolidated_text_with_html(self, poland, tmp_path):
        doc = self._fetch(poland, tmp_path, 'DU/2018/1000', 'DU/2019/1781', jurisdiction='PL',
                          version='consolidated')
        assert (doc['meta']['version'], doc['meta']['version_date']) == ('consolidated', '2019-08-30')
        assert doc['meta']['eli'] == 'https://eli.gov.pl/eli/DU/2018/1000/ogl'

    def test_consolidated_text_names_itself(self, poland, tmp_path):
        doc = self._fetch(poland, tmp_path, 'https://eli.gov.pl/eli/DU/2019/1781/ogl', 'DU/2019/1781')
        assert doc['meta']['version'] == 'consolidated'

    def test_original_of_a_consolidated_text(self, poland, tmp_path):
        self._fetch(poland, tmp_path, 'DU/2019/1781', 'DU/2018/1000', jurisdiction='PL', version='original')

    def test_no_consolidated_text_yet(self, poland, tmp_path):
        with pytest.raises(FileLoadError, match='on or before 2018-06-01'):
            self._fetch(poland, tmp_path, 'DU/2018/1000', None, jurisdiction='PL', version='consolidated',
                        date='2018-06-01')

    def test_pdf_only(self, tmp_path):
        with patch.object(SejmELIClient, 'act', return_value=dict(ACT, textHTML=False, references={})):
            with pytest.raises(FileLoadError, match='only as PDF'):
                tulit.fetch('DU/2018/1000', jurisdiction='PL', download_dir=str(tmp_path))


class TestSejmELIClient:
    def test_download_text(self, tmp_path):
        client = SejmELIClient(download_dir=str(tmp_path))
        with patch.object(client.session, 'get', return_value=Mock(status_code=200, content=b'<html/>')) as get:
            path = client.download_text('DU/2018/1000')
        assert get.call_args.args[0] == 'https://api.sejm.gov.pl/eli/acts/DU/2018/1000/text.html'
        assert path.endswith('DU_2018_1000.html')

    def test_missing_act(self, tmp_path):
        client = SejmELIClient(download_dir=str(tmp_path))
        with patch.object(client.session, 'get', return_value=Mock(status_code=404)):
            with pytest.raises(FileLoadError):
                client.act('DU/2018/99999')
