"""Portugal: consolidated legislation of the Diário da República (Legislação Consolidada), with mocked HTTP."""
import json
from unittest.mock import Mock, patch

import pytest

import tulit
from tulit.client.state.portugal import PortugalConsolidatedClient, PortugalDREClient, consolidated_page
from tulit.parser.exceptions import FileLoadError, NetworkError, UnsupportedError
from tulit.parser.json.dre_consolidated import DREConsolidatedParser, number_token, text_lines
from tulit.quality import ERROR, check
from tulit.sources.pt import act_reference, code_page, not_in_force, version_date

DRE = 'https://diariodarepublica.pt'
CP_PAGE = f'{DRE}/dr/legislacao-consolidada/decreto-lei/1995-34437675'
L43_PAGE = f'{DRE}/dr/legislacao-consolidada/lei/2004-122101697'
CRP_PAGE = f'{DRE}/dr/legislacao-consolidada/decreto-aprovacao-constituicao/1976-34520775'
CODES = [
    {'DiplomaFrag': {'Designacao': 'Constituição da República Portuguesa - CRP', 'LinkSiteMap': CRP_PAGE[len(DRE):]}},
    {'DiplomaFrag': {'Designacao': 'Código Penal - CP', 'LinkSiteMap': CP_PAGE[len(DRE):]}},
    {'DiplomaFrag': {'Designacao': 'Código do Registo Predial - CRP',
                     'LinkSiteMap': '/dr/legislacao-consolidada/decreto-lei/1984-34544675'}},
    {'DiplomaFrag': {'Designacao': '', 'LinkSiteMap': ''}},
]


@pytest.fixture
def fixtures(data_root):
    return data_root / 'sources' / 'member_states' / 'portugal' / 'dre_consolidated'


def _response(data=None, url='', text=''):
    response = Mock(url=url, text=text)
    response.json.return_value = data
    response.raise_for_status.return_value = None
    return response


class FakeDRE:
    """The Diário da République as the client sees it: ELI redirects and screen services."""

    def __init__(self, fixtures):
        self.fixtures = fixtures
        self.headers, self.proxies = {}, {}
        self.calls: list[tuple[str, dict]] = []
        self.api_changed = False

    def _load(self, name):
        return json.loads((self.fixtures / f'{name}.json').read_text(encoding='utf-8'))

    def get(self, url, **kwargs):
        if url.endswith('moduleversioninfo'):
            return _response({'versionToken': 'module-token'})
        if url.endswith('.mvc.js'):
            return _response(text='callDataAction("DataActionGetData", "id", '
                                  '"screenservices/dr/LegislacaoConsolidada/LegCons_Detalhe/DataActionGetData", '
                                  '"new-api-version", function (b) {')
        pages = {'dec-lei/48/1995': CP_PAGE, 'lei/43/2004': L43_PAGE}
        for eli, page in pages.items():
            if f'eli/{eli}/p/cons/' in url:
                return _response(url=page)
        return _response(url=f'{DRE}/dr/error')

    def post(self, url, json=None, **kwargs):
        action = url.rsplit('/', 1)[1]
        variables = json['screenData']['variables']
        self.calls.append((action, variables))
        if action == 'DataActionGetCodigos':
            return _response({'versionInfo': {}, 'data': {'CodigosList': {'List': CODES}}})
        name = {'34437675': 'codigo_penal', '122101697': 'lei_43_2004',
                '34520775': 'constituicao'}[variables['DiplomaFragId']]
        if action == 'DataActionGetDiplomaFragByIdAndApplicationSetting':
            return _response(self._load(f'{name}_diploma'))
        if self.api_changed and json['versionInfo']['apiVersion'] != 'new-api-version':
            return _response({'versionInfo': {'hasModuleVersionChanged': False, 'hasApiVersionChanged': True},
                              'data': {}})
        if name == 'codigo_penal':
            # The consolidation published on 2026-08-19, and the one before it
            name += '_2026-08-20' if variables['DataSelecionada'] >= '2026-08-19' else '_2026-07-26'
        return _response(self._load(f'{name}_text'))


@pytest.fixture
def dre(fixtures):
    fake = FakeDRE(fixtures)
    with patch('tulit.client.state.portugal.requests.Session', return_value=fake):
        yield fake


