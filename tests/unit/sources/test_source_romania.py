import json
from unittest.mock import Mock, patch

import pytest
import requests
from lxml import etree

import tulit
from tulit.client.state.romania import (NS, PORTAL, PortalLegislativClient, act_forms, fold, iso_date,
                                        shown_form)
from tulit.parser.exceptions import FileLoadError, NetworkError, UnsupportedError
from tulit.parser.html.legislatie_ro import LegislatieHtmlParser, clean
from tulit.parser.xml.legislatie_ro import LegislatieParser, amendment_action
from tulit.quality import ERROR, check
from tulit.sources.ro import RomaniaSource, act_reference, choose_form

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
    ('Codul civil', ('CODUL CIVIL', '0', '2009')),
    ('Codul penal', ('CODUL PENAL', '0', '2009')),
    ('Codul de procedură penală', ('CODUL DE PROCEDURĂ PENALĂ', '0', '2010')),
    ('Codul muncii', ('LEGE', '53', '2003')),
    ('Codul administrativ', ('ORDONANȚĂ DE URGENȚĂ', '57', '2019')),
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

    def test_original_takes_no_date(self, tmp_path):
        with pytest.raises(UnsupportedError, match='selects a consolidated version'):
            tulit.fetch('Legea nr. 190/2018', jurisdiction='RO', date='2020-01-01', download_dir=str(tmp_path))


# Consolidated forms, from the portal's pages (trimmed copies of the official pages)

def soap_record(tmp_path, document, kind, title, in_force):
    """A record of the web service, as ``PortalLegislativClient.download`` saves it."""
    path = tmp_path / f'record_{document}.xml'
    path.write_text(f'<a:Legi xmlns:a="{NS}"><a:DataVigoare>{in_force}</a:DataVigoare><a:Emitent>Parlamentul'
                    f'</a:Emitent><a:LinkHtml>http://legislatie.just.ro/Public/DetaliiDocument/{document}</a:LinkHtml>'
                    f'<a:TipAct>{kind}</a:TipAct><a:Titlu>{title}</a:Titlu><a:Text>...</a:Text></a:Legi>',
                    encoding='utf-8')
    return str(path)


@pytest.fixture
def companies_law(tmp_path):
    """Law 31/1990 on companies: its record in the web service (document 798)."""
    return soap_record(tmp_path, '798', 'LEGE', 'LEGE nr. 31 din 16 noiembrie 1990 privind societăţile comerciale '
                       'EMITENT: PARLAMENTUL PUBLICAT ÎN: MONITORUL OFICIAL NR. 126-127 din 17 noiembrie 1990',
                       '1990-11-17')


def pages(romania, **by_id):
    """A stand-in for ``download_page``: the fixture page of each document id."""
    def download_page(url):
        document = url.rsplit('/', 1)[1]
        if document not in by_id:
            raise AssertionError(f'unexpected page {url}')
        return str(romania / by_id[document])
    return download_page


class TestForms:
    def test_act_forms(self, romania):
        page = (romania / 'pagina_798.html').read_text(encoding='utf-8')
        forms = act_forms(page)
        assert len(forms) == 45
        # The form the page shows has no link: its id is the page's own
        assert shown_form(page) == '304533'
        assert forms[0] == {'date': '2025-12-18', 'kind': 'consolidation', 'id': '304533',
                            'url': f'{PORTAL}/304533'}
        assert forms[1]['id'] == '291512'
        republication = [form for form in forms if form['kind'] == 'republication']
        assert [(form['date'], form['url']) for form in republication] == [
            ('2004-11-17', f'{PORTAL}/56732?isFormaDeBaza=True'), ('1998-01-29', f'{PORTAL}/800?isFormaDeBaza=True')]

    @pytest.mark.parametrize('date, expected', [
        ('2026-10-18', '304533'), ('2025-12-18', '304533'), ('2025-12-17', '291512'),
        ('2016-01-01', '169688'), ('1998-02-01', '800'), ('1991-06-04', '221405'), ('1991-01-01', None),
    ])
    def test_choose_form(self, romania, date, expected):
        forms = act_forms((romania / 'pagina_798.html').read_text(encoding='utf-8'))
        chosen = choose_form(forms, date)
        assert (chosen['id'] if chosen else None) == expected

    def test_page_without_forms(self, romania):
        # An act never amended: the page lists no form and shows the act as published
        assert act_forms((romania / 'pagina_29843.html').read_text(encoding='utf-8')) == []


