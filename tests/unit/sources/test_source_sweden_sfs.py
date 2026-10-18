"""Sweden, the act as adopted: the PDF of the electronic Svensk författningssamling."""
from unittest.mock import Mock, patch

import pytest

pytest.importorskip('pdfplumber')

import tulit  # noqa: E402
from tulit.client.state.sweden import RiksdagenClient, SFSClient, _months, pdf_url  # noqa: E402
from tulit.parser.exceptions import FileLoadError, NetworkError, UnsupportedError  # noqa: E402
from tulit.parser.pdf.sweden import SFSPDFParser, _numbers, _section_references, masthead  # noqa: E402
from tulit.quality import ERROR, check  # noqa: E402
from tulit.sources.se import sfs_number  # noqa: E402


@pytest.fixture
def sweden(data_root):
    return data_root / 'sources' / 'member_states' / 'sweden'


@pytest.fixture
def act(sweden):
    """SFS 2018:218 as published: the first page and the last two (6 and 7 kap., transitional provisions)."""
    return SFSPDFParser().parse(str(sweden / 'sfs2018-218_p0_5_6.pdf'))


@pytest.mark.parametrize('identifier', ['2018:218', 'SFS 2018:218', 'sfs-2018-218', 'SFS2018:218'])
def test_sfs_number(identifier):
    assert sfs_number(identifier) == ('2018', '218')


def test_sfs_number_rejects_other_identifiers():
    with pytest.raises(UnsupportedError):
        sfs_number('dataskyddslagen')


@pytest.mark.parametrize('listed, numbers', [
    ('1, 2 a och 4–6', ['1', '2a', '4', '6', '5']),
    ('4 a–4 d', ['4a', '4d', '4b', '4c']),
    ('1–2 a', ['1', '2a', '2']),
])
def test_numbers(listed, numbers):
    assert _numbers(listed) == numbers


@pytest.mark.parametrize('clause, references', [
    ('dels att 1 kap. 4 § ska ha följande lydelse', {('1', '4')}),
    ('ska införas tre nya paragrafer, 6 kap. 8 § och 7 kap. 3 a och 6 §§, och närmast före 6 kap. 8 § '
     'och 7 kap. 6 § nya rubriker', {('6', '8'), ('7', '3a'), ('7', '6')}),
    # Headings named by their place are not the sections themselves
    ('ska införas två nya kapitel, 27 och 28 kap., en ny paragraf, 26 kap. 4 a §, och närmast före '
     '26 kap. 1 och 6 §§, och 34 kap. 1 § nya rubriker', {('27', None), ('28', None), ('26', '4a')}),
    ('dels att 27–28 kap. och 38 kap. 1–2 a §§ ska upphöra att gälla',
     {('27', None), ('28', None), ('38', '1'), ('38', '2'), ('38', '2a')}),
    ('Regeringen föreskriver att 3 och 5 §§ förordningen (2018:219) ska ha följande lydelse',
     {(None, '3'), (None, '5')}),
])
def test_section_references(clause, references):
    assert _section_references(clause) == references