@pytest.mark.parametrize('identifier, expected', [
    ('Lei n.º 7/2009', {'type': 'lei', 'number': '7', 'year': '2009', 'month': None, 'day': None}),
    ('Decreto-Lei n.º 48/95', {'type': 'dec-lei', 'number': '48', 'year': '1995', 'month': None}),
    ('Lei n.º 58/2019, de 8 de agosto', {'type': 'lei', 'month': '08', 'day': '08'}),
    ('https://data.dre.pt/eli/lei/7/2009/p/cons/20250327/pt/html',
     {'type': 'lei', 'number': '7', 'year': '2009', 'region': 'p', 'cons': '20250327', 'month': None}),
])
def test_act_reference(identifier, expected):
    parts = act_reference(identifier)
    assert {key: parts[key] for key in expected} == expected


def test_consolidated_page():
    assert consolidated_page(CP_PAGE + '-1160369275') == ('decreto-lei', '1995', '34437675')
    assert consolidated_page(f'{DRE}/dr/error') is None


def test_code_page():
    codes = [{'designation': c['DiplomaFrag']['Designacao'], 'page': c['DiplomaFrag']['LinkSiteMap']}
             for c in CODES if c['DiplomaFrag']['Designacao']]
    assert code_page('Código Penal', codes) == CP_PAGE[len(DRE):]
    assert code_page('codigo  penal', codes) == CP_PAGE[len(DRE):]
    assert code_page('CP', codes) == CP_PAGE[len(DRE):]
    assert code_page('Constituição da República Portuguesa', codes) == CRP_PAGE[len(DRE):]
    # Two codes share the acronym
    assert code_page('CRP', codes) is None
    assert code_page('Código Comercial', codes) is None


def test_version_dates():
    fragments = [{'FragmentoVersao': {'DataEntradaVigor': '2022-03-21T00:00:00Z', 'DataVersao': '2021-12-21'}},
                 {'FragmentoVersao': {'DataEntradaVigor': '2026-09-01T00:00:00Z', 'DataVersao': '2026-07-28'}},
                 {'FragmentoVersao': {'DataEntradaVigor': '1900-01-01T00:00:00', 'DataVersao': '2023-05-25'}}]
    assert version_date(fragments, '2026-08-20', '1995-03-15') == '2023-05-25'
    assert version_date(fragments, '2020-01-01', '1995-03-15') == '1995-03-15'
    assert not_in_force(fragments, '2026-08-20') == [fragments[1]]


@pytest.mark.parametrize('identification, token', [
    ('5.º', '5'), ('10.º-A', '10a'), ('374-B', '374b'), ('único', 'unico'), ('IV', 'IV'),
    ('Disposições finais e transitórias', None), ('', None),
])
def test_number_token(identification, token):
    assert number_token(identification) == token


def test_text_lines():
    assert text_lines('a) Quando <a href="x">91/533/CEE</a>;<br/>b) Contra &quot;x&quot;  \r\n\r\n') == [
        'a) Quando 91/533/CEE;', 'b) Contra "x"']
    # A link whose opening tag lost its '>' in the source
    assert text_lines('a Diretiva <a href="eurlex.asp?id=311L0096" title="Link para Directiva!�2011/96/CE</a>,'
                      ' do Conselho') == ['a Diretiva 2011/96/CE, do Conselho']


