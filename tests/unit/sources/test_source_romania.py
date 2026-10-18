from unittest.mock import Mock, patch

import pytest
from lxml import etree

import tulit
from tulit.client.state.romania import NS, PortalLegislativClient, fold, iso_date
from tulit.parser.exceptions import FileLoadError
from tulit.parser.xml.legislatie_ro import LegislatieParser, amendment_action
from tulit.sources.ro import act_reference

TOKEN = ('<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body>'
         '<GetTokenResponse xmlns="http://tempuri.org/"><GetTokenResult>ABC123</GetTokenResult></GetTokenResponse>'
         '</s:Body></s:Envelope>')


def search_answer(*records: bytes) -> bytes:
    items = b''.join(records)
    return (b'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body>'
            b'<SearchResponse xmlns="http://tempuri.org/"><SearchResult xmlns:a="' + NS.encode() + b'">'
            + items + b'</SearchResult></SearchResponse></s:Body></s:Envelope>')


@pytest.fixture
def romania(data_root):
    return data_root / 'sources' / 'member_states' / 'romania'


@pytest.mark.parametrize('identifier, expected', [
    ('Legea nr. 190/2018', ('LEGE', '190', '2018')),
    ('Legea 190/2018', ('LEGE', '190', '2018')),
    ('OUG nr. 57/2019', ('ORDONANȚĂ DE URGENȚĂ', '57', '2019')),
    ('Ordonanța de urgență a Guvernului nr. 57/2019', ('ORDONANȚĂ DE URGENȚĂ', '57', '2019')),
    ('Ordonanţa nr. 1/2016', ('ORDONANȚĂ', '1', '2016')),
    ('O.G. nr. 1/2016', ('ORDONANȚĂ', '1', '2016')),
    ('HG nr. 677 din 21 septembrie 2017', ('HOTĂRÂRE', '677', '2017')),
    ('Hotărârea Guvernului nr. 677/2017', ('HOTĂRÂRE', '677', '2017')),
    ('Constituția', ('CONSTITUȚIE', '0', '1991')),
    ('Constituţia din 1923', ('CONSTITUȚIE', '0', '1923')),
])
def test_act_reference(identifier, expected):
    assert act_reference(identifier) == expected


@pytest.mark.parametrize('identifier', ['190/2018', 'Regulamentul nr. 190/2018', 'Legea privind datele'])
def test_act_reference_rejects(identifier):
    with pytest.raises(ValueError):
        act_reference(identifier)


@pytest.mark.parametrize('instruction, action', [
    ('La articolul 1, alineatul (3) se modifică și va avea următorul cuprins:', 'replace'),
    ('La articolul 1, după alineatul (3) se introduce un nou alineat, alineatul (3^1), cu următorul cuprins:',
     'insert'),
    ('Articolul 13 se abrogă.', 'delete'),
    ('Legea nr. 102/2005 ... se modifică și se completează după cum urmează:', 'amend'),
    ('Prezenta lege intră în vigoare la 5 zile de la data publicării.', None),
])
def test_amendment_action(instruction, action):
    assert amendment_action(instruction) == action


def test_iso_date_and_fold():
    assert iso_date('LEGE nr. 190 din 18 iulie 2018') == '2018-07-18'
    assert fold('Ordonanţă de urgenţă') == 'ORDONANȚĂ DE URGENȚĂ'


