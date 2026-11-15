import unittest
from lxml import etree
from tulit.parser.xml.akomantoso.luxembourg import LuxembourgAKNParser


class TestLuxembourgAKNParser(unittest.TestCase):
    def test_namespaces_override(self):
        p = LuxembourgAKNParser()
        # Ensure the CSD13 namespace is set
        self.assertIn('akn', p.namespaces)
        self.assertIn('scl', p.namespaces)

    def test_extract_eId_from_id_and_fallback(self):
        p = LuxembourgAKNParser()
        elem = etree.Element('article')
        elem.set('id', 'lux_123')
        self.assertEqual(p.extract_eId(elem), 'lux_123')

        # fallback when missing and index provided
        self.assertEqual(p.extract_eId(etree.Element('a'), index=7), 'art_7')


# Trimmed from the Loi du 5 mai 2026 (cybersécurité, Mémorial A 225) and the Loi du 18 février 2026 (A 98)
LEGILUX = '''<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD13" xmlns:scl="http://www.scl.lu">
<act><preface><longTitle><p>Loi du 5 mai 2026 concernant la cybersécurité.</p></longTitle></preface>
<body><chapter id="chapitre_1er"><num>Chapitre 1<sup>er</sup></num><heading>Champ d’application</heading>
<article id="art_1er"><num>Art. 1<sup>er</sup>.</num>
<paragraph><num>(1)</num><alinea><content><p>La loi s’applique au paragraphe 1<sup>er</sup> dudit
<ref href="x">article</ref>, et aux entités.</p></content></alinea>
<alinea><content><p>L’article 3 ne s’applique pas.</p></content></alinea></paragraph>
<paragraph><num>(2)</num><alinea><content><p>Elle s’applique dans les cas suivants :</p>
<ol scl:start="1" scl:symbol="1°"><li>les services sont fournis par :<ol scl:start="1" scl:symbol="a)">
<li>des fournisseurs ;</li><li>des prestataires ;</li></ol></li><li>l’entité est seule.</li></ol>
</content></alinea></paragraph></article>
<article id="art_2"><num>Art. 2.</num><alinea><content><p>L’article 8 du Code de procédure pénale est complété
par un alinéa 2 nouveau, libellé comme suit :</p><embeddedStructure><p>« Il en est de même.<authorialNote>
<p>Note.</p></authorialNote> »</p></embeddedStructure></content></alinea></article></chapter></body>
<attachments><attachment id="attachment_1"><doc name=""><preface><longTitle><p><b>ANNEXE I</b></p>
<p>Secteurs hautement critiques</p></longTitle></preface><mainBody><alinea><content><table>
<tr><td><p>Secteur</p></td><td><p>Type d’entité</p></td></tr>
<tr><td><p>Énergie</p></td><td><ul scl:symbol="dash"><li>Producteurs</li></ul></td></tr>
</table></content></alinea></mainBody></doc></attachment></attachments></act></akomaNtoso>'''


def test_articles_keep_their_whole_text_and_amendments(tmp_path):
    path = tmp_path / 'lu.xml'
    path.write_text(LEGILUX, encoding='utf-8')
    p = LuxembourgAKNParser()
    p.parse(str(path))

    first, second = p.articles
    assert [c['eId'] for c in first['children']] == ['par_1', 'par_2']
    assert first['children'][0]['text'] == ('(1) La loi s’applique au paragraphe 1er dudit article, et aux entités. '
                                            'L’article 3 ne s’applique pas.')
    assert first['children'][1]['text'] == ('(2) Elle s’applique dans les cas suivants: 1° les services sont '
                                            'fournis par: a) des fournisseurs; b) des prestataires; '
                                            '2° l’entité est seule.')
    assert first['children'][0]['amendment'] is None
    amendment = second['children'][0]['amendment']
    assert amendment['action'] == 'add'
    assert amendment['amended_act'].startswith('Code de procédure pénale')
    assert amendment['quoted'] == [{'kind': 'text', 'text': 'Il en est de même.'}]

    [annex] = p.annexes
    assert (annex['eId'], annex['num'], annex['heading']) == ('anx_I', 'ANNEXE I', 'Secteurs hautement critiques')
    assert [c['text'] for c in annex['children']] == ['Secteur | Type d’entité', 'Énergie | – Producteurs']


if __name__ == '__main__':
    unittest.main()