class TestConsolidated:
    def test_code_in_force_on_a_date(self, dre, tmp_path):
        """The consolidation of 2026-08-19 enters into force on 2026-08-24: on 2026-08-20 the one before applies."""
        doc = tulit.fetch('Código Penal', jurisdiction='PT', date='2026-08-20', download_dir=str(tmp_path))
        assert [variables['DataSelecionada'] for action, variables in dre.calls
                if action == 'DataActionGetData'] == ['2026-08-20', '2026-08-18']
        meta = doc['meta']
        assert (meta['version'], meta['version_date'], meta['in_force']) == ('consolidated', '2022-03-21', True)
        assert meta['source'] == CP_PAGE
        assert meta['eli'] == 'https://data.dre.pt/eli/dec-lei/48/1995/p/cons/20220321'
        assert doc['preface'] == 'Decreto-Lei n.º 48/95, de 15 de março - Código Penal - CP'
        assert not [p for p in check(doc) if p.severity == ERROR]

        assert [(c['eId'], c['type'], c['num'], c['heading'], c['parent']) for c in doc['chapters']] == [
            ('anx_1', 'annex', None, 'CÓDIGO PENAL', None),
            ('bok_I', 'book', 'Livro I', 'Parte geral', 'anx_1'),
            ('tit_I', 'title', 'Título I', 'Da lei criminal', 'bok_I'),
            ('cpt_unico', 'chapter', 'Capítulo único', 'Princípios gerais', 'tit_I'),
            ('bok_II', 'book', 'Livro II', 'Parte especial', 'anx_1'),
            ('tit_III', 'title', 'Título III', 'Dos crimes contra a identidade cultural e integridade pessoal',
             'bok_II')]
        articles = doc['articles']
        assert [(a['eId'], a['num'], a['parent']) for a in articles] == [
            ('art_1', 'Artigo 1.º', None), ('anx_1__art_1', 'Artigo 1.º', 'cpt_unico'),
            ('anx_1__art_5', 'Artigo 5.º', 'cpt_unico'), ('anx_1__art_236', 'Artigo 236.º', 'tit_III')]
        assert articles[1]['heading'] == 'Princípio da legalidade'
        assert [c['eId'] for c in articles[2]['children']] == ['par_1', 'par_2']
        assert articles[2]['children'][0]['text'].startswith('1 - Salvo tratado ou convenção internacional')
        # Points are folded into their paragraph
        assert ' a) Quando constituírem os crimes ' in articles[2]['children'][0]['text']
        assert articles[3]['children'] == [{'eId': 'unp_1', 'text': '(Revogado.)', 'amendment': None}]

        preamble = doc['preamble']
        assert preamble['formula'].endswith('o Governo decreta o seguinte:')
        recitals = [r['text'] for r in preamble['recitals']]
        assert recitals[0].startswith('1. A tendência cada vez mais universalizante')
        # The code's own preamble ('I - Introdução') follows the decree's
        assert 'I - Introdução (*)' in recitals
        assert doc['conclusions']['signature'] == 'O Primeiro-Ministro, Aníbal António Cavaco Silva.'

    def test_consolidated_eli_names_its_consolidation(self, dre, tmp_path):
        result = tulit.download('https://data.dre.pt/eli/dec-lei/48/1995/p/cons/20260819/pt/html',
                                download_dir=str(tmp_path))
        assert (result['jurisdiction'], result['version'], result['parser']) == (
            'PT', 'consolidated', 'pt-dre-consolidated')
        # Returned as the site has it, though one change enters into force later
        assert result['version_date'] == '2026-08-24'
        assert [v['DataSelecionada'] for a, v in dre.calls if a == 'DataActionGetData'] == ['2026-08-19']
        assert result['meta']['eli'] == 'https://data.dre.pt/eli/dec-lei/48/1995/p/cons/20260819'

    def test_law_with_annex_by_its_page(self, dre, tmp_path):
        doc = tulit.fetch(L43_PAGE, jurisdiction='PT', date='2020-01-01', download_dir=str(tmp_path))
        assert doc['meta']['version_date'] == '2019-08-09'
        assert doc['preface'] == ('Lei n.º 43/2004, de 18 de agosto - Lei de organização e funcionamento da '
                                  'Comissão Nacional de Protecção de Dados')
        assert [r['text'] for r in doc['preamble']['recitals']] == [
            'Lei de organização e funcionamento da Comissão Nacional de Protecção de Dados']
        assert [(a['eId'], a['heading']) for a in doc['articles']] == [('art_1', 'Âmbito'),
                                                                       ('art_19a', 'Fiscal único')]
        assert [(a['eId'], a['num'], a['heading']) for a in doc['annexes']] == [('anx_1', 'Anexo', 'MAPA I')]
        assert doc['annexes'][0]['children'][0]['text'] == '(a que se refere o n.º 1 do artigo 32.º)'
        assert not [p for p in check(doc) if p.severity == ERROR]

    def test_constitution_groups(self, dre, tmp_path):
        doc = tulit.fetch('Constituição da República Portuguesa', jurisdiction='PT', download_dir=str(tmp_path))
        assert [(c['eId'], c['type'], c['num'], c['heading'], c['parent']) for c in doc['chapters']] == [
            ('prt_1', 'part', None, 'Princípios fundamentais', None),
            ('prt_I', 'part', 'Parte I', 'Direitos e deveres fundamentais', None),
            ('tit_I', 'title', 'Título I', 'Princípios gerais', 'prt_I'),
            ('prt_IV', 'part', 'Parte IV', 'Garantia e revisão da Constituição', None),
            ('prt_4', 'part', None, 'Disposições finais e transitórias', 'prt_IV')]
        assert [a['parent'] for a in doc['articles']] == ['prt_1', 'tit_I', 'prt_4']
        assert doc['meta']['eli'] is None
        assert doc['preamble']['formula'].startswith('A Assembleia Constituinte, reunida na sessão plenária')

    def test_act_not_consolidated(self, dre, tmp_path):
        with pytest.raises(FileLoadError, match="no consolidated version of Lei n.º 58/2019.*version='original'"):
            tulit.fetch('Lei n.º 58/2019', jurisdiction='PT', version='consolidated', download_dir=str(tmp_path))

    def test_unknown_code(self, dre, tmp_path):
        with pytest.raises(UnsupportedError, match='name of a code'):
            tulit.fetch('Código Comercial', jurisdiction='PT', download_dir=str(tmp_path))

    def test_dates(self, dre, tmp_path):
        with pytest.raises(FileLoadError, match='published on 1995-03-15'):
            tulit.fetch('Código Penal', jurisdiction='PT', date='1990-01-01', download_dir=str(tmp_path))
        with pytest.raises(UnsupportedError, match='not an ISO date'):
            tulit.fetch('Código Penal', jurisdiction='PT', date='01/01/2021', download_dir=str(tmp_path))

    def test_original_of_a_reference_without_date(self, dre, tmp_path):
        """'Decreto-Lei n.º 48/95' as published: the date comes from its consolidated text."""
        with patch.object(PortugalDREClient, 'download', return_value=str(tmp_path / 'act.pdf')) as download:
            result = tulit.download('Decreto-Lei n.º 48/95', jurisdiction='PT', download_dir=str(tmp_path))
        assert download.call_args.kwargs == {'act_type': 'dec-lei', 'number': '48', 'year': '1995', 'month': '03',
                                             'day': '15', 'region': 'p', 'fmt': 'pdf'}
        assert (result['version'], result['version_date']) == ('original', '1995-03-15')
        assert result['meta']['eli'] == 'https://data.dre.pt/eli/dec-lei/48/1995/03/15/p'

    def test_original_needs_a_date(self, dre, tmp_path):
        with pytest.raises(UnsupportedError, match='has no date'):
            tulit.download('Lei n.º 58/2019', jurisdiction='PT', version='original', download_dir=str(tmp_path))
        with pytest.raises(UnsupportedError, match='a date selects a consolidated version'):
            tulit.download('Lei n.º 58/2019, de 8 de agosto', jurisdiction='PT', version='original',
                           date='2020-01-01', download_dir=str(tmp_path))