class TestLegislatieParser:
    def test_law(self, romania):
        parser = LegislatieParser().parse(str(romania / 'lege_190_2018.xml'))
        assert parser.preface.startswith('LEGE nr. 190 din 18 iulie 2018 privind măsuri de punere în aplicare')
        assert parser.recitals_init == ('EMITENT PARLAMENTUL ROMÂNIEI Publicat în '
                                        'MONITORUL OFICIAL nr. 651 din 26 iulie 2018')
        assert parser.formula == 'Parlamentul României adoptă prezenta lege.'
        assert [(c['eId'], c['num'], c['heading']) for c in parser.chapters[:2]] == [
            ('cpt_I', 'Capitolul I', 'Dispoziții generale'),
            ('cpt_II', 'Capitolul II', 'Reguli speciale privind prelucrarea unor categorii de date cu caracter '
                                       'personal')]
        assert len(parser.articles) == 16
        # The title printed above an article is its heading
        first, second = parser.articles[:2]
        assert (first['num'], first['heading'], first['parent']) == ('Articolul 1', 'Obiectul legii', 'cpt_I')
        assert second['heading'] == 'Definiții'
        assert [c['eId'] for c in second['children']] == ['par_1', 'par_2']
        assert ' b) număr de identificare național' in second['children'][0]['text']
        # Article 15 amends another law, whose article it quotes in full
        quoting = parser.articles[14]['children'][0]['amendment']
        assert (quoting['action'], quoting['amended_act']) == ('replace', 'Legea nr. 102/2005')
        assert quoting['quoted'][0]['text'] == 'Articolul 14^2'
        assert parser.articles[15]['num'] == 'Articolul 16'
        assert parser.annexes[0]['heading'] == 'Plan de remediere'
        assert parser.conclusions['conclusion_text'].startswith('Această lege a fost adoptată de Parlamentul')
        assert parser.conclusions['signature'].endswith('București, 18 iulie 2018. Nr. 190.')

    def test_amending_law(self, romania):
        parser = LegislatieParser().parse(str(romania / 'lege_129_2018.xml'))
        assert [a['num'] for a in parser.articles] == [f'Articolul {n}' for n in
                                                       ('I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX')]
        # The quoted chapters and articles stay inside the amending article
        assert parser.chapters == []
        points = parser.articles[0]['children']
        assert points[0]['amendment']['action'] == 'amend'
        replace = points[1]['amendment']
        assert (replace['action'], replace['amended_act']) == ('replace', 'Legea nr. 102/2005')
        assert replace['quoted'][0]['text'].startswith('(3) Atribuțiile Autorității naționale de supraveghere')
        assert points[10]['text'] == '10. Articolul 13 se abrogă.'
        assert points[10]['amendment']['action'] == 'delete'
        chapters = points[11]['amendment']
        assert chapters['action'] == 'insert'
        assert chapters['quoted'][0]['text'] == 'Capitolul III^1'
        abrogation = parser.articles[4]['children'][0]['amendment']
        assert (abrogation['action'], abrogation['amended_act']) == ('delete', 'Legea nr. 677/2001')

    def test_older_ordinance(self, romania):
        parser = LegislatieParser().parse(str(romania / 'ordonanta_1_2016.xml'))
        # Considerations and formula share one paragraph in older texts
        assert parser.formula == 'Guvernul României adoptă prezenta ordonanţă.'
        assert parser.recitals[0]['text'].startswith('Din necesitatea de a facilita accesul')
        article = parser.articles[0]
        assert (article['eId'], article['num']) == ('art_1', 'Articol unic')
        points = article['children']
        assert [p['amendment']['action'] for p in points] == ['amend', 'insert', 'replace', 'replace']
        assert [len(p['amendment']['quoted']) for p in points[1:]] == [2, 1, 1]
        assert points[3]['amendment']['quoted'][0]['text'].startswith('Art. 36. - (1) Comunicările')
        assert parser.conclusions['signature'].startswith('PRIM-MINISTRU DACIAN JULIEN CIOLOŞ')

    def test_decision(self, romania):
        parser = LegislatieParser().parse(str(romania / 'hotarare_677_2017.xml'))
        assert parser.formula == 'Guvernul României adoptă prezenta hotărâre.'
        assert [r['text'][:20] for r in parser.recitals] == ['Având în vedere Acor', 'în temeiul art. 108 ']
        assert parser.articles[0]['num'] == 'Articol unic'
        assert [c['eId'] for c in parser.articles[0]['children']] == ['par_1', 'par_2']
        assert parser.annexes[0]['num'] == 'ANEXĂ'

    def test_code_layout_glitches(self, tmp_path):
        # Trimmed from the Codul penal and Codul civil: an editor's note, the table of contents after a
        # part's heading, an article run into a section's heading, and a heading-like paragraph ending ':'
        sep = '\n\t\t\t\t\xa0+\xa0\n\t\t\t  '
        text = sep.join([
            ' LEGE nr. 286 din 17 iulie 2009  privind Codul penal     EMITENT     PARLAMENTUL       Publicat în'
            '\xa0\n\t\t\t  MONITORUL OFICIAL nr. 510 din 24 iulie 2009     ----------  NOTĂ C.T.C.E. S.A.:  '
            'Potrivit art. 446 din prezentul cod:  "(1) Prezentul cod intră în vigoare."  ',
            'Partea GENERALĂ     \n\t\t\t\t  Titlul I - Legea penală  art. 1-2    ',
            'Partea GENERALĂ     ',
            'Articolul 1      Legalitatea   (1) Legea penală prevede faptele.    (2) Dacă s-au stabilit mai multe '
            'pedepse de acelaşi conţinut:  \xa0...\xa0    a) se aplică una.  ',
            'Capitolul VI   Autorul',
            'Articolul 2      Autorul   Autor este persoana care săvârșește fapta, „direct“.  ',
            'Secţiunea a 3-a   Cecul   ART 3  Legea aplicabilă  Legea statului unde cecul este plătibil.   ',
        ])
        record = tmp_path / 'code.xml'
        record.write_text(f'<a:Legi xmlns:a="{NS}"><a:Text>{text}</a:Text></a:Legi>', encoding='utf-8')
        parser = LegislatieParser().parse(str(record))
        assert parser.recitals == []
        assert [(c['num'], c['heading'], c['parent']) for c in parser.chapters] == [
            ('Partea GENERALĂ', None, None), ('Capitolul VI', 'Autorul', 'prt_GENERALĂ'),
            ('Secţiunea a 3-a', 'Cecul', 'cpt_VI')]
        assert [(a['num'], a['heading'], a['parent']) for a in parser.articles] == [
            ('Articolul 1', 'Legalitatea', 'prt_GENERALĂ'), ('Articolul 2', 'Autorul', 'cpt_VI'),
            ('Articolul 3', 'Legea aplicabilă', 'sct_3')]
        assert parser.articles[2]['children'][0]['text'] == 'Legea statului unde cecul este plătibil.'

    def test_record_without_text(self, tmp_path):
        record = tmp_path / 'empty.xml'
        record.write_text(f'<a:Legi xmlns:a="{NS}"><a:Text></a:Text></a:Legi>')
        with pytest.raises(FileLoadError, match='no act text'):
            LegislatieParser().parse(str(record))


