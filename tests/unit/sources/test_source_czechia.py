import json
from unittest.mock import Mock, patch

import pytest

import tulit
from tulit.client.state.czechia import EsbirkaClient
from tulit.parser.exceptions import FileLoadError
from tulit.parser.json.esbirka import EsbirkaParser, amendment_action, fragment_text
from tulit.sources.cz import act_path

ACT = {'staleUrl': '/sb/2019/110/2025-08-01', 'typZneni': 'AKTUALNI', 'datumUcinnostiOd': '2019-04-24',
       'datumUcinnostiZneniOd': '2025-08-01', 'datumCasVyhlaseni': '2019-04-24T00:00:00.000+02:00'}
VERSIONS = {
    '/sb/2019/110': ACT,
    '/sb/2019/110/2025-08-01': ACT,
    '/sb/2019/110/2019-04-24': dict(ACT, staleUrl='/sb/2019/110/2019-04-24', typZneni='MINULE',
                                    datumUcinnostiZneniOd='2019-04-24'),
    '/sb/2019/110/2021-01-01': dict(ACT, staleUrl='/sb/2019/110/2019-04-24', typZneni='MINULE',
                                    datumUcinnostiZneniOd='2019-04-24'),
}


@pytest.fixture
def czechia(data_root):
    return data_root / 'sources' / 'member_states' / 'czechia'


@pytest.mark.parametrize('identifier, expected', [
    ('110/2019 Sb.', ('/sb/2019/110', None)),
    ('zákon č. 110/2019 Sb.', ('/sb/2019/110', None)),
    ('/sb/2019/110', ('/sb/2019/110', None)),
    ('https://e-sbirka.gov.cz/eli/cz/sb/2019/110/2025-08-01/dokument', ('/sb/2019/110', '2025-08-01')),
])
def test_act_path(identifier, expected):
    assert act_path(identifier) == expected


@pytest.mark.parametrize('instruction, action', [
    ('5. V § 68 odstavec 5 zní:', 'replace'),
    ('6. V § 82 se odstavec 2 zrušuje.', 'delete'),
    ('1. V § 14 se slovo „správy“ nahrazuje slovem „moci“.', 'replace'),
    ('2. V § 66 odst. 2 se za slova „evidence“ vkládají slova „rejstříku“.', 'insert'),
    ('9. V § 84a se doplňuje odstavec 6, který zní:', 'add'),
])
def test_amendment_action(instruction, action):
    assert amendment_action(instruction) == action


def test_fragment_text():
    assert fragment_text('Unie<a href="#"><sup>1</sup>)</a>, zároveň') == 'Unie¹), zároveň'
    assert fragment_text('') == ''


class TestEsbirkaParser:
    def test_act(self, czechia):
        parser = EsbirkaParser().parse(str(czechia / 'sb_2019_110_2025-08-01.json'))
        assert parser.preface == 'ZÁKON ze dne 12. března 2019 o zpracování osobních údajů'
        assert parser.formula == 'Parlament se usnesl na tomto zákoně České republiky:'
        part, title = parser.chapters[:2]
        assert (part['eId'], part['type'], part['num'], part['heading']) == (
            'prt_1', 'part', 'ČÁST PRVNÍ', 'ZPRACOVÁNÍ OSOBNÍCH ÚDAJŮ')
        assert (title['eId'], title['type'], title['parent']) == ('tit_1', 'title', 'prt_1')
        first = parser.articles[0]
        assert (first['eId'], first['num'], first['heading'], first['parent']) == (
            'art_1', '§ 1', 'Předmět úpravy', 'tit_1')
        section = next(a for a in parser.articles if a['eId'] == 'art_18')
        assert [c['eId'] for c in section['children']] == ['par_1', 'par_2']
        assert section['children'][0]['text'].startswith('(1) Správce může')
        assert parser.conclusions['signature'].startswith('Vondráček v. r.')

    def test_amending_act(self, czechia):
        parser = EsbirkaParser().parse(str(czechia / 'sb_2025_230_2025-08-01.json'))
        article = parser.articles[0]
        assert (article['num'], article['parent']) == ('Čl. I', 'prt_1')
        intro, first = article['children'][:2]
        assert intro['amendment'] is None
        assert first['eId'] == 'par_1'
        assert first['amendment']['action'] == 'replace'
        assert first['amendment']['amended_act'] == 'Zákon č. 273/2008 Sb., o Policii České republiky'
        replaced = next(c for c in article['children'] if c['eId'] == 'par_5')
        assert replaced['amendment']['quoted'][0]['text'].startswith('(5) Policie může')

    def test_unreadable_file(self, tmp_path):
        broken = tmp_path / 'broken.json'
        broken.write_text('{"metadata": {}}')
        with pytest.raises(FileLoadError):
            EsbirkaParser().parse(str(broken))