class TestClient:
    def test_reads_new_api_versions(self, dre, tmp_path):
        """After a redeployment the API version of a screen service is read again from its script."""
        dre.api_changed = True
        client = PortugalConsolidatedClient(download_dir=str(tmp_path))
        path = client.download('lei', '2004', '122101697', '2020-01-01')
        assert client._api['text'] == 'new-api-version'
        assert json.loads(open(path, encoding='utf-8').read())['page'] == L43_PAGE

    def test_server_exception(self, dre, tmp_path):
        client = PortugalConsolidatedClient(download_dir=str(tmp_path))
        failing = _response({'versionInfo': {}, 'data': {}, 'exception': {'message': 'Object reference not set'}})
        with patch.object(dre, 'post', return_value=failing):
            with pytest.raises(NetworkError, match='Object reference not set'):
                client.download('lei', '2004', '122101697', '2020-01-01')

    def test_unknown_act(self, dre, tmp_path):
        client = PortugalConsolidatedClient(download_dir=str(tmp_path))
        empty = _response({'versionInfo': {}, 'data': {'ConsolidadaConteudoDetalhe': {
            'DiplomaFrag': {'DiplomaLegisId': '0'}}}})
        with patch.object(dre, 'post', return_value=empty):
            with pytest.raises(FileLoadError, match='no consolidated act'):
                client.download('lei', '2019', '1', '2020-01-01')


def test_parser_reads_a_saved_document(fixtures, tmp_path):
    text = json.loads((fixtures / 'lei_43_2004_text.json').read_text(encoding='utf-8'))['data']
    diploma = json.loads((fixtures / 'lei_43_2004_diploma.json').read_text(encoding='utf-8'))['data']
    path = tmp_path / 'act.json'
    path.write_text(json.dumps({'diploma': diploma['ConsolidadaConteudoDetalhe'],
                                'fragments': text['LegConsBase']['List']}), encoding='utf-8')
    parser = DREConsolidatedParser().parse(str(path))
    assert parser.formula.startswith('A Assembleia da República decreta')
    assert parser.in_force is True
    assert parser.conclusions['signature'] == 'O Primeiro-Ministro, Pedro Miguel de Santana Lopes.'
    with pytest.raises(FileLoadError):
        DREConsolidatedParser().parse(str(tmp_path / 'missing.json'))
