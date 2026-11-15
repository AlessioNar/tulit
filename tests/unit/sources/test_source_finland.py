import shutil
from unittest.mock import call, patch

import pytest

import tulit
from tulit.client.state.finlex import FinlexClient
from tulit.parser.exceptions import FileLoadError
from tulit.parser.xml.akomantoso import create_akn_parser
from tulit.parser.xml.akomantoso.finlex import FinlexAKNParser
from tulit.sources.fi import statute_number


@pytest.mark.parametrize('identifier, expected', [
    ('1050/2018', ('2018', '1050')),
    ('sd/2018/1050', ('2018', '1050')),
    ('http://data.finlex.fi/eli/sd/2018/1050/ajantasa', ('2018', '1050')),
])
def test_statute_number(identifier, expected):
    assert statute_number(identifier) == expected


def test_statute_number_rejects_text():
    with pytest.raises(ValueError):
        statute_number('tietosuojalaki')


@pytest.fixture
def consolidated(data_root, tmp_path):
    source = data_root / 'sources' / 'member_states' / 'finland' / 'finlex' / '1050_2018_consolidated_fin.xml'
    target = tmp_path / 'finlex.xml'
    shutil.copy(source, target)
    return str(target)


def test_fetch_consolidated(consolidated, tmp_path):
    # Finlex keeps a text after each amending statute; the latest lists every amendment and its entry into force
    with patch.object(FinlexClient, 'versions', return_value=['', '20240029', '20250437']), \
            patch.object(FinlexClient, 'download', return_value=consolidated) as download:
        doc = tulit.fetch('1050/2018', jurisdiction='FI', version='consolidated', date='2025-06-01',
                          download_dir=str(tmp_path))
    assert download.call_args_list == [
        call('2018', '1050', consolidated=True, language='fin', version='20250437'),
        call('2018', '1050', consolidated=True, language='fin', version='20240029')]
    assert doc['meta']['eli'] == 'http://data.finlex.fi/eli/sd/2018/1050'
    assert (doc['meta']['version'], doc['meta']['version_date']) == ('consolidated', '2025-01-01')
    # chapters are the only divisions; sections are the articles and subsections their paragraphs
    assert [c['eId'] for c in doc['chapters']] == ['cpt_1', 'cpt_2', 'cpt_3', 'cpt_4', 'cpt_5', 'cpt_6']
    assert doc['articles'][1]['parent'] == 'cpt_1'


def test_consolidated_before_first_version(consolidated, tmp_path):
    with patch.object(FinlexClient, 'versions', return_value=['20250437']), \
            patch.object(FinlexClient, 'download', return_value=consolidated):
        with pytest.raises(FileLoadError, match='in force on 2020-01-01 from 2026-01-01'):
            tulit.fetch('1050/2018', jurisdiction='FI', version='consolidated', date='2020-01-01',
                        download_dir=str(tmp_path))


def test_original_with_decree_number(consolidated, tmp_path):
    # The Criminal Code, 39/1889, is the first act of decree 39: Finlex numbers it 39-001
    with patch.object(FinlexClient, 'download', side_effect=[None, consolidated]) as download:
        doc = tulit.fetch('39/1889', jurisdiction='FI', version='original', download_dir=str(tmp_path))
    assert [c.args[1] for c in download.call_args_list] == ['39', '39-001']
    assert doc['meta']['eli'] == 'http://data.finlex.fi/eli/sd/1889/39-001'
    assert doc['meta']['version_date'] == '2018-12-05'


def test_versions_by_bisection(tmp_path):
    client = FinlexClient(download_dir=str(tmp_path))
    numbers = [str(n) for n in range(1, 60)] + ['60-001', '60-002', '61']
    listing = [(n, 'fin', '') for n in numbers]
    listing[30:30] = [('31', 'swe', ''), ('31', 'fin', '20180817'), ('31', 'swe', '20180817')]
    pages = [listing[i:i + 10] for i in range(0, len(listing), 10)]

    def page(year, n):
        return pages[n - 1] if n <= len(pages) else []

    with patch.object(client, '_listing', side_effect=page) as listed:
        assert client.versions('1999', '31') == ['', '20180817']
        assert client.versions('1889', '60-002') == ['']
    assert listed.call_count < 2 * len(pages)


