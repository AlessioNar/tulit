import pytest

from tulit.parser.parser import LegalJSONValidator
from tulit.parser.registry import get_parser
from tulit.parser.xml.bwb import BWBParser


@pytest.fixture(scope='module')
def uavg(data_root):
    path = data_root / 'sources' / 'member_states' / 'netherlands' / 'bwb' / 'BWBR0040940.xml'
    return BWBParser().parse(str(path)).to_dict()


def test_registered():
    assert isinstance(get_parser('bwb'), BWBParser)


def test_preface_and_preamble(uavg):
    assert uavg['preface'].startswith('Wet van 16 mei 2018, houdende regels ter uitvoering')
    preamble = uavg['preamble']
    assert preamble['formula'].startswith('Wij Willem-Alexander')
    assert preamble['recitals'][0] == {
        'eId': 'rct_1', 'text': 'Allen, die deze zullen zien of horen lezen, saluut! doen te weten:'}
    assert preamble['final'].startswith('Zo is het, dat Wij')


def test_divisions_keep_dotted_numbers(uavg):
    assert [c['eId'] for c in uavg['chapters']] == ['cpt_1', 'cpt_2', 'sbs_2-1', 'sbs_2-2']
    assert uavg['chapters'][2] == {
        'eId': 'sbs_2-1', 'type': 'subsection', 'num': 'Paragraaf 2.1',
        'heading': 'Oprichting en inrichting van de Autoriteit persoonsgegevens', 'parent': 'cpt_2'}


def test_articles_and_paragraphs(uavg):
    articles = {a['eId']: a for a in uavg['articles']}
    art1 = articles['art_1']
    assert (art1['num'], art1['heading'], art1['parent']) == ('Artikel 1', 'Definities', 'cpt_1')
    # an article without numbered paragraphs: the list belongs to the opening sentence
    assert len(art1['children']) == 1
    assert 'bijzondere categorieën van persoonsgegevens' in art1['children'][0]['text']
    numbered = next(a for a in uavg['articles'] if len(a['children']) > 1)
    assert numbered['children'][0]['eId'] == 'par_1'
    assert numbered['children'][0]['text'].startswith('1 ')


def test_metadata_blocks_left_out(uavg):
    text = ' '.join(c['text'] for a in uavg['articles'] for c in a['children'])
    assert 'Stb.' not in text and 'jci1.3' not in text


def test_signatures(uavg):
    signature = uavg['conclusions']['signature']
    assert (signature['place'], signature['date'], signature['signatory']) == (
        'Wassenaar', '2018-05-16', 'Willem-Alexander')
    assert len(signature['signatories']) == 4
    # the publication line (uitgifte) closes the conclusions
    assert 'tweeëntwintigste mei 2018' in uavg['conclusions']['conclusion_text']


def test_valid(uavg):
    assert LegalJSONValidator().validate(uavg)


def _parse(tmp_path, body):
    path = tmp_path / 'act.xml'
    path.write_text(f'<toestand><wetgeving><intitule>Wet</intitule><wet-besluit><wettekst>{body}'
                    '</wettekst></wet-besluit></wetgeving></toestand>', encoding='utf-8')
    return BWBParser().parse(str(path)).to_dict()


def test_unnumbered_article_keeps_art_1_free(tmp_path):
    # the Grondwet opens with an unnumbered 'Algemene bepaling' before Artikel 1
    doc = _parse(tmp_path, '<artikel><kop><titel>Algemene bepaling</titel></kop><al>De Grondwet waarborgt.</al>'
                           '</artikel><artikel label="Artikel 1"><kop><label>Artikel</label><nr>1</nr></kop>'
                           '<al>Allen die zich in Nederland bevinden.</al></artikel>')
    assert [(a['eId'], a['num']) for a in doc['articles']] == [('art_unnumbered', None), ('art_1', 'Artikel 1')]


def test_repealing_article_is_an_amendment(tmp_path):
    doc = _parse(tmp_path, '<wijzig-artikel><kop><label>Artikel</label><nr>51.</nr></kop>'
                           '<wat type="ingetrokken">De Wet bescherming persoonsgegevens wordt ingetrokken.</wat>'
                           '</wijzig-artikel>')
    amendment = doc['articles'][0]['children'][0]['amendment']
    assert (amendment['action'], amendment['amended_act']) == ('repeal', 'De Wet bescherming persoonsgegevens')


def test_amending_article_without_parts_is_one_amendment(tmp_path):
    # stb-2024-200: Artikel II and IIA carry their instruction in the article itself
    doc = _parse(tmp_path, '<wijzig-artikel><kop><nr>II.</nr></kop><wat type="wijziging">In artikel 1.1 van het '
                           'Uitvoeringsbesluit WHW 2008 vervallen de begripsomschrijvingen.</wat></wijzig-artikel>'
                           '<wijzig-artikel><kop><nr>IIA.</nr></kop><wat type="wijziging">Aan artikel V van de Wet '
                           'wordt een volzin toegevoegd, luidende:</wat><wijziging><artikeltekst><al>In dat besluit '
                           'kan worden bepaald.</al></artikeltekst></wijziging></wijzig-artikel>')
    second, third = doc['articles']
    assert [c['amendment']['action'] for c in second['children']] == ['delete']
    assert len(third['children']) == 1
    amendment = third['children'][0]['amendment']
    assert amendment['action'] == 'add'
    assert amendment['quoted'] == [{'kind': 'text', 'text': 'In dat besluit kan worden bepaald.'}]


def test_transitional_provision_marked_as_amending_is_no_amendment(tmp_path):
    # stb-2010-1, Artikel X
    doc = _parse(tmp_path, '<wijzig-artikel><kop><nr>X</nr></kop><wat type="wijziging">Artikel I is niet van '
                           'toepassing op strafbare feiten die zijn begaan voor de inwerkingtreding.</wat>'
                           '</wijzig-artikel>')
    assert doc['articles'][0]['children'][0].get('amendment') is None


def test_ministeriele_regeling(tmp_path):
    # BWBR0018715 (Regeling zorgverzekering): regeling-tekst instead of wettekst
    path = tmp_path / 'regeling.xml'
    path.write_text(
        '<toestand><wetgeving><intitule>Regeling zorgverzekering</intitule><regeling>'
        '<aanhef><wie>De Minister van Volksgezondheid,</wie><considerans><considerans.al>Gelet op artikel 32;'
        '</considerans.al></considerans><afkondiging><al>Besluit:</al></afkondiging></aanhef>'
        '<regeling-tekst><hoofdstuk><kop><label>Hoofdstuk</label><nr>1</nr></kop><artikel><kop><label>Artikel'
        '</label><nr>1.1</nr></kop><al>In deze regeling wordt verstaan onder wet: Zorgverzekeringswet.</al>'
        '</artikel></hoofdstuk></regeling-tekst><regeling-sluiting><slotformulering><al>Deze regeling zal in de '
        'Staatscourant worden geplaatst.</al></slotformulering><ondertekening>De <functie>Minister</functie>, '
        '<naam><voornaam>J.F.</voornaam><achternaam>Hoogervorst</achternaam></naam></ondertekening>'
        '</regeling-sluiting></regeling></wetgeving></toestand>', encoding='utf-8')
    doc = BWBParser().parse(str(path)).to_dict()
    assert [a['eId'] for a in doc['articles']] == ['art_1-1']
    assert doc['preamble']['formula'] == 'De Minister van Volksgezondheid,'
    assert doc['conclusions']['signature']['signatory'].endswith('J.F. Hoogervorst')