class TestLegislatieHtmlParser:
    def test_consolidated_law(self, romania):
        parser = LegislatieHtmlParser().parse(str(romania / 'pagina_798.html'))
        assert parser.preface == 'LEGE nr. 31 din 16 noiembrie 1990 (republicată) privind societățile'
        assert [(c['eId'], c['num'], c['heading'], c['parent']) for c in parser.chapters] == [
            ('tit_I', 'Titlul I', 'Dispoziții generale', None),
            ('tit_III', 'Titlul III', 'Funcționarea societăților', None),
            ('cpt_IV', 'Capitolul IV', 'Societățile pe acțiuni', 'tit_III'),
            ('sct_III', 'Secţiunea a III-a', 'Despre administrația societății', 'cpt_IV'),
            # A lettered paragraph of a section heads articles
            ('sbs_A', 'A.', 'Directoratul', 'sct_III'),
            ('tit_IX', 'Titlul IX', 'Dispoziții finale și tranzitorii', None)]
        assert [(a['eId'], a['parent']) for a in parser.articles] == [
            ('art_1', 'tit_I'), ('art_2', 'tit_I'), ('art_153', 'sct_III'), ('art_153-1', 'sbs_A'),
            ('art_293', 'tit_IX'), ('art_293-1', 'tit_IX'), ('art_294', 'tit_IX')]
        first = parser.articles[0]
        assert [c['eId'] for c in first['children']] == ['par_1', 'par_2']
        assert first['children'][0]['text'].startswith('(1) În vederea desfășurării de activități')
        # Repealed, and its record of the change left out
        assert [c['text'] for c in parser.articles[4]['children']] == ['Abrogat.']
        text = json.dumps(parser.to_dict(), ensure_ascii=False)
        assert '(la ' not in text and 'a fost modificat de' not in text and 'Notă' not in text

    def test_constitution(self, romania):
        parser = LegislatieHtmlParser().parse(str(romania / 'pagina_47355.html'))
        assert parser.preface == 'CONSTITUȚIE din 21 noiembrie 1991 (republicată)'
        # Marginal titles printed as the first paragraph are the headings
        assert [(a['num'], a['heading']) for a in parser.articles] == [
            ('Articolul 1', 'Statul român'), ('Articolul 7', 'Românii din străinătate'),
            ('Articolul 156', 'Republicarea Constituției')]
        assert [c['eId'] for c in parser.articles[0]['children']] == ['par_1', 'par_2', 'par_3', 'par_4', 'par_5']
        assert 'Decizie de respingere' not in json.dumps(parser.articles, ensure_ascii=False)
        assert parser.recitals[1]['text'].startswith('Constituția României, în forma inițială, a fost adoptată')

    def test_regulation(self, romania):
        parser = LegislatieHtmlParser().parse(str(romania / 'pagina_227381.html'))
        assert parser.formula == 'Guvernul României adoptă prezenta hotărâre.'
        assert parser.recitals[0]['text'].startswith('În temeiul art. 108 din Constituția României')
        # The note before the text quotes articles of another act: they are not articles of this one
        assert [a['num'] for a in parser.articles] == ['Articolul 3', 'Articolul 8', 'Articolul 20', 'Articolul 21',
                                                       'Articolul 161']
        # A heading changed by an amendment is printed as the section's first paragraph
        section = next(c for c in parser.chapters if c['num'] == 'Secţiunea a 2-a')
        assert section['heading'] == 'Înștiințarea Agenției'
        assert parser.articles[3]['parent'] == section['eId']
        # Letters folded into their paragraph, without the records of their changes
        definitions = parser.articles[0]['children']
        assert len(definitions) == 1 and ' b) comisie de soluționare a contestațiilor' in definitions[0]['text']
        assert '(la ' not in definitions[0]['text']
        assert parser.conclusions['signature'].startswith('PRIM-MINISTRU CĂLIN POPESCU-TĂRICEANU')
        assert [(a['num'], [c['text'] for c in a['children']][:1]) for a in parser.annexes][1] == (
            'Anexa nr. 5', ['Abrogată.'])

    def test_amending_law(self, romania):
        parser = LegislatieHtmlParser().parse(str(romania / 'pagina_29843.html'))
        assert parser.preface.startswith('LEGE nr. 459 din 18 iulie 2001 pentru aprobarea Ordonanţei Guvernului')
        assert parser.formula == 'Parlamentul României adopta prezenta lege.'
        points = parser.articles[0]['children']
        amendments = [p['amendment'] for p in points if p['amendment']]
        assert len(amendments) == 8
        assert (amendments[0]['action'], amendments[0]['instruction']) == (
            'replace', '1. Articolul 1 va avea următorul cuprins:')
        assert amendments[0]['quoted'][0]['text'].startswith('Art. 1. - Activitatea de medicina legală')
        assert amendments[4] == {'action': 'delete', 'instruction': '5. La articolul 17 litera g) se abroga.',
                                 'amended_act': None, 'quoted': []}
        # The record of the adoption and the signatures close the act
        assert parser.conclusions['conclusion_text'].startswith('Această lege a fost adoptată de Camera Deputaţilor')
        assert 'VALER DORNEANU' in parser.conclusions['signature']
        assert [len(a['children']) for a in parser.articles[1:]] == [1, 1]

    def test_code(self, romania):
        parser = LegislatieHtmlParser().parse(str(romania / 'pagina_175630.html'))
        assert parser.preface == ('CODUL CIVIL din 17 iulie 2009 (republicat)(actualizat) (Legea nr. 287/2009) '
                                  '(actualizat până la data de 4 februarie 2016)')
        # The editor's footnote under the preliminary title is not a recital
        assert parser.recitals == []
        assert [(c['eId'], c['type'], c['heading'], c['parent']) for c in parser.chapters[:4]] == [
            ('tit_PRELIMINAR', 'title', 'Despre legea civilă', None),
            ('cpt_I', 'chapter', 'Dispoziţii generale', 'tit_PRELIMINAR'),
            ('prt_I', 'part', 'Despre persoane', None), ('tit_II', 'title', 'Persoana fizică', 'prt_I')]
        first = parser.articles[0]
        assert first['heading'] == 'Izvoarele dreptului civil'
        # Paragraphs the page marks as letters, numbered in their text
        assert [c['eId'] for c in first['children']] == [f'par_{n}' for n in range(1, 7)]

    def test_subsections(self, tmp_path):
        # Trimmed from the Civil Code: '§1.' paragraphs of a section head its articles
        page = tmp_path / 'page.html'
        page.write_text(
            '<html><body><div id="div_Formaconsolidata"><span class="S_DEN">CODUL CIVIL din 17 iulie 2009</span>'
            '<span class="S_SEC"><span class="S_SEC_TTL">Secţiunea a 4-a</span><span class="S_SEC_DEN">Exercitarea '
            'tutelei</span><span class="S_SEC_BDY"><span class="S_PAR">§1. Dispoziţii generale</span>'
            '<span class="S_ART"><span class="S_ART_TTL">Articolul 133</span><span class="S_ART_DEN">Exercitarea '
            'tutelei</span><span class="S_ART_BDY"><span class="S_PAR">Tutorele exercită drepturile.</span>'
            '</span></span><span class="S_PAR">§2. Exercitarea tutelei cu privire la persoana minorului</span>'
            '<span class="S_ART"><span class="S_ART_TTL">Articolul 134</span><span class="S_ART_DEN"></span>'
            '<span class="S_ART_BDY"><span class="S_PAR">Tutorele are îndatorirea de a îngriji de minor.</span>'
            '<span class="S_PAR" style="color:blue;">(la 01-10-2011, Articolul 134 a fost modificat de Legea '
            'nr. 71/2011)</span></span></span></span></span></div></body></html>', encoding='utf-8')
        parser = LegislatieHtmlParser().parse(str(page))
        assert [(c['eId'], c['num'], c['heading'], c['parent']) for c in parser.chapters] == [
            ('sct_4', 'Secţiunea a 4-a', 'Exercitarea tutelei', None),
            ('sbs_1', '§1.', 'Dispoziţii generale', 'sct_4'),
            ('sbs_2', '§2.', 'Exercitarea tutelei cu privire la persoana minorului', 'sct_4')]
        assert [(a['eId'], a['parent'], [c['text'] for c in a['children']]) for a in parser.articles] == [
            ('art_133', 'sbs_1', ['Tutorele exercită drepturile.']),
            ('art_134', 'sbs_2', ['Tutorele are îndatorirea de a îngriji de minor.'])]

    @pytest.mark.parametrize('title, expected', [
        ('CONSTITUȚIE*) din 21 noiembrie 1991 (*republicată*)', 'CONSTITUȚIE din 21 noiembrie 1991 (republicată)'),
        ('privind societăţile***) (actualizată la data de 16 iulie 2015*)',
         'privind societăţile (actualizată la data de 16 iulie 2015)'),
        ('Despre legea civilă**)', 'Despre legea civilă'),
    ])
    def test_clean(self, title, expected):
        assert clean(title) == expected

    def test_page_without_text(self, tmp_path):
        page = tmp_path / 'page.html'
        page.write_text('<html><body><p>Eroare</p></body></html>', encoding='utf-8')
        with pytest.raises(FileLoadError, match='no act text'):
            LegislatieHtmlParser().parse(str(page))


