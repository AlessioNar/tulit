import json
from unittest.mock import Mock, patch

import pytest

import tulit
from tulit.client.state.hungary import NJTClient
from tulit.parser.exceptions import FileLoadError
from tulit.parser.html.njt import NJTParser, amendment_action, roman
from tulit.sources.hu import eli_path


PAGE = '<html><head><meta charset="utf-8"></head><body><div id="jogszab">%s</div></body></html>'


@pytest.fixture
def hungary(data_root):
    return data_root / 'sources' / 'member_states' / 'hungary'


@pytest.mark.parametrize('citation, path', [
    ('2011. évi CXII. törvény', 'TV/2011/112'),
    ('2012. évi I. törvény a munka törvénykönyvéről', 'TV/2012/1'),
    ('335/2005. (XII. 29.) Korm. rendelet', 'R/2005/Korm/335'),
    ('21/2016. (X. 11.) IM rendelet', 'R/2016/IM/21'),
    ('1979. évi 13. törvényerejű rendelet', 'TVR/1979/13'),
    ('Alaptörvény', 'Alaptv'),
    ('Infotv.', None),
])
def test_eli_path(citation, path):
    assert eli_path(citation) == path


def test_roman():
    assert (roman('CXII'), roman('XIV'), roman('MMXXIV')) == (112, 14, 2024)


@pytest.mark.parametrize('instruction, action', [
    ('Az Adatvagyontv. 2. § (5) bekezdése helyébe a következő rendelkezés lép:', 'replace'),
    ('A 9. § (7) bekezdésében a „származó” szövegrész helyébe a „származó, talált” szöveg lép.', 'replace'),
    ('A Bvszr. a következő 78. §-sal egészül ki:', 'add'),
    ('Hatályát veszti a 2023. évi LXX. törvény 123. § (3) bekezdése.', 'delete'),
    ('Nem lép hatályba a 2023. évi LXX. törvény 12. §-a.', 'delete'),
    ('A Bvszr. 1. számú melléklete a 2. melléklet szerint módosul.', 'amend'),
    ('A bíróság a Hatóság határozatát hatályon kívül helyezi.', None),
])
def test_amendment_action(instruction, action):
    assert amendment_action(instruction) == action


