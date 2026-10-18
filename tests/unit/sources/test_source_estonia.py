from unittest.mock import Mock, patch

import pytest

import tulit
from tulit.client.state.estonia import RiigiTeatajaClient
from tulit.parser.exceptions import FileLoadError
from tulit.parser.xml.riigiteataja import RiigiTeatajaParser, amendment_action

GROUP = 1045568
TEXTS = [
    {'globaalID': 104012019011, 'terviktekstID': GROUP, 'tekst': 'algtekst-terviktekst', 'lyhend': 'IKS',
     'kehtivus': {'algus': '2019-01-15', 'lopp': '2023-10-31'}},
    {'globaalID': 111032023011, 'terviktekstID': GROUP, 'tekst': 'terviktekst', 'lyhend': 'IKS',
     'kehtivus': {'algus': '2023-11-01', 'lopp': '2024-12-31'}},
    {'globaalID': 130062026052, 'terviktekstID': GROUP, 'tekst': 'terviktekst', 'lyhend': 'IKS',
     'kehtivus': {'algus': '2026-10-01', 'lopp': None}},
    # An older act with the same abbreviation
    {'globaalID': 130122010011, 'terviktekstID': 311276, 'tekst': 'terviktekst', 'lyhend': 'IKS',
     'kehtivus': {'algus': '2011-01-01', 'lopp': '2014-06-30'}},
]


@pytest.fixture
def estonia(data_root):
    return data_root / 'sources' / 'member_states' / 'estonia'


@pytest.mark.parametrize('instruction, action', [
    ('1) paragrahv 14 muudetakse ja sõnastatakse järgmiselt:', 'replace'),
    ('4) paragrahvi 44 lõike 9 teine lause tunnistatakse kehtetuks;', 'delete'),
    ('5) paragrahvi 47 täiendatakse lõikega 4 järgmises sõnastuses:', 'add'),
])
def test_amendment_action(instruction, action):
    assert amendment_action(instruction) == action


