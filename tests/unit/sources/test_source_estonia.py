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