def test_fetch_by_eli_and_language(consolidated, tmp_path):
    with patch.object(FinlexClient, 'download', return_value=consolidated) as download:
        tulit.fetch('http://data.finlex.fi/eli/sd/2018/1050', language='swe', download_dir=str(tmp_path))
    download.assert_called_once_with('2018', '1050', consolidated=False, language='swe')


def test_missing_statute(tmp_path):
    with patch.object(FinlexClient, 'download', return_value=None):
        with pytest.raises(FileLoadError, match='Finlex has no'):
            tulit.fetch('1/1889', jurisdiction='FI', download_dir=str(tmp_path))


def test_client_sends_user_agent(tmp_path):
    assert 'tulit' in FinlexClient(download_dir=str(tmp_path)).session.headers['User-Agent']


FINLEX_ACT = '''<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
 xmlns:finlex="http://data.finlex.fi/schema/finlex"><act name="main"><meta><identification source="#finlex">
<FRBRWork><FRBRthis value="/akn/fi/act/statute/2025/30"/><FRBRdate date="2025-01-23" name="dateIssued"/></FRBRWork>
</identification></meta>
<preface><p class="title"><docTitle>Asetus yliopistojen koulutusvastuun täsmentämisestä</docTitle></p></preface>
<preamble><formula name="enactingClause"><p>Opetus- ja kulttuuriministeriön päätöksen mukaisesti</p>
<blockContainer><block name="substitutions"><i>muutetaan</i> asetuksen liite seuraavasti:</block></blockContainer>
</formula></preamble>
<body>
<hcontainer name="statuteTextWrapper"><content><p>Tämä asetus tulee voimaan 1 päivänä elokuuta 2026.</p></content>
</hcontainer>
<hcontainer name="conclusions"><hcontainer name="preliminaryWork"><content><p>HE 1/1998</p><p>PeVM 10/1998</p>
</content></hcontainer><hcontainer name="signatures"><content><p>Helsingissä 23.1.2025</p><p><signature>
<role>Tiede- ja kulttuuriministeri</role> <person>Sari Multala</person></signature></p></content></hcontainer>
</hcontainer>
<hcontainer name="attachments"><hcontainer name="attachment"><content><p><i>Liite</i></p>
<p>Yliopistojen nimien lyhenteet:</p><table><tr><td><p>AYO</p></td><td><p>Aalto-yliopisto</p></td></tr></table>
</content></hcontainer></hcontainer>
<hcontainer name="amendmentEntryIntoForceAndApplianceProvisions"><heading>Muutossäädösten voimaantulo</heading>
<hcontainer eId="entryIntoForce_20200869" name="entryIntoForce"><heading>27.11.2020/869:</heading>
<content><p>Tämä laki tulee voimaan 1 päivänä joulukuuta 2020.</p></content></hcontainer></hcontainer>
</body></act></akomaNtoso>'''


def test_finlex_containers(tmp_path):
    path = tmp_path / 'finlex_2025_30_fin.xml'
    path.write_text(FINLEX_ACT, encoding='utf-8')
    parser = create_akn_parser(file_path=str(path))
    parser.parse(str(path))
    assert isinstance(parser, FinlexAKNParser)
    assert parser.formula == ('Opetus- ja kulttuuriministeriön päätöksen mukaisesti muutetaan asetuksen liite '
                              'seuraavasti:')
    # A statute without sections: one unnumbered article
    assert [(a['eId'], a['num'], [c['text'] for c in a['children']]) for a in parser.articles] == [
        ('art_1', None, ['Tämä asetus tulee voimaan 1 päivänä elokuuta 2026.'])]
    assert parser.conclusions == {'conclusion_text': 'HE 1/1998; PeVM 10/1998',
                                  'signature': 'Helsingissä 23.1.2025 Tiede- ja kulttuuriministeri Sari Multala'}
    attachment, entry = parser.annexes
    assert (attachment['num'], [c['text'] for c in attachment['children']]) == (
        'Liite', ['Yliopistojen nimien lyhenteet:', 'AYO Aalto-yliopisto'])
    assert entry['heading'] == 'Muutossäädösten voimaantulo'
    assert entry['children'] == [{'eId': 'entryIntoForce_20200869',
                                  'text': '27.11.2020/869: Tämä laki tulee voimaan 1 päivänä joulukuuta 2020.'}]
