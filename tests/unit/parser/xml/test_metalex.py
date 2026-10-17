import pytest

from tulit.parser.parser import LegalJSONValidator
from tulit.parser.registry import get_parser
from tulit.parser.xml.metalex import METALEX_NS, MetaLexParser


@pytest.fixture(scope='module')
def folder(data_root):
    return data_root / 'sources' / 'member_states' / 'slovakia' / 'slovlex'


@pytest.fixture(scope='module')
def act(folder):
    return MetaLexParser().parse(str(folder / '18_2018_20260818.xml'))


@pytest.fixture(scope='module')
def constitution(folder):
    return MetaLexParser().parse(str(folder / '460_1992_vyhlasene_znenie.xml')).to_dict()


def test_registered():
    assert isinstance(get_parser('metalex'), MetaLexParser)


def test_preface_formula_and_metadata(act):
    doc = act.to_dict()
    assert doc['preface'] == ('ZÁKON z 29. novembra 2017 o ochrane osobných údajov '
                              'a o zmene a doplnení niektorých zákonov')
    assert doc['preamble']['formula'] == 'Národná rada Slovenskej republiky sa uzniesla na tomto zákone:'
    assert act.metadata('slovlex-owl:schvaleny') == '2017-11-29'
    assert act.metadata('slovlex-owl:vyhlaseny') == '2018-01-30'


def test_article_wrapping_the_act_is_transparent(act):
    doc = act.to_dict()
    # Čl. I holds the act itself: its parts are top-level divisions
    assert doc['chapters'][0] == {'eId': 'prt_1', 'type': 'part', 'num': 'PRVÁ ČASŤ',
                                  'heading': 'ZÁKLADNÉ USTANOVENIA', 'parent': None}
    # the amending articles that follow are articles outside any division
    amending = [a for a in doc['articles'] if a['num'].startswith('Čl.')]
    assert [a['eId'] for a in amending] == ['art_IX', 'art_XVI']
    assert all(a['parent'] is None for a in amending)


def test_paragraphs_and_subsections(act):
    paragraph = next(a for a in act.to_dict()['articles'] if a['eId'] == 'art_3')
    assert (paragraph['num'], paragraph['heading'], paragraph['parent']) == ('§ 3', 'Pôsobnosť', 'prt_1')
    assert paragraph['children'][0]['eId'] == 'par_1'
    assert paragraph['children'][0]['text'].startswith('(1) Tento zákon sa vzťahuje')


def test_quoted_annexes_belong_to_the_amending_article(act):
    doc = act.to_dict()
    assert [a['eId'] for a in doc['annexes']] == ['anx_1']
    assert doc['annexes'][0]['num'].startswith('Príloha k zákonu č. 18/2018')


def test_signatories(act):
    assert act.to_dict()['conclusions']['signature']['signatories'] == [
        'Andrej Kiska v. r.', 'Andrej Danko v. r.', 'Robert Fico v. r.']


def test_constitution(constitution):
    # The title in the order of the document, the preamble as a recital
    assert constitution['preface'] == 'ÚSTAVA SLOVENSKEJ REPUBLIKY z 1. septembra 1992'
    assert constitution['preamble']['formula'] is None
    assert [r['text'][:26] for r in constitution['preamble']['recitals']] == ['My, národ slovenský, pamät']
    assert constitution['chapters'][:2] == [
        {'eId': 'tit_1', 'type': 'title', 'num': 'PRVÁ HLAVA', 'heading': None, 'parent': None},
        {'eId': 'sct_1', 'type': 'section', 'num': 'Prvý oddiel', 'heading': 'ZÁKLADNÉ USTANOVENIA',
         'parent': 'tit_1'},
    ]
    article = constitution['articles'][0]
    assert (article['eId'], article['num'], article['parent']) == ('art_1', 'Čl. 1', 'sct_1')


def test_amending_points(act):
    article = next(a for a in act.to_dict()['articles'] if a['eId'] == 'art_IX')
    intro, first, second = article['children'][:3]
    assert intro['amendment'] is None
    assert first['amendment']['action'] == 'replace'
    assert first['amendment']['amended_act'].startswith('Zákon č. 417/2002 Z. z. o používaní analýzy')
    assert first['amendment']['quoted'][0]['text'].startswith('b) analýzou deoxyribonukleovej kyseliny')
    assert (second['amendment']['action'], second['amendment']['instruction']) == (
        'add', '2. § 2 sa dopĺňa písmenom f), ktoré znie:')


def _act(tmp_path, body):
    path = tmp_path / 'act.xml'
    path.write_text(f'<root xmlns="{METALEX_NS}"><hcontainer name="predpis">'
                    '<htitle name="predpisTyp">ZÁKON</htitle>' + body + '</hcontainer></root>', encoding='utf-8')
    return MetaLexParser().parse(str(path)).to_dict()


def _par(number, *blocks):
    return (f'<hcontainer name="paragraf"><htitle name="paragrafOznacenie">{number}</htitle>' + ''.join(blocks)
            + '</hcontainer>')


def _block(name, text):
    return f'<hcontainer name="{name}"><container name="text"><block name="blokTextu">{text}</block></container>' \
           '</hcontainer>'


