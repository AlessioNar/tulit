import json

import pytest

from tulit.parser.parser import LegalJSONValidator
from tulit.parser.registry import get_parser
from tulit.parser.xml.ris import RISParser, classify_division, german_ordinal


@pytest.fixture(scope='module')
def dsg(data_root):
    folder = data_root / 'sources' / 'member_states' / 'austria' / 'ris' / '10001597'
    return RISParser().parse(str(folder)).to_dict()


@pytest.mark.parametrize('word, number', [
    ('Erstes', 1), ('Zweytes', 2), ('Drittes', 3), ('Eilftes', 11), ('Sechzehntes', 16),
    ('Zwanzigstes', 20), ('Zwey u. zwanzigstes', 22), ('Dreyßigstes', 30), ('Erste', 1),
])
def test_german_ordinal(word, number):
    assert german_ordinal(word) == number


@pytest.mark.parametrize('text, expected', [
    ('5. Abschnitt', ('section', '5')),
    ('1. Hauptstück', ('chapter', '1')),
    ('Erster Theil', ('part', '1')),
    ('Zweyte Abtheilung', ('title', '2')),
    ('Sechs u. zwanzigstes Hauptstück.', ('chapter', '26')),
    ('2. Unterabschnitt', ('subsection', '2')),
    ('Artikel 2', ('part', '2')),
    ('Einleitung.', ('part', 'einleitung')),
    ('Schlußteil', ('part', None)),
    ('Von dem Sachenrechte.', None),
])
def test_classify_division(text, expected):
    assert classify_division(text) == expected


def test_registered_as_ris():
    assert isinstance(get_parser('ris'), RISParser)


def test_preface_and_formula(dsg):
    assert dsg['preface'].startswith('Bundesgesetz zum Schutz natürlicher Personen')
    assert dsg['preamble']['formula'] == 'Der Nationalrat hat beschlossen:'


def test_divisions_are_typed_and_nested(dsg):
    chapters = {c['eId']: c for c in dsg['chapters']}
    assert chapters['prt_1']['heading'] == '(Verfassungsbestimmung)'
    assert chapters['cpt_1'] == {
        'eId': 'cpt_1', 'type': 'chapter', 'num': '1. Hauptstück',
        'heading': 'Durchführung der Datenschutz-Grundverordnung und ergänzende Regelungen',
        'parent': 'prt_2'}
    assert chapters['sct_1']['parent'] == 'cpt_1'


def test_articles_and_paragraphs(dsg):
    articles = {a['eId']: a for a in dsg['articles']}
    assert list(articles) == ['art_1', 'art_4', 'art_5', 'art_14', 'art_34', 'art_35', 'art_35a']
    art1 = articles['art_1']
    assert art1['num'] == '§ 1'
    assert art1['heading'] == 'Grundrecht auf Datenschutz'
    assert art1['parent'] == 'prt_1'
    assert art1['children'][0]['eId'] == 'par_1'
    # the § number is the article num, not part of the paragraph text
    assert art1['children'][0]['text'].startswith('(1) Jedermann')


def test_lists_fold_into_their_paragraph(dsg):
    art34 = next(a for a in dsg['articles'] if a['eId'] == 'art_34')
    paragraph = next(c for c in art34['children'] if c['eId'] == 'par_2')
    assert '1. spezielle Verfahren' in paragraph['text']


def test_structure_tree(dsg):
    part2 = dsg['structure'][1]
    assert part2['eId'] == 'prt_2'
    assert part2['children'][0]['eId'] == 'cpt_1'


def test_output_is_valid_legaljson(dsg):
    assert LegalJSONValidator().validate(dsg)


def _unit(headings, text):
    elements = ''.join(f'<ueberschrift typ="{typ}" ct="text" halign="c">{t}</ueberschrift>' for typ, t in headings)
    return ('<?xml version="1.0" encoding="utf-8"?><risdok xmlns="http://www.bka.gv.at"><nutzdaten>'
            '<abschnitt><ueberschrift typ="titel" halign="j">Text</ueberschrift>'
            f'{elements}<absatz typ="abs" ct="text" halign="j">{text}</absatz>'
            '<ueberschrift typ="titel" halign="j">Zuletzt aktualisiert am</ueberschrift>'
            '</abschnitt></nutzdaten></risdok>')


def test_lettered_and_numbered_sections(tmp_path):
    # B-VG: 'Zweites Hauptstück' / 'A. Nationalrat' / ... ; 'A. Verwaltung' / '1. Bundespräsident'
    units = [
        ('Art. 24', [('g1', 'Zweites Hauptstück'), ('g2', 'Gesetzgebung des Bundes'), ('g1min', 'A. Nationalrat')]),
        ('Art. 34', [('g1', 'B. Bundesrat')]),
        ('Art. 38', [('para', 'C. Bundesversammlung')]),
        ('Art. 60', [('g1', 'Drittes Hauptstück'), ('g2', 'Vollziehung des Bundes'), ('g1min', 'A. Verwaltung'),
                     ('g2', '1. Bundespräsident')]),
        ('Art. 69', [('g1', '2. Bundesregierung')]),
    ]
    index = {'units': []}
    for position, (label, headings) in enumerate(units):
        (tmp_path / f'{position}.xml').write_text(_unit(headings, 'Text.'), encoding='utf-8')
        index['units'].append({'file': f'{position}.xml', 'unit': label, 'short_title': 'B-VG'})
    (tmp_path / 'index.json').write_text(json.dumps(index), encoding='utf-8')

    doc = RISParser().parse(str(tmp_path)).to_dict()
    divisions = [(c['eId'], c['num'], c['heading'], c['parent']) for c in doc['chapters']]
    assert divisions == [
        ('cpt_2', 'Zweites Hauptstück', 'Gesetzgebung des Bundes', None),
        ('sct_A', 'A.', 'Nationalrat', 'cpt_2'),
        ('sct_B', 'B.', 'Bundesrat', 'cpt_2'),
        ('sct_C', 'C.', 'Bundesversammlung', 'cpt_2'),
        ('cpt_3', 'Drittes Hauptstück', 'Vollziehung des Bundes', None),
        ('sct_A_2', 'A.', 'Verwaltung', 'cpt_3'),
        ('sbs_1', '1.', 'Bundespräsident', 'sct_A_2'),
        ('sbs_2', '2.', 'Bundesregierung', 'sct_A_2'),
    ]
    articles = {a['num']: a for a in doc['articles']}
    assert articles['Art. 34']['parent'] == 'sct_B'
    assert [c['text'] for c in articles['Art. 34']['children']] == ['Text.']
    assert articles['Art. 38']['heading'] is None
    assert articles['Art. 69']['parent'] == 'sbs_2'