class TestPortalLegislativClient:
    def test_find_matches_type_number_and_year(self, romania, tmp_path):
        law = etree.tostring(etree.parse(str(romania / 'lege_190_2018.xml')).getroot())
        decree = (f'<a:Legi xmlns:a="{NS}"><a:TipAct>DECRET</a:TipAct><a:Titlu> DECRET nr. 190 din 1 februarie '
                  f'2018 pentru numirea unui procuror</a:Titlu></a:Legi>').encode('utf-8')
        client = PortalLegislativClient(download_dir=str(tmp_path))
        answers = [Mock(status_code=200, content=TOKEN.encode()),
                   Mock(status_code=200, content=search_answer(decree, law))]
        with patch.object(client.session, 'post', side_effect=answers) as post:
            path = client.download('LEGE', '190', '2018')
        sent = post.call_args_list[1].kwargs['data'].decode('utf-8')
        assert '<a:SearchAn>2018</a:SearchAn>' in sent and '<a:SearchNumar>190</a:SearchNumar>' in sent
        assert '<tokenKey>ABC123</tokenKey>' in sent
        assert path.endswith('lege_190_2018.xml')
        assert LegislatieParser().parse(path).preface.startswith('LEGE nr. 190')

    def test_not_found(self, tmp_path):
        client = PortalLegislativClient(download_dir=str(tmp_path))
        answers = [Mock(status_code=200, content=TOKEN.encode()), Mock(status_code=200, content=search_answer())]
        with patch.object(client.session, 'post', side_effect=answers):
            with pytest.raises(FileLoadError, match='no LEGE nr. 999/2018'):
                client.find('LEGE', '999', '2018')

    def test_metadata(self, romania):
        meta = PortalLegislativClient.metadata(str(romania / 'lege_190_2018.xml'))
        assert (meta['type'], meta['issuer']) == ('LEGE', 'Parlamentul')
        assert (meta['date_document'], meta['date_publication'], meta['date_in_force']) == (
            '2018-07-18', '2018-07-26', '2018-07-31')
        assert meta['publication'] == 'Monitorul Oficial nr. 651 din 26 iulie 2018'
        assert meta['source'] == 'https://legislatie.just.ro/Public/DetaliiDocument/203151'


class TestRomaniaSource:
    def test_fetch(self, romania, tmp_path):
        with patch.object(PortalLegislativClient, 'download',
                          return_value=str(romania / 'lege_190_2018.xml')) as download:
            doc = tulit.fetch('Legea nr. 190/2018', jurisdiction='RO', download_dir=str(tmp_path))
        download.assert_called_once_with('LEGE', '190', '2018', title='')
        meta = doc['meta']
        assert (meta['jurisdiction'], meta['version'], meta['language'], meta['version_date']) == (
            'RO', 'original', 'ron', '2018-07-18')
        assert meta['source'] == 'https://legislatie.just.ro/Public/DetaliiDocument/203151'
        assert len(doc['articles']) == 16

    def test_no_consolidated_version(self, tmp_path):
        with pytest.raises(ValueError, match='does not publish the consolidated version'):
            tulit.fetch('Legea nr. 190/2018', jurisdiction='RO', version='consolidated', download_dir=str(tmp_path))