class TestRiigiTeatajaParser:
    def test_consolidated_text(self, estonia):
        parser = RiigiTeatajaParser().parse(str(estonia / '130062026052.xml'))
        assert parser.preface == 'Isikuandmete kaitse seadus'
        chapter = parser.chapters[0]
        assert (chapter['eId'], chapter['type'], chapter['num'], chapter['heading']) == (
            'cpt_1', 'chapter', '1. peatükk', 'Üldsätted')
        sections = [c for c in parser.chapters if c['type'] == 'section']
        assert sections and all(c['parent'].startswith('cpt_') for c in sections)
        first = parser.articles[0]
        assert (first['eId'], first['num'], first['heading'], first['parent']) == (
            'art_1', '§ 1.', 'Seaduse reguleerimisala', 'cpt_1')
        assert [c['eId'] for c in first['children']] == ['par_1', 'par_2']
        assert first['children'][0]['text'].startswith('(1) Käesolev seadus reguleerib: 1) füüsiliste isikute')
        # Superscript numbers
        inserted = next(a for a in parser.articles if a['eId'] == 'art_2-1')
        assert inserted['num'] == '§ 2¹.'
        children = [c['eId'] for a in parser.articles for c in a['children']]
        assert 'par_5-1' in children and 'par_5-2' in children
        # Editorial amendment notes are left out
        assert not any('[RT I' in c['text'] for a in parser.articles for c in a['children'])

    def test_amending_act(self, estonia):
        parser = RiigiTeatajaParser().parse(str(estonia / '111032023001.xml'))
        article = parser.articles[0]
        assert article['heading'] == 'Karistusseadustiku muutmine'
        intro, first, second = article['children'][:3]
        assert intro['text'] == 'Karistusseadustikus tehakse järgmised muudatused:'
        assert first['eId'] == 'par_1'
        assert first['amendment']['action'] == 'replace'
        assert first['amendment']['amended_act'] == 'Karistusseadustikus'
        assert first['amendment']['quoted'][0]['text'] == '§ 14. Juriidilise isiku vastutus'
        assert '§ 37¹' in second['text']

    def test_plain_amendment(self, estonia):
        # § 2 holds one amendment as plain text, not as numbered points in HTML
        article = RiigiTeatajaParser().parse(str(estonia / '111032023001.xml')).articles[1]
        assert len(article['children']) == 1
        amendment = article['children'][0]['amendment']
        assert (amendment['action'], amendment['amended_act']) == ('add', 'Isikuandmete kaitse seaduse')
        assert amendment['quoted'][0]['text'].startswith('(1) Käesolevas peatükis')

    @staticmethod
    def _act(tmp_path, content):
        path = tmp_path / 'act.xml'
        path.write_text(f'<?xml version="1.0" encoding="UTF-8"?><oigusakt xmlns="tyviseadus_1_10.02.2010">'
                        f'<aktinimi><nimi><pealkiri>Seadus</pealkiri></nimi></aktinimi>'
                        f'<sisu>{content}</sisu></oigusakt>', encoding='utf-8')
        return RiigiTeatajaParser().parse(str(path))

    def test_html_in_subsection(self, tmp_path):
        parser = self._act(tmp_path, """
            <sisuTekst><tavatekst>Kõikumatus usus ja vankumatus tahtes</tavatekst></sisuTekst>
            <paragrahv><paragrahvNr>170</paragrahvNr><kuvatavNr><![CDATA[§ 170.]]></kuvatavNr>
              <loige><sisuTekst><tavatekst>Käesolev seadus jõustub.</tavatekst></sisuTekst>
                <sisuTekst><HTMLKonteiner><![CDATA[<hr/><p>Jõustumise kuupäev on <a href="x">märgitud</a>.</p>]]>
                </HTMLKonteiner></sisuTekst>
                <sisuTekst><HTMLKonteiner><![CDATA[<p><table summary="allkiri"><tr><td><b>Riigikogu esimees
                  Toomas SAVI</b></td></tr></table></p>]]></HTMLKonteiner></sisuTekst></loige>
              <loige><sisuTekst><tavatekst>Õiend<reavahetus/>Käesolev tekst vastab eelnõu tekstile.</tavatekst>
                </sisuTekst></loige>
              <veaparandus><veaparandusTekst>Veaparandus: parandatud</veaparandusTekst></veaparandus>
            </paragrahv>""")
        [article] = parser.articles
        assert [c['text'] for c in article['children']] == [
            'Käesolev seadus jõustub. Jõustumise kuupäev on märgitud.']
        assert parser.conclusions == {'conclusion_text': 'Õiend Käesolev tekst vastab eelnõu tekstile.',
                                      'signature': 'Riigikogu esimees Toomas SAVI'}
        # The consolidated text sets the preamble as plain text before the paragraphs
        assert parser.recitals == [{'eId': 'rct_1', 'text': 'Kõikumatus usus ja vankumatus tahtes'}]

    def test_embedded_files_and_legal_basis(self, tmp_path):
        parser = self._act(tmp_path, """
            <preambul><tavatekst>Määrus kehtestatakse «</tavatekst><viide><kuvatavTekst>Lennundusseaduse</kuvatavTekst>
              <viideURID><viideURI>./dyn=1&amp;id=2</viideURI></viideURID></viide>
              <tavatekst>» § 57<sup>2</sup> lõike 8 alusel.</tavatekst></preambul>
            <paragrahv><paragrahvNr>1</paragrahvNr><kuvatavNr><![CDATA[§ 1.]]></kuvatavNr>
              <loige><sisuTekst><tavatekst>(1) Eelarve</tavatekst>
                <fail failNimi="tabel.png" failVorming="png">iVBORw0KGgoAAAANSUhEUg</fail></sisuTekst></loige>
            </paragrahv>""")
        assert parser.citations == [
            {'eId': 'cit_1', 'text': 'Määrus kehtestatakse «Lennundusseaduse» § 57² lõike 8 alusel.'}]
        assert parser.articles[0]['children'][0]['text'] == '(1) Eelarve'

    def test_text_without_paragraphs(self, tmp_path):
        parser = self._act(tmp_path, """<sisuTekst><HTMLKonteiner><![CDATA[<p align="center">OTSUS</p>
            <p>1. Lugeda põhiseadus vastuvõetuks.</p><p></p>]]></HTMLKonteiner></sisuTekst>""")
        [article] = parser.articles
        assert article['num'] is None
        assert [c['text'] for c in article['children']] == ['OTSUS', '1. Lugeda põhiseadus vastuvõetuks.']

    def test_unreadable_file(self, tmp_path):
        broken = tmp_path / 'broken.xml'
        broken.write_text('<oigusakt')
        with pytest.raises(FileLoadError):
            RiigiTeatajaParser().parse(str(broken))