class TestSFSPDFParser:
    def test_masthead(self, act, sweden):
        assert act.preface == 'Lag (2018:218) med kompletterande bestämmelser till EU:s dataskyddsförordning'
        assert (act.number, act.issued, act.published) == ('2018:218', '2018-04-19', '2018-04-24')
        assert act.formula == 'Enligt riksdagens beslut föreskrivs följande.'
        assert masthead(str(sweden / 'sfs2018-218_p0_5_6.pdf')) == {
            'number': '2018:218', 'issued': '2018-04-19', 'published': '2018-04-24'}

    def test_chapters_and_sections(self, act):
        assert [(c['eId'], c['num'], c['heading']) for c in act.chapters] == [
            ('cpt_1', '1 kap.', 'Inledande bestämmelser'),
            ('cpt_6', '6 kap.', 'Tillsynsmyndighetens handläggning och beslut'),
            ('cpt_7', '7 kap.', 'Skadestånd och överklagande')]
        first, second, third = act.articles[:3]
        assert (first['eId'], first['num'], first['parent'], first['heading']) == ('art_1-1', '1 §', 'cpt_1', None)
        # The word broken at the line end is mended, the footnote mark left out
        assert first['children'][0]['text'].endswith(
            '(allmän dataskyddsförordning), här benämnd EU:s dataskyddsförordning.')
        assert first['children'][1]['text'] == ('Termer och uttryck i denna lag har samma betydelse som i EU:s '
                                                'dataskyddsförordning.')
        assert second['heading'] == 'Utvidgad tillämpning av bestämmelserna i EU:s dataskyddsförordning'
        # List items belong to their paragraph
        assert len(third['children']) == 1
        assert '1. lagen (2007:258) om behandling av personuppgifter i Försvarsmaktens' in third['children'][0]['text']
        assert [a['eId'] for a in act.articles][-5:] == ['art_7-1', 'art_7-2', 'art_7-3', 'art_7-4', 'art_7-5']
        assert act.articles[-1]['heading'] == 'Överklagandeförbud'
        assert act.articles[-1]['children'][0]['text'] == ('Andra beslut enligt EU:s dataskyddsförordning eller '
                                                           'denna lag än de som avses i 2–4 §§ får inte överklagas.')

    def test_transitional_provisions_and_signatures(self, act):
        annex = act.annexes[0]
        assert annex['eId'] == 'anx_transitional'
        assert [c['text'][:3] for c in annex['children']] == ['1. ', '2. ', '3. ', '4. ', '5. ', '6. ', '7. ', '8. ']
        assert annex['children'][0]['text'] == '1. Denna lag träder i kraft den 25 maj 2018.'
        assert act.conclusions == {'conclusion_text': 'På regeringens vägnar',
                                   'signature': 'STEFAN LÖFVEN MORGAN JOHANSSON (Justitiedepartementet)'}

    def test_quality(self, act):
        assert not [p for p in check(act.to_dict()) if p.severity == ERROR]

    def test_amending_act_inserting_sections(self, sweden):
        act = SFSPDFParser().parse(str(sweden / 'sfs2025-256_p0_1.pdf'))
        assert act.preface == ('Lag (2025:256) om ändring i lagen (2018:218) med kompletterande bestämmelser '
                               'till EU:s dataskyddsförordning')
        assert [(a['eId'], a['num'], a['parent']) for a in act.articles] == [
            ('art_6-8', '8 §', 'cpt_6'), ('art_7-3a', '3 a §', 'cpt_7'), ('art_7-6', '6 §', 'cpt_7')]
        amendment = act.articles[0]['children'][0]['amendment']
        assert amendment['action'] == 'insert'
        assert amendment['amended_act'] == ('lagen (2018:218) med kompletterande bestämmelser till EU:s '
                                            'dataskyddsförordning')
        assert amendment['instruction'].startswith('Enligt riksdagens beslut föreskrivs att det i lagen (2018:218)')
        quoted = amendment['quoted'][0]
        assert quoted['kind'] == 'structure'
        starts = ['Besked om handläggningen av ett klagomål', 'Om tillsynsmyndigheten inte inom tre månader',
                  'Tillsynsmyndigheten ska lämna ett besked', 'Om tillsynsmyndigheten har avslagit en begäran']
        assert len(quoted['children']) == len(starts)
        assert all(c['text'].startswith(start) for c, start in zip(quoted['children'], starts))
        # Only the first paragraph carries the amendment
        assert all(c['amendment'] is None for c in act.articles[0]['children'][1:])
        assert [c['text'] for c in act.annexes[0]['children']] == ['Denna lag träder i kraft den 1 maj 2025.']
        assert act.conclusions['signature'] == 'GUNNAR STRÖMMER David Brandell (Justitiedepartementet)'

    def test_amending_act_with_clauses(self, sweden):
        """'dels att ...': each section takes the action of the clause naming it."""
        act = SFSPDFParser().parse(str(sweden / 'sfs2026-1528_p0.pdf'))
        assert act.preface == 'Lag (2026:1528) om ändring i brottsbalken'
        assert act.formula.startswith('Enligt riksdagens beslut föreskrivs i fråga om brottsbalken dels att 32 kap. '
                                      '3 § ska upphöra att gälla, dels att nuvarande 32 kap. 3 a § ska betecknas')
        amendments = [(a['eId'], a['children'][0]['amendment']) for a in act.articles]
        assert [eid for eid, _ in amendments] == ['art_1-6', 'art_29-7']
        for _, amendment in amendments:
            assert amendment['action'] == 'replace'
            assert amendment['amended_act'] == 'brottsbalken'
            assert amendment['instruction'] == ('dels att 1 kap. 6 §, 29 kap. 7 §, 32 kap. 1 och 4 §§ och 38 kap. '
                                                '20 § ska ha följande lydelse.')

    def test_appendix(self, sweden):
        act = SFSPDFParser().parse(str(sweden / 'sfs2024-1333_p0_10_16.pdf'))
        assert act.preface == 'Förordning (2024:1333) med instruktion för Försvarsmakten'
        assert act.formula == 'Regeringen föreskriver följande.'
        assert act.articles[0]['heading'] == 'Uppgifter och ansvar Huvudsakliga uppgifter'
        annex = act.annexes[-1]
        assert (annex['eId'], annex['num']) == ('anx_3', 'Bilaga 3')
        assert annex['heading'] == ('Befattningar för vilka regeringen beslutar om placering efter förslag från '
                                    'Försvarsmakten')
        assert annex['children'][0]['text'] == 'Högkvarteret:'
        assert act.conclusions['conclusion_text'] == 'På regeringens vägnar'

    def test_not_an_act(self, tmp_path):
        path = tmp_path / 'empty.pdf'
        path.write_bytes(b'not a pdf')
        with pytest.raises(FileLoadError):
            SFSPDFParser().parse(str(path))