class TestNJTParser:
    def test_law_as_promulgated(self, hungary):
        parser = NJTParser().parse(str(hungary / '2011-112-00-00.0.html'))
        assert parser.preface == ('2011. évi CXII. törvény az információs önrendelkezési jogról és az '
                                  'információszabadságról')
        assert parser.formula.endswith('az Alaptörvény VI. cikke alapján a következő törvényt alkotja:')
        assert (parser.promulgation_date, parser.adoption_date) == ('2011-07-26', '2011-07-11')
        assert [(c['eId'], c['num'], c['heading']) for c in parser.chapters[:2]] == [
            ('cpt_I', 'I. Fejezet', 'ÁLTALÁNOS RENDELKEZÉSEK'), ('sct_1', '1.', 'A törvény célja')]
        first = parser.articles[0]
        assert (first['eId'], first['num'], first['parent']) == ('art_1', '1. §', 'sct_1')
        # Footnote calls are left out of the text
        assert first['children'][0]['text'].startswith('E törvény célja az adatok kezelésére')
        assert parser.annexes[0]['heading'] == 'ÁLTALÁNOS KÖZZÉTÉTELI LISTA'
        assert parser.conclusions['signature'].startswith('Dr. Schmitt Pál s. k., köztársasági elnök')

    def test_amendments(self, hungary):
        parser = NJTParser().parse(str(hungary / '2011-112-00-00.0.html'))
        section = next(a for a in parser.articles if a['num'] == '89. §')
        first = section['children'][0]['amendment']
        assert first['action'] == 'replace'
        assert first['amended_act'] == ('A nemzeti adatvagyon körébe tartozó állami nyilvántartások fokozottabb '
                                        'védelméről szóló 2010. évi CLVII. törvény')
        assert first['quoted'][0]['text'].startswith('„(5) Törvény lehetővé teheti')
        # Words replaced in the running text
        words = next(a for a in parser.articles if a['num'] == '78. §')['children'][2]['amendment']
        assert [q['text'] for q in words['quoted']] == ['származó', 'származó talált']

    def test_amending_law(self, hungary):
        parser = NJTParser().parse(str(hungary / '2023-101-00-00.0.html'))
        # The act named in the instruction, through its abbreviation where one is defined
        amendment = parser.articles[0]['children'][0]['amendment']
        assert amendment['action'] == 'add'
        assert amendment['amended_act'].startswith('Az információs önrendelkezési jogról')
        assert amendment['quoted']
        assert parser.articles[-1]['children'][1]['amendment']['action'] == 'delete'

    def test_government_decree(self, hungary):
        parser = NJTParser().parse(str(hungary / '2005-335-20-22.55.html'))
        assert parser.formula.endswith('a Kormány a következőket rendeli el:')
        assert parser.in_force == '2026.10.01.'
        # Unnumbered headings become divisions of their own
        assert parser.chapters[1]['heading'] == 'A rendelet hatálya'
        annex = parser.annexes[0]
        assert annex['num'].startswith('1. melléklet a 335/2005. (XII. 29.) Korm. rendelethez')
        assert annex['heading'] == 'Az egységes kormányzati ügyiratkezelő rendszerbe bevont szervek'
        assert annex['children'][0]['text'] == '1. Miniszterelnökség'

    def test_amending_decree(self, hungary):
        parser = NJTParser().parse(str(hungary / '2016-21-20-06.0.html'))
        # Repealed sections stay as placeholders numbered by their range
        assert [a['eId'] for a in parser.articles][:2] == ['art_1', 'art_13']
        assert parser.articles[0]['num'] == '1–12. §'
        added = parser.articles[1]['children'][0]['amendment']
        assert added['action'] == 'add'
        # The act amended is named by the decree's title
        assert added['amended_act'] == 'a bírósági végrehajtás szervezetéről szóló 16/2001. (X. 26.) IM rendelet'

    def test_civil_code_books_and_section_titles(self, tmp_path):
        # Trimmed from the Polgári Törvénykönyv (2013. évi V. törvény)
        page = tmp_path / 'ptk.html'
        page.write_text(PAGE % '''
            <h1>2013. évi V. törvény</h1><h2>a Polgári Törvénykönyvről</h2>
            <div class="konyv">MÁSODIK KÖNYV</div><div class="konyvcim">AZ EMBER MINT JOGALANY</div>
            <div class="resz">ELSŐ RÉSZ</div><div class="reszcim">A JOGKÉPESSÉG</div>
            <div class="focim">I. CÍM</div><div class="focimCim">A JOGKÉPESSÉG KEZDETE</div>
            <span class="jhId" id="SZ2:1"></span><div class="szakasz">2:1. § [Jogképesség]</div>
            <span class="jhId" id="SZ2:1@BE1"></span><div class="bekezdesNyito">(1) Minden ember jogképes.</div>
            <span class="jhId" id="SZ2:1@BE2"></span>
            <div class="bekezdesNyito">(2) A végrendelet hatályát veszti, ha azt visszavonják.</div>''',
                        encoding='utf-8')
        parser = NJTParser().parse(str(page))
        assert [(c['eId'], c['type'], c['heading'], c['parent']) for c in parser.chapters] == [
            ('div_2', 'book', 'AZ EMBER MINT JOGALANY', None), ('prt_1', 'part', 'A JOGKÉPESSÉG', 'div_2'),
            ('tit_I', 'title', 'A JOGKÉPESSÉG KEZDETE', 'prt_1')]
        article = parser.articles[0]
        assert (article['eId'], article['num'], article['heading'], article['parent']) == (
            'art_2-1', '2:1. §', 'Jogképesség', 'tit_I')
        # A will that loses effect amends no legislation
        assert [c['amendment'] for c in article['children']] == [None, None]

    def test_fundamental_law(self, tmp_path):
        # Trimmed from Magyarország Alaptörvénye
        page = tmp_path / 'alaptv.html'
        page.write_text(PAGE % '''
            <h1>Magyarország Alaptörvénye</h1><h2></h2>
            <span class="jhId" id="PR"></span><div class="szoveg"><p>Isten, áldd meg a magyart!</p></div>
            <div class="alaptorvenyFejezet">NEMZETI HITVALLÁS</div><!-- -->
            <div class="szoveg"><p>MI, A MAGYAR NEMZET TAGJAI</p><p>Büszkék vagyunk.</p></div>
            <div class="alaptorvenyFejezet">ALAPVETÉS</div>
            <span class="jhId" id="CBA"></span><div class="cikkBetu">A) cikk</div>
            <div class="bekezdesNyito">HAZÁNK neve Magyarország.</div>
            <div class="alaptorvenyFejezet">SZABADSÁG ÉS FELELŐSSÉG</div>
            <span class="jhId" id="CRI"></span><div class="cikkRomai">I. cikk</div>
            <span class="jhId" id="CRI@BE1"></span><div class="bekezdesNyito">(1) Az ember jogai.</div>
            <span class="jhId" id="CRI@BE2"></span><div class="szelet">(2) A címer.</div>
            <div class="alaptorvenyFejezet">AZ ÁLLAM</div><div class="alaptorvenyFejezet">Az Országgyűlés</div>
            <span class="jhId" id="CA1"></span><div class="cikkArab">1. cikk</div>
            <div class="bekezdesNyito">Az Országgyűlés a legfelsőbb népképviseleti szerv.</div>
            <span class="jhId" id="RR1"></span><div class="szelet">*Mi, az Országgyűlés képviselői.</div>
            <span class="jhId" id="RR2"></span><div class="szelet">Kövér László s. k.</div>''', encoding='utf-8')
        parser = NJTParser().parse(str(page))
        assert parser.preface == 'Magyarország Alaptörvénye'
        assert [r['text'] for r in parser.recitals] == [
            'Isten, áldd meg a magyart!', 'MI, A MAGYAR NEMZET TAGJAI', 'Büszkék vagyunk.']
        assert [(c['eId'], c['type'], c['heading']) for c in parser.chapters] == [
            ('prt_1', 'part', 'ALAPVETÉS'), ('prt_2', 'part', 'SZABADSÁG ÉS FELELŐSSÉG'),
            ('prt_3', 'part', 'AZ ÁLLAM'), ('cpt_1', 'chapter', 'Az Országgyűlés')]
        assert [(a['eId'], a['num'], a['parent'], len(a['children'])) for a in parser.articles] == [
            ('art_A', 'A) cikk', 'prt_1', 1), ('art_I', 'I. cikk', 'prt_2', 2), ('art_1', '1. cikk', 'cpt_1', 1)]
        assert parser.conclusions['signature'] == 'Mi, az Országgyűlés képviselői. Kövér László s. k.'

    def test_page_without_act(self, tmp_path):
        page = tmp_path / 'page.html'
        page.write_text('<html><body><div id="kereso">Keresés</div></body></html>')
        with pytest.raises(FileLoadError, match='no act text'):
            NJTParser().parse(str(page))