def test_amendment_verbs_and_quoted_footnotes(tmp_path):
    quote = ('<container name="text2"><quoteblock name="blokTextu"><quotation name="citat">'
             '<hcontainer name="poznamka"><container name="text"><block name="blokTextu">1) Zákon č. 199/2004 Z. z.'
             '</block></container></hcontainer></quotation></quoteblock></container>')
    doc = _act(tmp_path, '<hcontainer name="clanok"><htitle name="clanokOznacenie">Čl. I</htitle>'
               + _block('odsek', 'Zákon č. 177/2018 Z. z. sa mení a dopĺňa takto:')
               + _block('bod', '1. V § 1 sa za slová „verejnej správy“ vkladajú slová „a v systéme“.')
               + '<hcontainer name="bod"><container name="text"><block name="blokTextu">2. Poznámka pod čiarou '
                 'k odkazu 1 znie:</block></container>' + quote + '</hcontainer></hcontainer>')
    intro, insert, footnote = doc['articles'][0]['children']
    assert (insert['amendment']['action'], insert['amendment']['amended_act']) == ('insert', 'Zákon č. 177/2018 Z. z.')
    # A footnote an amendment quotes is kept
    assert footnote['amendment']['quoted'] == [{'kind': 'text', 'text': '1) Zákon č. 199/2004 Z. z.'}]
    assert footnote['text'].endswith('1) Zákon č. 199/2004 Z. z.')


def test_quoted_oath_is_not_an_amendment(tmp_path):
    quote = '<container name="text2"><quoteblock name="blokTextu">„Sľubujem na svoju česť.“</quoteblock></container>'
    doc = _act(tmp_path, '<hcontainer name="ustavnyclanok"><htitle name="ustavnyclanokOznacenie">Čl. 75</htitle>'
               '<hcontainer name="odsek"><container name="text"><block name="blokTextu">Poslanec skladá sľub, '
               'ktorý znie:</block></container>' + quote + '</hcontainer></hcontainer>')
    assert doc['articles'][0]['children'][0]['amendment'] is None


def test_articles_the_markup_misplaces(tmp_path):
    # Civil Code 1964: principles in a marked item, § 197 inside § 196, § 451 in a subsection of a section
    doc = _act(tmp_path, '<hcontainer name="oznacenaPolozka"><htitle name="oznacenaPolozkaOznacenie">Zásady</htitle>'
               '<hcontainer name="clanok"><htitle name="clanokOznacenie">Článok I</htitle>'
               + _block('odsek', 'Základom je výroba.') + '</hcontainer></hcontainer>'
               '<hcontainer name="hlava"><htitle name="hlavaOznacenie">PRVÁ HLAVA</htitle>'
               + _par('§ 196', _block('odsek', 'Text 196.'), _par('§ 197', _block('odsek', 'Text 197.')))
               + '<hcontainer name="odsek">' + _par('§ 451', _block('odsek', 'Text 451.')) + '</hcontainer>'
               '</hcontainer>')
    assert [(a['num'], [c['text'] for c in a['children']]) for a in doc['articles']] == [
        ('Článok I', ['Základom je výroba.']), ('§ 196', ['Text 196.']), ('§ 197', ['Text 197.']),
        ('§ 451', ['Text 451.'])]
    assert [(c['type'], c['heading']) for c in doc['chapters']] == [('group', 'Zásady'), ('title', None)]


def test_notice_without_articles(tmp_path):
    doc = _act(tmp_path, '<container name="text"><block name="blokTextu">Ministerstvo oznamuje, že boli uložené '
               'zmluvy:</block></container>' + _block('bod', '1. Kolektívna zmluva pre odvetvie vodovodov.'))
    article, = doc['articles']
    assert article['num'] is None
    assert [c['text'] for c in article['children']] == [
        'Ministerstvo oznamuje, že boli uložené zmluvy:', '1. Kolektívna zmluva pre odvetvie vodovodov.']
    assert doc['preamble']['formula'] is None


def test_annex_table_rows(tmp_path):
    def row(*cells):
        return '<inline name="xhtml:tr">' + ''.join(f'<inline name="xhtml:td">{c}</inline>' for c in cells) \
            + '</inline>'
    doc = _act(tmp_path, _par('§ 1', _block('odsek', 'Text.')) + '<hcontainer name="priloha">'
               '<htitle name="prilohaOznacenie">Príloha č. 1</htitle><hcontainer name="oznacenaPolozka">'
               '<htitle name="oznacenaPolozkaOznacenie">Nepatrné množstvo látok</htitle><container name="text">'
               '<block name="blokTextu"><inline name="xhtml:table"><inline name="xhtml:tbody">'
               + row('Druh látky', 'Účinná látka') + row('Heroín', 'diacetylmorfín')
               + '</inline></inline></block></container></hcontainer></hcontainer>')
    assert [c['text'] for c in doc['annexes'][0]['children']] == [
        'Nepatrné množstvo látok', 'Druh látky Účinná látka', 'Heroín diacetylmorfín']


def test_valid(act, constitution):
    assert LegalJSONValidator().validate(act.to_dict())
    assert LegalJSONValidator().validate(constitution)
