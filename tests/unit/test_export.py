import io
import json
import zipfile

import pytest
from lxml import etree

import tulit
from tulit.cli import main
from tulit.exporters import leg_files, to_akn, to_leg, validate
from tulit.parser.registry import get_parser
from tulit.quality import counts

AKN = {'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0'}


def _doc():
    amendment = {'action': 'replace', 'instruction': 'Article 5 is replaced by the following:',
                 'amended_act': 'Regulation (EU) 2016/679',
                 'quoted': [{'kind': 'text', 'text': 'Article 5 Principles'},
                            {'kind': 'structure', 'children': [{'text': '1. Personal data shall be processed.'}]}]}
    return {
        'meta': {'jurisdiction': 'XX', 'language': 'eng', 'version': 'original', 'version_date': '2024-03-13',
                 'date_document': '2024-03-13', 'source': 'https://example.org/acts/2024-7.xml', 'number': '2024/7'},
        'preface': 'Data Protection Act',
        'preamble': {'formula': 'The Parliament enacts:', 'citations': [{'eId': 'cit_1', 'text': 'Having regard'}],
                     'recitals_intro': 'Whereas:', 'recitals': [{'eId': 'rct_1', 'text': '(1) A recital.'}],
                     'final': 'HAS ADOPTED THIS ACT:'},
        'chapters': [{'eId': 'prt_1', 'type': 'part', 'num': 'Part 1', 'heading': 'General', 'parent': None},
                     {'eId': 'grp_1', 'type': 'group', 'num': None, 'heading': 'Definitions', 'parent': 'prt_1'},
                     {'eId': 'cpt_2', 'type': 'chapter', 'num': 'Chapter 2', 'heading': 'Empty', 'parent': None}],
        'articles': [
            {'eId': 'art_1', 'num': 'Article 1', 'heading': 'Scope', 'parent': 'grp_1',
             'children': [{'eId': 'par_1', 'text': '1. This Act applies.', 'amendment': None},
                          {'eId': 'par_1', 'text': '1. A repeated number.', 'amendment': None},
                          {'eId': 'unp_1', 'text': 'Unnumbered text.', 'amendment': None}]},
            {'eId': 'art_2', 'num': None, 'heading': None, 'parent': None,
             'children': [{'eId': 'unp_1', 'text': 'Article 5 is replaced by the following: Article 5 Principles',
                           'amendment': amendment}]},
            {'eId': 'art_3', 'num': 'Article 3', 'heading': 'Repealed', 'parent': None, 'children': []},
        ],
        'conclusions': {'conclusion_text': 'Done at Brussels.', 'signature': 'For the Parliament, The President'},
        'annexes': [{'eId': 'anx_1', 'num': 'ANNEX I', 'heading': 'Fees', 'children': [
            {'eId': 'unp_1', 'text': 'Fees apply.', 'amendment': None},
            {'eId': 'unp_2', 'text': 'Fee | Amount\nRegistration | 10 EUR', 'amendment': None,
             'table': {'caption': None, 'rows': [['Fee', 'Amount'], ['Registration', '10 EUR']], 'notes': []}}]}],
        'structure': [{'eId': 'prt_1', 'type': 'part', 'num': 'Part 1', 'children': [
            {'eId': 'grp_1', 'type': 'group', 'num': None, 'children': [{'eId': 'art_1', 'type': 'article'}]}]},
            {'eId': 'art_2', 'type': 'article'}, {'eId': 'art_3', 'type': 'article'},
            {'eId': 'cpt_2', 'type': 'chapter', 'num': 'Chapter 2', 'children': []}],
    }


def _read(xml: bytes, tmp_path, name='act.xml', format_id='akn'):
    path = tmp_path / name
    path.write_bytes(xml)
    return get_parser(format_id).parse(str(path)).to_dict()


def test_akn_is_valid():
    xml = to_akn(_doc())
    assert validate(xml) == []
    root = etree.fromstring(xml)
    assert root.find('.//akn:FRBRWork/akn:FRBRuri', AKN).get('value') == '/akn/xx/act/2024-03-13/2024-7'
    assert root.find('.//akn:FRBRExpression/akn:FRBRuri', AKN).get('value') == \
        '/akn/xx/act/2024-03-13/2024-7/eng@2024-03-13'
    # The group, which has no Akoma Ntoso element, is an hcontainer; the empty chapter is kept
    assert root.find('.//akn:part/akn:hcontainer[@name="group"]/akn:article', AKN) is not None
    assert root.find('.//akn:body/akn:chapter/akn:heading', AKN).text == 'Empty'
    # Repeated eIds are made unique
    ids = [e.get('eId') for e in root.iter() if e.get('eId')]
    assert len(ids) == len(set(ids))


