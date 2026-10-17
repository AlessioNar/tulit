from unittest.mock import Mock, patch

import pytest

import tulit
from tulit.client.state.sweden import RiksdagenClient
from tulit.parser.exceptions import FileLoadError
from tulit.parser.html.riksdagen import RiksdagenSFSParser
from tulit.sources.se import document_id


@pytest.fixture
def statute(data_root):
    return str(data_root / 'sources' / 'member_states' / 'sweden' / 'sfs-2018-218.html')


@pytest.mark.parametrize('identifier', ['2018:218', 'SFS 2018:218', 'sfs-2018-218',
                                        'https://data.riksdagen.se/dokument/sfs-2018-218.html'])
def test_document_id(identifier):
    assert document_id(identifier) == 'sfs-2018-218'


def test_document_id_rejects_other_identifiers():
    with pytest.raises(ValueError):
        document_id('dataskyddslagen')


class TestRiksdagenSFSParser:
    def test_structure(self, statute):
        parser = RiksdagenSFSParser(date='2026-10-17').parse(statute)
        assert parser.preface == 'Lag (2018:218) med kompletterande bestämmelser till EU:s dataskyddsförordning'
        assert [(c['eId'], c['num'], c['heading']) for c in parser.chapters[:2]] == [
            ('cpt_1', '1 kap.', 'Inledande bestämmelser'),
            ('cpt_2', '2 kap.', 'Rättslig grund för behandling av personuppgifter')]
        first, second = parser.articles[:2]
        assert (first['eId'], first['num'], first['parent']) == ('art_1-1', '1 §', 'cpt_1')
        assert [c['eId'] for c in first['children']] == ['unp_1', 'unp_2']
        assert second['heading'] == 'Utvidgad tillämpning av bestämmelserna i EU:s dataskyddsförordning'
        # Section numbers restart in every chapter
        assert 'art_7-3a' in [a['eId'] for a in parser.articles]

    def test_version_in_force(self, statute):
        """1 kap. 3 § is replaced on 2027-01-01: one version before, the other from that date."""
        before = RiksdagenSFSParser(date='2026-10-17').parse(statute)
        after = RiksdagenSFSParser(date='2027-01-01').parse(statute)
        old = [a for a in before.articles if a['eId'] == 'art_1-3']
        new = [a for a in after.articles if a['eId'] == 'art_1-3']
        assert len(old) == len(new) == 1
        assert old[0]['children'][0]['text'] != new[0]['children'][0]['text']
        assert not any('Upphör att gälla' in c['text'] for a in before.articles for c in a['children'])

    def test_transitional_provisions(self, statute):
        parser = RiksdagenSFSParser().parse(statute)
        annex = parser.annexes[0]
        assert annex['heading'] == 'Övergångsbestämmelser'
        assert annex['children'][0]['text'].startswith('2018:218 1. Denna lag träder i kraft den 25 maj 2018.')
        assert annex['children'][1]['text'].startswith('2018:1248')

    def test_not_a_statute(self, tmp_path):
        page = tmp_path / 'page.html'
        page.write_text('<p>Nothing</p>')
        with pytest.raises(FileLoadError):
            RiksdagenSFSParser().parse(str(page))


class TestSwedenSource:
    def test_fetch(self, statute, tmp_path):
        with patch.object(RiksdagenClient, 'download', return_value=statute) as download, \
                patch.object(RiksdagenClient, 'metadata', return_value={'datum': '2018-04-19 00:00:00'}):
            doc = tulit.fetch('SFS 2018:218', jurisdiction='SE', download_dir=str(tmp_path))
        download.assert_called_once_with('sfs-2018-218')
        meta = doc['meta']
        assert (meta['jurisdiction'], meta['version'], meta['date_document']) == ('SE', 'consolidated', '2018-04-19')

    def test_past_dates_are_rejected(self, tmp_path):
        with pytest.raises(ValueError, match='past date'):
            tulit.fetch('2018:218', jurisdiction='SE', date='2020-01-01', download_dir=str(tmp_path))


class TestRiksdagenClient:
    def test_download(self, tmp_path):
        client = RiksdagenClient(download_dir=str(tmp_path))
        with patch.object(client.session, 'get', return_value=Mock(status_code=200, content=b'<h2>Lag</h2>')) as get:
            path = client.download('sfs-2018-218')
        assert get.call_args.args[0] == 'https://data.riksdagen.se/dokument/sfs-2018-218.html'
        assert path.endswith('sfs-2018-218.html')

    def test_missing_statute(self, tmp_path):
        client = RiksdagenClient(download_dir=str(tmp_path))
        with patch.object(client.session, 'get', return_value=Mock(status_code=200, content=b'  ')):
            with pytest.raises(FileLoadError):
                client.download('sfs-1800-1')