class TestNJTClient:
    def test_versions_and_time_state(self, hungary, tmp_path):
        client = NJTClient(download_dir=str(tmp_path))
        data = json.loads((hungary / 'versions_2011-112-00-00.json').read_text())
        with patch.object(client.session, 'request', return_value=Mock(status_code=200, json=lambda: data)) as post:
            versions = client.versions('2011-112-00-00')
        assert post.call_args.kwargs['data'] == {'documentId': '2011-112-00-00'}
        assert versions[0] == {'version': 0, 'from': '2011-07-27', 'until': '2011-07-27'}
        # A time state whose coming into force is unknown is never in force
        assert client.in_force(versions, '2030-01-01')['version'] == 54
        assert client.in_force(versions, '2011-08-01')['version'] == 1
        assert client.in_force(versions, '2011-07-26') is None

    def test_resolve_eli(self, tmp_path):
        client = NJTClient(download_dir=str(tmp_path))
        redirected = Mock(status_code=200, url='https://njt.jog.gov.hu/jogszabaly/2011-112-00-00.0')
        with patch.object(client.session, 'request', return_value=redirected) as get:
            assert client.resolve('TV/2011/112/kozlony') == ('2011-112-00-00', '0')
        assert get.call_args.args[1] == 'https://njt.jog.gov.hu/eli/TV/2011/112/kozlony'

    def test_unknown_eli(self, tmp_path):
        client = NJTClient(download_dir=str(tmp_path))
        search = Mock(status_code=200, url='https://njt.jog.gov.hu/eli/kereses')
        with patch.object(client.session, 'request', return_value=search):
            with pytest.raises(FileLoadError, match='no act for the ELI'):
                client.resolve('R/2016/KORM/403')

    def test_lazy_blocks_are_filled(self, tmp_path):
        # A long act's page leaves its later sections in empty blocks the browser loads while scrolling
        client = NJTClient(download_dir=str(tmp_path))
        page = (PAGE % '''
            <span class="jhId" id="SZ1"></span><div class="szakasz">1. §</div>
            <div class="pH borderStart" data-show-order="10" data-b-n="1">
              <div class="pH" data-b-n="1"><span id="SZ2"></span></div>
              <div class="pH" data-b-n="1"><span id="SZ2@BE0"></span></div></div>''').encode('utf-8')
        block = ('<!--n-->\n<span class="jhId" id="SZ2"></span><div class="szakasz">2. §</div>'
                 '<span class="jhId" id="SZ2@BE0"></span><div class="bekezdesNyito">Második.</div>').encode('utf-8')
        responses = [Mock(status_code=200, content=page), Mock(status_code=200, content=block)]
        with patch.object(client.session, 'request', side_effect=responses) as request:
            path = client.download('2013-5-00-00', 0)
        assert request.call_args.kwargs['json'] == {'documentId': '2013-5-00-00.0', 'data': [{'start': 10}]}
        parser = NJTParser().parse(path)
        assert [(a['num'], [c['text'] for c in a['children']]) for a in parser.articles] == [
            ('1. §', []), ('2. §', ['Második.'])]

    def test_eli_of_page(self, hungary):
        assert NJTClient.eli(str(hungary / '2005-335-20-22.55.html')) == 'https://njt.jog.gov.hu/eli/R/2005/Korm/335'