def test_amendment_markup():
    root = etree.fromstring(to_akn(_doc()))
    mod = root.find('.//akn:article[@eId="art_2"]//akn:mod', AKN)
    # The quoted text is marked where it stands; the quoted structure follows
    assert mod.text == 'Article 5 is replaced by the following: '
    assert mod.find('akn:quotedText', AKN).text == 'Article 5 Principles'
    assert mod.find('akn:quotedStructure/akn:p', AKN).text == '1. Personal data shall be processed.'
    modification = root.find('.//akn:activeModifications/akn:textualMod', AKN)
    assert modification.get('type') == 'substitution'
    reference = modification.find('akn:destination', AKN).get('href')[1:]
    assert root.find(f'.//akn:TLCReference[@eId="{reference}"]', AKN).get('showAs') == 'Regulation (EU) 2016/679'


def test_akn_round_trip(tmp_path):
    doc = _doc()
    back = _read(to_akn(doc), tmp_path)
    assert {k: v for k, v in counts(back).items() if k != 'characters'} == \
        {k: v for k, v in counts(doc).items() if k != 'characters'}
    assert back['preface'] == 'Data Protection Act'
    assert [c['type'] for c in back['chapters']] == ['part', 'group', 'chapter']
    assert back['articles'][1]['num'] is None
    amendment = back['articles'][1]['children'][0]['amendment']
    assert amendment == doc['articles'][1]['children'][0]['amendment']
    annex = back['annexes'][0]
    assert (annex['num'], annex['heading']) == ('ANNEX I', 'Fees')
    assert annex['children'][1]['table']['rows'] == [['Fee', 'Amount'], ['Registration', '10 EUR']]
    assert annex['children'][1]['text'] == 'Fee | Amount\nRegistration | 10 EUR'
    assert back['conclusions']['conclusion_text'] == 'Done at Brussels.'


def test_leg_package(tmp_path):
    doc = _doc()
    files = leg_files(doc)
    assert list(files) == ['main.xml', 'ACT-2024-7-eng.xml', 'ANNEX-1-2024-7-eng.xml']
    for content in files.values():
        assert validate(content) == []
    main_xml = etree.fromstring(files['main.xml'])
    assert main_xml.find('.//akn:collectionBody/akn:component/akn:documentRef', AKN).get('href') == \
        'ACT-2024-7-eng.xml'
    act = etree.fromstring(files['ACT-2024-7-eng.xml'])
    assert act.find('.//akn:attachment/akn:documentRef', AKN).get('href') == 'ANNEX-1-2024-7-eng.xml'
    assert etree.fromstring(files['ANNEX-1-2024-7-eng.xml']).find('akn:doc', AKN).get('name') == 'ANNEX'

    package = to_leg(doc)
    assert zipfile.ZipFile(io.BytesIO(package)).namelist() == list(files)
    back = _read(package, tmp_path, 'act.leg', 'leg')
    assert {k: v for k, v in counts(back).items() if k != 'characters'} == \
        {k: v for k, v in counts(doc).items() if k != 'characters'}


def test_export_api(tmp_path):
    doc = _doc()
    assert tulit.export(doc) == to_akn(doc)
    target = tmp_path / 'act.leg'
    assert tulit.export(doc, to='leg', path=str(target)) == target.read_bytes()
    with pytest.raises(ValueError, match="Unknown export format 'pdf'"):
        tulit.export(doc, to='pdf')


def test_cli_export(tmp_path):
    source = tmp_path / 'act.json'
    source.write_text(json.dumps(_doc()), encoding='utf-8')
    target = tmp_path / 'act.leg'
    assert main(['export', str(source), '--to', 'leg', '-o', str(target)]) == 0
    assert 'main.xml' in zipfile.ZipFile(target).namelist()
    assert main(['export', str(source), '--to', 'akn', '-o', str(tmp_path / 'act.xml')]) == 0
    assert validate((tmp_path / 'act.xml').read_bytes()) == []


def test_minimal_document_is_valid():
    xml = to_akn({'preface': None, 'preamble': {'citations': [], 'recitals': []}, 'articles': []})
    assert validate(xml) == []
