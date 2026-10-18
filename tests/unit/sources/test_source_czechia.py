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

    @staticmethod
    def _parse(tmp_path, *fragments):
        """Parse fragments given as (kind, depth, anchor, xhtml)."""
        path = tmp_path / 'act.json'
        path.write_text(json.dumps({'metadata': {}, 'fragments': [
            {'kodTypuFragmentu': kind, 'hloubka': depth, 'staleUrl': f'/sb/1993/1/1993-01-01#{anchor}',
             'xhtml': xhtml} for kind, depth, anchor, xhtml in fragments]}), encoding='utf-8')
        return EsbirkaParser().parse(str(path))

    def test_constitution_title_and_preamble(self, tmp_path):
        parser = self._parse(
            tmp_path,
            ('Prefix_Type', 2, '', 'ÚSTAVNÍ ZÁKON'), ('Prefix_Author', 2, '', 'České národní rady'),
            ('Prefix_Date', 2, '', 'ze dne 16. prosince 1992'),
            # No title fragment: the title and the date again are prefixes
            ('Prefix', 2, '', 'ÚSTAVA ČESKÉ REPUBLIKY'), ('Prefix', 2, '', 'ze dne 16. prosince 1992'),
            ('Preambule', 2, '', 'Česká národní rada se usnesla na tomto ústavním zákoně:'),
            ('Preambule', 2, '', 'PREAMBULE'),
            ('Preambule', 2, '', 'My, občané České republiky v Čechách, na Moravě a ve Slezsku,'),
            ('Clanek', 3, 'cl_1', 'Čl. 1'), ('Odstavec_Dc', 4, 'cl_1', 'Česká republika je právní stát.'))
        assert parser.preface == 'ÚSTAVNÍ ZÁKON České národní rady ze dne 16. prosince 1992 ÚSTAVA ČESKÉ REPUBLIKY'
        assert parser.formula == 'Česká národní rada se usnesla na tomto ústavním zákoně:'
        assert [r['text'] for r in parser.recitals] == [
            'My, občané České republiky v Čechách, na Moravě a ve Slezsku,']

    def test_preamble_before_the_formula(self, tmp_path):
        # Zákon o rodině (94/1963 Sb.): the formula is cut short by the source
        parser = self._parse(
            tmp_path, ('Prefix_Type', 2, '', 'Zákon o rodině'), ('Prefix_Date', 2, '', 'ze dne 4. prosince 1963'),
            ('Prefix', 2, '', 'Rodina je základem společnosti.'),
            ('Prefix', 2, '', 'Aby tyto zásady byly vyjádřeny, usneslo se Národní shromáždění na tomto'),
            ('Clanek', 3, 'cl_1', 'Článek I'), ('Odstavec_Dc', 4, 'cl_1', 'Manželství spočívá na citech.'))
        assert parser.preface == 'Zákon o rodině ze dne 4. prosince 1963'
        assert parser.formula.startswith('Aby tyto zásady')
        assert [r['text'] for r in parser.recitals] == ['Rodina je základem společnosti.']

    def test_annexes(self, tmp_path):
        table = ('<table><tbody><tr><th>Třída<br/>práce</th><th>M</th></tr>'
                 '<tr><td>I</td><td>80</td></tr></tbody></table>')
        parser = self._parse(
            tmp_path, ('Prefix_Type', 2, '', 'NAŘÍZENÍ VLÁDY'),
            ('Paragraf', 3, 'par_1', '§ 1'), ('Odstavec_Dc', 4, 'par_1', 'Text.'),
            ('Postfix', 2, '', 'Topolánek v. r.'), ('Virtual_Prilohy', 1, '', ''),
            ('Block_Priloha', 2, '', ''), ('Hlavicka_priloha', 3, 'pril_1', 'Příloha č. 1 k nařízení vlády'),
            ('Nadpis_nad', 4, 'pril_1', 'Třídy práce'), ('Cast', 4, 'pril_1-cast_A', 'Část A'),
            ('Tabulka', 5, 'pril_1-cast_A', table),
            ('Block_Priloha_Rozvolnena', 2, '', ''), ('Hlavicka_priloha', 3, 'pril_2', 'Příloha č. 2'),
            ('Obecny_text', 4, 'pril_2', 'Dosahy končetin'), ('PPC', 2, 'ppc_1', '¹) Směrnice Rady 89/391/EHS.'))
        # Parts of an annex are not divisions of the act
        assert parser.chapters == []
        assert [a['num'] for a in parser.articles] == ['§ 1']
        first, second = parser.annexes
        assert (first['eId'], first['num'], first['heading']) == (
            'anx_1', 'Příloha č. 1 k nařízení vlády', 'Třídy práce')
        assert [c['text'] for c in first['children']] == ['Část A', 'Třída práce M', 'I 80']
        assert [c['text'] for c in second['children']] == ['Dosahy končetin']

    def test_act_promulgated_as_an_annex(self, tmp_path):
        # The Charter of Fundamental Rights (2/1993 Sb.) is the annex of a resolution
        parser = self._parse(
            tmp_path, ('Prefix_Type', 2, '', 'USNESENÍ'), ('Prefix', 2, '', 'Předsednictvo se usneslo takto:'),
            ('Odstavec_Dc', 2, '', 'Předsednictvo vyhlašuje LISTINU.'), ('Postfix', 2, '', 'Uhde v. r.'),
            ('Block_Priloha_Norma', 2, '', ''), ('Preambule', 3, '', 'Federální shromáždění,'),
            ('Hlava', 3, 'prilohy-hlava_1', 'HLAVA PRVNÍ'),
            ('Clanek', 4, 'prilohy-cl_1', 'Čl. 1'), ('Odstavec_Dc', 5, 'prilohy-cl_1', 'Lidé jsou svobodní.'))
        assert parser.annexes == []
        assert [(c['num'], a['num']) for c, a in zip(parser.chapters, parser.articles)] == [('HLAVA PRVNÍ', 'Čl. 1')]
        assert [r['text'] for r in parser.recitals] == ['Federální shromáždění,']

    def test_communication_without_paragraphs(self, tmp_path):
        parser = self._parse(
            tmp_path, ('Prefix_Type', 2, '', 'SDĚLENÍ'), ('Prefix_Author', 2, '', 'Českého statistického úřadu'),
            ('Prefix_Title', 2, '', 'o aktualizaci Klasifikace zaměstnání'),
            ('Prosty_Text', 2, '', 'Český statistický úřad sděluje aktualizaci.'),
            ('Prosty_Text', 2, '', 'Platné znění je na internetu.'),
            ('Postfix_Head', 2, '', 'Předseda:'), ('Postfix', 2, '', 'Ing. Rojíček, Ph.D., v. r.'))
        assert parser.preface == 'SDĚLENÍ Českého statistického úřadu o aktualizaci Klasifikace zaměstnání'
        article, = parser.articles
        assert (article['num'], [c['text'] for c in article['children']]) == (
            None, ['Český statistický úřad sděluje aktualizaci.', 'Platné znění je na internetu.'])
        assert parser.conclusions['signature'] == 'Předseda: Ing. Rojíček, Ph.D., v. r.'

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
        assert (meta['version'], meta['version_date'], meta['date_document']) == (
            'original', '2019-04-24', '2019-04-24')
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

    def test_published_without_versions(self, czechia, tmp_path):
        # A communication on a treaty: in effect before it was published, and without versions
        notice = {'staleUrl': '/sb/2026/20/0000-00-00', 'typZneni': 'VYHLASENE', 'datumUcinnostiOd': '2025-11-05',
                  'datumUcinnostiZneniOd': '2026-02-16', 'datumCasVyhlaseni': '2026-02-16T12:14:41.227+01:00'}
        with patch.object(EsbirkaClient, 'metadata', side_effect=lambda path: {'/sb/2026/20': notice}[path]), \
                patch.object(EsbirkaClient, 'download',
                             return_value=str(czechia / 'sb_2019_110_2025-08-01.json')) as download:
            doc = tulit.fetch('20/2026 Sb.', jurisdiction='CZ', download_dir=str(tmp_path))
        download.assert_called_once_with('/sb/2026/20/0000-00-00')
        assert (doc['meta']['version'], doc['meta']['version_date']) == ('original', '2026-02-16')


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