class TestCzechiaSource:
    def _fetch(self, czechia, tmp_path, identifier, expected, **kwargs):
        with patch.object(EsbirkaClient, 'metadata', side_effect=lambda path: VERSIONS[path]), \
                patch.object(EsbirkaClient, 'download',
                             return_value=str(czechia / 'sb_2019_110_2025-08-01.json')) as download:
            doc = tulit.fetch(identifier, download_dir=str(tmp_path), **kwargs)
        download.assert_called_once_with(expected)
        return doc

    def test_original(self, czechia, tmp_path):
        doc = self._fetch(czechia, tmp_path, '110/2019 Sb.', '/sb/2019/110/2019-04-24', jurisdiction='CZ')
        meta = doc['meta']
        assert (meta['version'], meta['version_date'], meta['date_document']) == ('original', '2019-04-24', '2019-04-24')
        assert meta['eli'] == 'https://e-sbirka.gov.cz/eli/cz/sb/2019/110'

    def test_current_version(self, czechia, tmp_path):
        doc = self._fetch(czechia, tmp_path, '110/2019 Sb.', '/sb/2019/110/2025-08-01', jurisdiction='CZ',
                          version='consolidated')
        assert (doc['meta']['version_date'], doc['meta']['in_force']) == ('2025-08-01', True)

    def test_version_on_a_date(self, czechia, tmp_path):
        doc = self._fetch(czechia, tmp_path, '110/2019', '/sb/2019/110/2019-04-24', jurisdiction='CZ',
                          version='consolidated', date='2021-01-01')
        assert (doc['meta']['version_date'], doc['meta']['in_force']) == ('2019-04-24', False)

    def test_eli_names_a_version(self, czechia, tmp_path):
        doc = self._fetch(czechia, tmp_path, 'https://e-sbirka.gov.cz/eli/cz/sb/2019/110/2025-08-01',
                          '/sb/2019/110/2025-08-01')
        assert (doc['meta']['jurisdiction'], doc['meta']['version']) == ('CZ', 'consolidated')


class TestEsbirkaClient:
    def test_download_all_pages(self, tmp_path):
        client = EsbirkaClient(download_dir=str(tmp_path))
        pages = [Mock(status_code=200, json=Mock(return_value=ACT)),
                 Mock(status_code=200, json=Mock(return_value={'seznam': [{'id': 1}], 'pocetStranek': 2})),
                 Mock(status_code=200, json=Mock(return_value={'seznam': [{'id': 2}], 'pocetStranek': 2}))]
        with patch.object(client.session, 'get', side_effect=pages) as get:
            path = client.download('/sb/2019/110/2025-08-01')
        assert get.call_args_list[1].args[0].endswith('%2Fsb%2F2019%2F110%2F2025-08-01/fragmenty')
        assert get.call_args_list[2].kwargs['params'] == {'cisloStranky': 1}
        with open(path, encoding='utf-8') as f:
            saved = json.load(f)
        assert [f['id'] for f in saved['fragments']] == [1, 2]
        assert saved['metadata']['staleUrl'] == '/sb/2019/110/2025-08-01'

    def test_no_version_on_a_date(self, tmp_path):
        client = EsbirkaClient(download_dir=str(tmp_path))
        with patch.object(client.session, 'get', return_value=Mock(status_code=200, json=Mock(return_value={}))):
            with pytest.raises(FileLoadError):
                client.metadata('/sb/2019/110/2018-01-01')