class TestPages:
    def test_download_page(self, tmp_path):
        client = PortalLegislativClient(download_dir=str(tmp_path))
        answer = Mock(status_code=200, content='<span class="S_DEN">LEGE nr. 31 privind societăţile</span>'.encode())
        with patch.object(client.session, 'get', return_value=answer) as get:
            path = client.download_page(f'{PORTAL}/169688')
            again = client.download_page(f'{PORTAL}/169688')
        assert path == again and path.endswith('169688.html')
        # Downloaded once, presenting itself as a browser
        get.assert_called_once()
        assert get.call_args.kwargs['headers']['User-Agent'].startswith('Mozilla/5.0')
        with patch.object(client.session, 'get', return_value=answer):
            assert client.download_page(f'{PORTAL}/800?isFormaDeBaza=True').endswith('800_baza.html')

    def test_unreachable(self, tmp_path):
        client = PortalLegislativClient(download_dir=str(tmp_path))
        with patch.object(client.session, 'get', side_effect=requests.ConnectionError('reset')):
            with pytest.raises(NetworkError, match='could not be reached'):
                client.download_page(f'{PORTAL}/169688')
        with patch.object(client.session, 'get', return_value=Mock(status_code=404, content=b'')):
            with pytest.raises(FileLoadError, match='has no page'):
                client.download_page(f'{PORTAL}/1')
        with pytest.raises(ValueError):
            client.download_page('https://legislatie.just.ro/Public/Acasa')