def test_group_headings_and_repeated_parts(tmp_path):
    # ABGB: Roman sections, 'art' group headings, 'b)' subsections, a part heading repeated in a later unit
    units = [
        ('§ 16', [('g1', 'Erster Theil.'), ('g2', 'Von dem Personen-Rechte.'),
                  ('art', 'I. Aus dem Charakter der Persönlichkeit.'), ('para', 'Angeborne Rechte.')]),
        ('§ 21', [('g1min', 'II. Personenrechte der Minderjährigen'), ('para', 'Minderjährige')]),
        ('§ 143', [('g1min', 'b) Abstammung von der Mutter')]),
        ('§ 285', [('g1', 'Zweyter Theil'), ('g2', 'Von dem Sachenrechte.')]),
        ('§ 310', [('art', 'Erwerbung des Besitzes.'), ('para', 'Fähigkeit der Person zur Besitzerwerbung.')]),
        ('§ 859', [('g1', 'Zweyter Theil.'), ('g1', 'Zweyte Abtheilung.'),
                   ('g2', 'Von den persönlichen Sachenrechten.')]),
    ]
    index = {'units': []}
    for position, (label, headings) in enumerate(units):
        (tmp_path / f'{position}.xml').write_text(_unit(headings, 'Text.'), encoding='utf-8')
        index['units'].append({'file': f'{position}.xml', 'unit': label, 'short_title': 'ABGB'})
    (tmp_path / 'index.json').write_text(json.dumps(index), encoding='utf-8')

    doc = RISParser().parse(str(tmp_path)).to_dict()
    divisions = [(c['eId'], c['num'], c['heading'], c['parent']) for c in doc['chapters']]
    assert divisions == [
        ('prt_1', 'Erster Theil.', 'Von dem Personen-Rechte.', None),
        ('sct_I', 'I.', 'Aus dem Charakter der Persönlichkeit.', 'prt_1'),
        ('sct_II', 'II.', 'Personenrechte der Minderjährigen', 'prt_1'),
        ('sbs_b', 'b)', 'Abstammung von der Mutter', 'sct_II'),
        ('prt_2', 'Zweyter Theil', 'Von dem Sachenrechte.', None),
        ('sct_3', None, 'Erwerbung des Besitzes.', 'prt_2'),
        ('tit_2', 'Zweyte Abtheilung.', 'Von den persönlichen Sachenrechten.', 'prt_2'),
    ]
    articles = {a['num']: a for a in doc['articles']}
    assert articles['§ 16']['heading'] == 'Angeborne Rechte.'
    assert [c['text'] for c in articles['§ 310']['children']] == ['Text.']
    assert articles['§ 859']['parent'] == 'tit_2'


def test_numbered_division_on_the_second_line(tmp_path):
    # StGB: 'Allgemeiner Teil' (g1) / 'Erster Abschnitt' (g2) / 'Allgemeine Bestimmungen' (g1min)
    units = [
        ('§ 1', [('g1', 'Allgemeiner Teil'), ('g2', 'Erster Abschnitt'), ('g1min', 'Allgemeine Bestimmungen')]),
        ('§ 17', [('g1', 'Zweiter Abschnitt'), ('g2', 'Einteilung der strafbaren Handlungen')]),
        ('§ 75', [('g1', 'Besonderer Teil'), ('g2', 'Erster Abschnitt'), ('g1min', 'Strafbare Handlungen')]),
        ('§ 325', [('g1', 'Schlußteil')]),
    ]
    index = {'units': []}
    for position, (label, headings) in enumerate(units):
        (tmp_path / f'{position}.xml').write_text(_unit(headings, 'Text.'), encoding='utf-8')
        index['units'].append({'file': f'{position}.xml', 'unit': label, 'short_title': 'StGB'})
    (tmp_path / 'index.json').write_text(json.dumps(index), encoding='utf-8')

    doc = RISParser().parse(str(tmp_path)).to_dict()
    divisions = [(c['eId'], c['num'], c['heading'], c['parent']) for c in doc['chapters']]
    assert divisions == [
        ('prt_1', 'Allgemeiner Teil', None, None),
        ('sct_1', 'Erster Abschnitt', 'Allgemeine Bestimmungen', 'prt_1'),
        ('sct_2', 'Zweiter Abschnitt', 'Einteilung der strafbaren Handlungen', 'prt_1'),
        ('prt_2', 'Besonderer Teil', None, None),
        ('sct_1_2', 'Erster Abschnitt', 'Strafbare Handlungen', 'prt_2'),
        ('prt_3', 'Schlußteil', None, None),
    ]
    assert [a['parent'] for a in doc['articles']] == ['sct_1', 'sct_2', 'sct_1_2', 'prt_3']