class TestSFSClient:
    def test_months(self):
        # The month of issue, then the next one
        assert _months(2018, '218', '2018-04-19')[:3] == [4, 5, 3]
        assert _months(2025, '256', None)[0] == 3
        assert sorted(_months(2025, '1654', None)) == list(range(1, 13))

    def test_pdf_url(self):
        assert pdf_url(2018, '218', 4) == ('https://svenskforfattningssamling.se/sites/default/files/sfs/'
                                           '2018-04/SFS2018-218.pdf')

    def test_download_finds_the_month(self, tmp_path):
        client = SFSClient(download_dir=str(tmp_path))

        def request(method, url, timeout):
            found = '/2018-05/' in url
            return Mock(status_code=200 if found else 404, content=b'%PDF-1.7 ...' if found else b'')

        with patch.object(client.session, 'request', side_effect=request) as calls:
            path, url = client.download(2018, '218', '2018-04-19')
        assert url == pdf_url(2018, '218', 5)
        assert [c.args[0] for c in calls.call_args_list] == ['HEAD', 'HEAD', 'GET']
        assert path.endswith('SFS2018-218.pdf')
        # A second download reads the file again
        with patch.object(client.session, 'request') as again:
            assert client.download(2018, '218') == (path, url)
        again.assert_not_called()

    def test_act_not_published(self, tmp_path):
        client = SFSClient(download_dir=str(tmp_path))
        with patch.object(client.session, 'request', return_value=Mock(status_code=404)):
            with pytest.raises(FileLoadError, match='no SFS 2099:1'):
                client.download(2099, '1')

    def test_server_error(self, tmp_path):
        client = SFSClient(download_dir=str(tmp_path))
        with patch.object(client.session, 'request', return_value=Mock(status_code=403)):
            with pytest.raises(NetworkError):
                client.download(2018, '218', '2018-04-19')


class TestSwedenOriginal:
    def test_fetch(self, sweden, tmp_path):
        pdf = str(sweden / 'sfs2018-218_p0_5_6.pdf')
        url = pdf_url(2018, '218', 4)
        with patch.object(RiksdagenClient, 'metadata', return_value={'datum': '2018-04-19 00:00:00'}), \
                patch.object(SFSClient, 'download', return_value=(pdf, url)) as download:
            doc = tulit.fetch('SFS 2018:218', jurisdiction='SE', download_dir=str(tmp_path))
        download.assert_called_once_with(2018, '218', '2018-04-19')
        meta = doc['meta']
        assert (meta['version'], meta['version_date'], meta['date_document'], meta['date_publication']) == (
            'original', '2018-04-24', '2018-04-19', '2018-04-24')
        assert meta['source'] == url
        assert doc['preface'] == 'Lag (2018:218) med kompletterande bestämmelser till EU:s dataskyddsförordning'

    def test_amending_act_unknown_to_the_riksdag(self, sweden, tmp_path):
        pdf = str(sweden / 'sfs2025-256_p0_1.pdf')
        with patch.object(RiksdagenClient, 'metadata', side_effect=FileLoadError('no statute')), \
                patch.object(SFSClient, 'download', return_value=(pdf, pdf_url(2025, '256', 3))) as download:
            doc = tulit.fetch('2025:256', jurisdiction='SE', version='original', download_dir=str(tmp_path))
        download.assert_called_once_with(2025, '256', None)
        assert sum(1 for a in doc['articles'] for c in a['children'] if c['amendment']) == 3

    @pytest.mark.parametrize('identifier', ['1974:152', 'SFS 2018:159'])
    def test_printed_acts(self, identifier, tmp_path):
        with pytest.raises(UnsupportedError, match='printed Svensk författningssamling'):
            tulit.fetch(identifier, jurisdiction='SE', download_dir=str(tmp_path))

    def test_date_is_rejected(self, tmp_path):
        with pytest.raises(UnsupportedError, match='consolidated'):
            tulit.fetch('2018:218', jurisdiction='SE', version='original', date='2020-01-01',
                        download_dir=str(tmp_path))