class TestHungarySource:
    def test_original(self, hungary, tmp_path):
        with patch.object(NJTClient, 'resolve', return_value=('2011-112-00-00', None)) as resolve, \
                patch.object(NJTClient, 'download', return_value=str(hungary / '2011-112-00-00.0.html')) as download:
            doc = tulit.fetch('2011. évi CXII. törvény', jurisdiction='HU', download_dir=str(tmp_path))
        resolve.assert_called_once_with('TV/2011/112')
        download.assert_called_once_with('2011-112-00-00', 0)
        meta = doc['meta']
        assert (meta['jurisdiction'], meta['version'], meta['language'], meta['version_date']) == (
            'HU', 'original', 'hun', '2011-07-26')
        assert (meta['date_document'], meta['eli'], meta['njt_id']) == (
            '2011-07-11', 'https://njt.jog.gov.hu/eli/TV/2011/112', '2011-112-00-00')

    def test_consolidated_on_a_date(self, hungary, tmp_path):
        versions = [{'version': 0, 'from': '2011-07-27', 'until': '2011-07-27'},
                    {'version': 1, 'from': '2011-07-27', 'until': '2012-01-01'},
                    {'version': 2, 'from': '2012-01-01', 'until': None}]
        with patch.object(NJTClient, 'versions', return_value=versions), \
                patch.object(NJTClient, 'download', return_value=str(hungary / '2011-112-00-00.0.html')) as download:
            doc = tulit.fetch('https://njt.jog.gov.hu/jogszabaly/2011-112-00-00', version='consolidated',
                              date='2011-09-01', download_dir=str(tmp_path))
        download.assert_called_once_with('2011-112-00-00', 1)
        assert (doc['meta']['jurisdiction'], doc['meta']['version_date']) == ('HU', '2011-07-27')

    def test_date_before_entry_into_force(self, tmp_path):
        versions = [{'version': 1, 'from': '2011-07-27', 'until': None}]
        with patch.object(NJTClient, 'versions', return_value=versions):
            with pytest.raises(FileLoadError, match='first came into force on 2011-07-27'):
                tulit.fetch('2011-112-00-00', jurisdiction='HU', version='consolidated', date='2010-01-01',
                            download_dir=str(tmp_path))

    def test_decree_date_from_citation(self, hungary, tmp_path):
        with patch.object(NJTClient, 'resolve', return_value=('2016-21-20-06', None)), \
                patch.object(NJTClient, 'download', return_value=str(hungary / '2016-21-20-06.0.html')):
            doc = tulit.fetch('21/2016. (X. 11.) IM rendelet', jurisdiction='HU', download_dir=str(tmp_path))
        assert doc['meta']['version_date'] == '2016-10-11'

    def test_bad_identifier(self, tmp_path):
        with pytest.raises(ValueError, match='not a Hungarian act reference'):
            tulit.fetch('Infotv.', jurisdiction='HU', download_dir=str(tmp_path))