class TestConsolidated:
    def test_fetch_in_force_today(self, romania, companies_law, tmp_path):
        download_page = pages(romania, **{'798': 'pagina_798.html'})
        with patch.object(PortalLegislativClient, 'download', return_value=companies_law) as download, \
                patch.object(PortalLegislativClient, 'download_page', side_effect=download_page) as page:
            doc = tulit.fetch('Legea nr. 31/1990', jurisdiction='RO', version='consolidated',
                              download_dir=str(tmp_path))
        download.assert_called_once_with('LEGE', '31', '1990', title='')
        # The act's page shows its latest form, consolidated on 18.12.2025: no other page is needed
        page.assert_called_once_with(f'{PORTAL}/798')
        meta = doc['meta']
        assert (meta['version'], meta['version_date'], meta['source'], meta['form']) == (
            'consolidated', '2025-12-18', f'{PORTAL}/304533', 'consolidation')
        assert meta['date_in_force'] == '1990-11-17'
        assert len(doc['articles']) == 7
        assert not [p for p in check(doc) if p.severity == ERROR]

    def test_fetch_on_date(self, romania, companies_law, tmp_path):
        download_page = pages(romania, **{'798': 'pagina_798.html', '169688': 'pagina_169688.html'})
        with patch.object(PortalLegislativClient, 'download', return_value=companies_law), \
                patch.object(PortalLegislativClient, 'download_page', side_effect=download_page) as page:
            doc = tulit.fetch('Legea nr. 31/1990', jurisdiction='RO', version='consolidated', date='2016-01-01',
                              download_dir=str(tmp_path))
        # The form consolidated on 16.07.2015 was in force until the next one, of 07.07.2017
        assert page.call_args_list[-1].args == (f'{PORTAL}/169688',)
        assert (doc['meta']['version_date'], doc['meta']['source']) == ('2015-07-16', f'{PORTAL}/169688')
        assert doc['preface'].endswith('(actualizată la data de 16 iulie 2015)')

    def test_republication(self, romania, companies_law, tmp_path):
        download_page = pages(romania, **{'798': 'pagina_798.html', '800?isFormaDeBaza=True': 'pagina_169688.html'})
        with patch.object(PortalLegislativClient, 'download', return_value=companies_law), \
                patch.object(PortalLegislativClient, 'download_page', side_effect=download_page) as page:
            found = RomaniaSource().retrieve('Legea nr. 31/1990', 'consolidated', '1998-06-01', None, str(tmp_path))
        assert page.call_args_list[-1].args == (f'{PORTAL}/800?isFormaDeBaza=True',)
        assert (found.version_date, found.meta['form']) == ('1998-01-29', 'republication')

    def test_before_first_consolidation(self, romania, companies_law, tmp_path):
        # In force as published until its first consolidation (04.06.1991)
        download_page = pages(romania, **{'798': 'pagina_798.html', '798?isFormaDeBaza=True': 'pagina_29843.html'})
        with patch.object(PortalLegislativClient, 'download', return_value=companies_law), \
                patch.object(PortalLegislativClient, 'download_page', side_effect=download_page) as page:
            found = RomaniaSource().retrieve('Legea nr. 31/1990', 'consolidated', '1991-01-01', None, str(tmp_path))
        assert page.call_args_list[-1].args == (f'{PORTAL}/798?isFormaDeBaza=True',)
        assert (found.version_date, found.meta['form'], found.parser) == ('1990-11-17', 'base', 'ro-legislatie-html')

    def test_not_yet_in_force(self, companies_law, tmp_path):
        with patch.object(PortalLegislativClient, 'download', return_value=companies_law):
            with pytest.raises(FileLoadError, match='enters into force on 1990-11-17'):
                RomaniaSource().retrieve('Legea nr. 31/1990', 'consolidated', '1990-01-01', None, str(tmp_path))

    def test_bad_date(self, tmp_path):
        with pytest.raises(UnsupportedError, match='not an ISO date'):
            RomaniaSource().retrieve('Legea nr. 31/1990', 'consolidated', '1.1.2020', None, str(tmp_path))

    def test_never_consolidated(self, romania, tmp_path):
        # Legea 190/2018: its page (document 203151) is its only form when it lists none
        download_page = pages(romania, **{'203151': 'pagina_29843.html'})
        with patch.object(PortalLegislativClient, 'download',
                          return_value=str(romania / 'lege_190_2018.xml')) as download, \
                patch.object(PortalLegislativClient, 'download_page', side_effect=download_page) as page:
            found = RomaniaSource().retrieve('Legea 190/2018', 'consolidated', '2020-01-01', None, str(tmp_path))
        download.assert_called_once_with('LEGE', '190', '2018', title='')
        page.assert_called_once_with(f'{PORTAL}/203151')
        assert (found.version, found.version_date, found.meta['form'], found.meta['source']) == (
            'consolidated', '2018-07-31', 'base', f'{PORTAL}/203151')

    def test_code(self, romania, tmp_path):
        # The text of the Civil Code is a document of its own, which its consolidated forms follow
        record = soap_record(tmp_path, '109884', 'CODUL CIVIL', 'CODUL CIVIL din 17 iulie 2009 ( Legea nr. 287/2009 ) '
                             'EMITENT: PARLAMENTUL PUBLICAT ÎN: MONITORUL OFICIAL nr. 511 din 24 iulie 2009',
                             '2011-10-01')
        download_page = pages(romania, **{'109884': 'pagina_175630.html', '137240': 'pagina_175630.html'})
        with patch.object(PortalLegislativClient, 'download', return_value=record) as download, \
                patch.object(PortalLegislativClient, 'download_page', side_effect=download_page) as page:
            doc = tulit.fetch('Codul civil', jurisdiction='RO', version='consolidated', date='2016-03-01',
                              download_dir=str(tmp_path))
            # Republished and consolidated on 01.10.2011, the day it entered into force: the consolidation
            first = RomaniaSource().retrieve('Codul civil', 'consolidated', '2011-10-01', None, str(tmp_path))
        download.assert_called_with('CODUL CIVIL', '0', '2009', title='codul civil')
        assert (doc['meta']['version_date'], doc['meta']['source']) == ('2016-02-04', f'{PORTAL}/175630')
        assert doc['articles'][0]['heading'] == 'Izvoarele dreptului civil'
        assert (first.version_date, first.meta['source']) == ('2011-10-01', f'{PORTAL}/137240')
        assert page.call_args_list[-1].args == (f'{PORTAL}/137240',)

    def test_constitution(self, romania, tmp_path):
        record = soap_record(tmp_path, '1413', 'CONSTITUȚIE', 'CONSTITUŢIA din 21 noiembrie 1991 EMITENT: ADUNAREA '
                             'CONSTITUANTĂ PUBLICAT ÎN: MONITORUL OFICIAL nr. 233 din 21 noiembrie 1991', '1991-12-14')
        download_page = pages(romania, **{'1413': 'pagina_47355.html'})
        with patch.object(PortalLegislativClient, 'download', return_value=record) as download, \
                patch.object(PortalLegislativClient, 'download_page', side_effect=download_page):
            doc = tulit.fetch('Constituția', jurisdiction='RO', version='consolidated', download_dir=str(tmp_path))
        download.assert_called_once_with('CONSTITUȚIE', '0', '1991', title='Constitutia')
        # The form in force is the Constitution as republished after its revision of 2003
        assert (doc['meta']['version_date'], doc['meta']['form'], doc['meta']['source']) == (
            '2003-10-31', 'republication', f'{PORTAL}/47355')
        assert doc['preface'] == 'CONSTITUȚIE din 21 noiembrie 1991 (republicată)'
