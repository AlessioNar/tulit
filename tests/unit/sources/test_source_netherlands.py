import shutil
from unittest.mock import Mock, patch

import pytest

import tulit
from tulit.client.state.netherlands import BWBClient
from tulit.parser.exceptions import FileLoadError
from tulit.parser.xml.bwb import BWBParser, amendment_action
from tulit.sources.nl import staatsblad_id


@pytest.fixture
def staatsblad(data_root):
    return data_root / 'sources' / 'member_states' / 'netherlands' / 'staatsblad'


@pytest.mark.parametrize('identifier', ['stb-2018-144', 'Stb. 2018, 144', 'Staatsblad 2018, 144', 'stb 2018 144'])
def test_staatsblad_id(identifier):
    assert staatsblad_id(identifier) == 'stb-2018-144'


def test_staatsblad_id_rejects_bwb_identifiers():
    assert staatsblad_id('BWBR0040940') is None


@pytest.mark.parametrize('instruction, action', [
    ('In artikel 6 wordt «a» vervangen door «b».', 'replace'),
    ('De bijlage komt te luiden:', 'replace'),
    ('Na artikel 4 wordt een artikel ingevoegd, luidende:', 'insert'),
    ('Aan artikel 5 wordt een lid toegevoegd, luidende:', 'add'),
    ('Artikel 7 vervalt.', 'delete'),
    ('Artikel 6a wordt als volgt gewijzigd:', 'amend'),
    ('In artikel 7 komt de zinsnede betreffende de Instellingswet te luiden:', 'replace'),
    ('De Wet bescherming persoonsgegevens wordt ingetrokken.', 'repeal'),
    ('De Grondwet ondergaat de in artikel II omschreven veranderingen.', 'amend'),
])
def test_amendment_action(instruction, action):
    assert amendment_action(instruction) == action


class TestStaatsbladParser:
    def test_new_act(self, staatsblad):
        parser = BWBParser().parse(str(staatsblad / 'stb-2018-144.xml'))
        assert parser.preface.startswith('Wet van 16 mei 2018, houdende regels ter uitvoering van Verordening (EU)')
        assert parser.formula.startswith('Wij Willem-Alexander')
        assert parser.chapters[0]['type'] == 'chapter'
        article = parser.articles[0]
        assert (article['eId'], article['parent']) == ('art_1', 'cpt_1')
        # Amending articles of an act that also amends others
        amending = [a for a in parser.articles if any(c['amendment'] for c in a['children'])]
        assert amending

    def test_amending_act(self, staatsblad):
        parser = BWBParser().parse(str(staatsblad / 'stb-2020-58.xml'))
        assert [a['eId'] for a in parser.articles] == ['art_I', 'art_II', 'art_III', 'art_IV']
        intro, first, second = parser.articles[0]['children'][:3]
        assert intro['text'] == 'Het Besluit rechtspositie rechterlijke ambtenaren wordt als volgt gewijzigd:'
        assert intro['amendment'] is None
        assert first['eId'] == 'par_a'
        assert first['amendment']['action'] == 'replace'
        assert first['amendment']['amended_act'] == 'Het Besluit rechtspositie rechterlijke ambtenaren'
        assert second['amendment']['action'] == 'amend'
        assert len(second['amendment']['quoted']) == 3
        # The annex quoted by an amendment is not an annex of the act
        assert parser.annexes == []


class TestNetherlandsOriginals:
    def test_fetch_by_staatsblad_id(self, staatsblad, tmp_path):
        with patch.object(BWBClient, 'download_publication',
                          return_value=str(staatsblad / 'stb-2018-144.xml')) as download:
            doc = tulit.fetch('Stb. 2018, 144', jurisdiction='NL', download_dir=str(tmp_path))
        download.assert_called_once_with('stb-2018-144')
        meta = doc['meta']
        assert (meta['version'], meta['version_date']) == ('original', '2018-05-16')
        assert meta['eli'] == 'https://zoek.officielebekendmakingen.nl/stb-2018-144'

    def test_url_selects_netherlands(self, staatsblad, tmp_path):
        with patch.object(BWBClient, 'download_publication', return_value=str(staatsblad / 'stb-2020-58.xml')):
            doc = tulit.fetch('https://zoek.officielebekendmakingen.nl/stb-2020-58.html', download_dir=str(tmp_path))
        assert doc['meta']['jurisdiction'] == 'NL'

    def test_original_of_a_bwb_regulation(self, staatsblad, tmp_path):
        with patch.object(BWBClient, 'original_publication', return_value='stb-2018-144'), \
                patch.object(BWBClient, 'download_publication',
                             return_value=str(staatsblad / 'stb-2018-144.xml')) as download:
            tulit.fetch('BWBR0040940', jurisdiction='NL', version='original', download_dir=str(tmp_path))
        download.assert_called_once_with('stb-2018-144')

    def test_invalid_requests(self, tmp_path):
        with pytest.raises(ValueError, match='BWB identifier'):
            tulit.fetch('stb-2018-144', jurisdiction='NL', version='consolidated', download_dir=str(tmp_path))
        with pytest.raises(ValueError, match='original version has none'):
            tulit.fetch('stb-2018-144', jurisdiction='NL', date='2020-01-01', download_dir=str(tmp_path))
        with pytest.raises(ValueError, match='not a BWB or Staatsblad identifier'):
            tulit.fetch('UAVG', jurisdiction='NL', download_dir=str(tmp_path))


class TestStaatsbladClient:
    def test_download(self, tmp_path):
        client = BWBClient(download_dir=str(tmp_path))
        response = Mock(status_code=200, content=b'<?xml version="1.0"?><officiele-publicatie/>')
        with patch.object(client.session, 'get', return_value=response) as get:
            path = client.download_publication('stb-2018-144')
        assert get.call_args.args[0].endswith('/stb/2018/stb-2018-144/1/xml/stb-2018-144.xml')
        assert path.endswith('stb-2018-144.xml')

    @pytest.mark.parametrize('status', [204, 404])
    def test_missing_publication(self, tmp_path, status):
        client = BWBClient(download_dir=str(tmp_path))
        with patch.object(client.session, 'get', return_value=Mock(status_code=status, content=b'')):
            with pytest.raises(FileLoadError, match='from 1995'):
                client.download_publication('stb-1881-35')

    def test_original_publication(self, data_root, tmp_path):
        consolidated = tmp_path / 'BWBR0040940.xml'
        shutil.copy(data_root / 'sources' / 'member_states' / 'netherlands' / 'bwb' / 'BWBR0040940.xml', consolidated)
        client = BWBClient(download_dir=str(tmp_path))
        with patch.object(client, 'download', return_value=(str(consolidated), {})):
            assert client.original_publication('BWBR0040940') == 'stb-2018-144'