class TestEstoniaSource:
    def _fetch(self, estonia, tmp_path, identifier, chosen, **kwargs):
        with patch.object(RiigiTeatajaClient, 'search', return_value=TEXTS), \
                patch.object(RiigiTeatajaClient, 'act', return_value={
                    'global_id': '104012019011', 'group_id': GROUP, 'text_type': 'algtekst-terviktekst',
                    'title': 'Isikuandmete kaitse seadus', 'abbreviation': 'IKS'}), \
                patch.object(RiigiTeatajaClient, 'download',
                             return_value=str(estonia / '130062026052.xml')) as download:
            doc = tulit.fetch(identifier, download_dir=str(tmp_path), **kwargs)
        download.assert_called_once_with(chosen)
        return doc

    def test_current_text_by_abbreviation(self, estonia, tmp_path):
        doc = self._fetch(estonia, tmp_path, 'IKS', '130062026052', jurisdiction='EE')
        meta = doc['meta']
        assert (meta['jurisdiction'], meta['version'], meta['version_date']) == ('EE', 'consolidated', '2026-10-01')
        assert meta['source'] == 'https://www.riigiteataja.ee/akt/130062026052'

    def test_text_in_force_on_a_date(self, estonia, tmp_path):
        doc = self._fetch(estonia, tmp_path, 'IKS', '111032023011', jurisdiction='EE',
                          version='consolidated', date='2024-06-01')
        assert doc['meta']['version_date'] == '2023-11-01'

    def test_original_text(self, estonia, tmp_path):
        doc = self._fetch(estonia, tmp_path, 'IKS', '104012019011', jurisdiction='EE', version='original')
        assert doc['meta']['version'] == 'original'
        assert doc['meta']['version_date'] == '2018-12-12'

    def test_dates_without_time_zone(self, tmp_path):
        path = tmp_path / '24304.xml'
        path.write_text('<?xml version="1.0" encoding="UTF-8"?><oigusakt xmlns="tyviseadus_1_10.02.2010">'
                        '<metaandmed><avaldamismarge><avaldamineKuupaev>1992-07-06+03:00</avaldamineKuupaev>'
                        '</avaldamismarge></metaandmed><aktinimi><nimi><pealkiri>Eesti Vabariigi põhiseadus</pealkiri>'
                        '</nimi></aktinimi><sisu><paragrahv><paragrahvNr>1</paragrahvNr><loige><sisuTekst>'
                        '<tavatekst>Eesti on iseseisev.</tavatekst></sisuTekst></loige></paragrahv></sisu></oigusakt>',
                        encoding='utf-8')
        texts = [{'globaalID': 24304, 'terviktekstID': 1, 'tekst': 'algtekst-terviktekst', 'lyhend': 'PS',
                  'kehtivus': {'algus': '1992-07-03+03:00', 'lopp': '2003-01-01+02:00'}}]
        with patch.object(RiigiTeatajaClient, 'search', return_value=texts), \
                patch.object(RiigiTeatajaClient, 'download', return_value=str(path)):
            original = tulit.fetch('PS', jurisdiction='EE', version='original', download_dir=str(tmp_path))
            consolidated = tulit.fetch('PS', jurisdiction='EE', version='consolidated', date='2000-01-01',
                                       download_dir=str(tmp_path))
        # No adoption date: the publication date stands in
        assert original['meta']['version_date'] == '1992-07-06'
        assert original['meta']['date_publication'] == '1992-07-06'
        assert consolidated['meta']['version_date'] == '1992-07-03'

    def test_text_id_url(self, estonia, tmp_path):
        doc = self._fetch(estonia, tmp_path, 'https://www.riigiteataja.ee/akt/104012019011', '104012019011')
        assert doc['meta']['jurisdiction'] == 'EE'
        assert doc['meta']['version'] == 'original'

    def test_no_text_in_force(self, estonia, tmp_path):
        with pytest.raises(FileLoadError, match='in force on 2025-06-01'):
            self._fetch(estonia, tmp_path, 'IKS', None, jurisdiction='EE', version='consolidated',
                        date='2025-06-01')

    def test_invalid_identifier(self, tmp_path):
        with pytest.raises(ValueError, match='not a Riigi Teataja'):
            tulit.fetch('isikuandmete kaitse', jurisdiction='EE', download_dir=str(tmp_path))


class TestRiigiTeatajaClient:
    def test_search_pages(self, tmp_path):
        client = RiigiTeatajaClient(download_dir=str(tmp_path))
        pages = [Mock(status_code=200, json=Mock(return_value={'metaandmed': {'kokku': 3}, 'aktid': TEXTS[:2]})),
                 Mock(status_code=200, json=Mock(return_value={'metaandmed': {'kokku': 3}, 'aktid': TEXTS[2:3]}))]
        with patch.object(client.session, 'get', side_effect=pages) as get:
            texts = client.texts(GROUP, abbreviation='IKS')
        assert [t['globaalID'] for t in texts] == [104012019011, 111032023011, 130062026052]
        assert get.call_args_list[1].kwargs['params']['leht'] == 2

    def test_download(self, tmp_path):
        client = RiigiTeatajaClient(download_dir=str(tmp_path))
        response = Mock(status_code=200, content=b'<?xml version="1.0"?><oigusakt/>')
        with patch.object(client.session, 'get', return_value=response) as get:
            path = client.download('104012019011')
        assert get.call_args.args[0] == 'https://www.riigiteataja.ee/public-api/api/v1/akt/104012019011/xml'
        assert path.endswith('104012019011.xml')

    def test_missing_text(self, tmp_path):
        client = RiigiTeatajaClient(download_dir=str(tmp_path))
        with patch.object(client.session, 'get', return_value=Mock(status_code=404)):
            with pytest.raises(FileLoadError):
                client.download('1')
