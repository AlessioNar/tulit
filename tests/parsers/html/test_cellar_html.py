import unittest
import os
from tulit.parsers.html.cellar import CellarHTMLParser
import json

DATA_DIR = os.path.join(os.path.dirname(__file__), "..\\..\\data\\sources\\eu\\eurlex\\regulations\\html")
file_path = os.path.join(DATA_DIR, "c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.03\\DOC_1.html")


class TestCellarHTMLParser(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None  # Allow full diff if needed
        self.parser = CellarHTMLParser()
        
        # Ensure test file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Test file not found at {file_path}")
        self.parser.get_root(file_path)
    
    def test_get_root(self):
        """Test parsing and root element retrieval from the Akoma Ntoso file."""
        self.assertTrue(os.path.exists(file_path), f"Test file not found at {file_path}")
        self.assertIsNotNone(self.parser.root, "Root element should not be None")      
    
    def test_get_body(self):
        self.parser.get_body()
        self.assertIsNotNone(self.parser.body, "Body element should not be None")      
    
    def test_get_preface(self):
        self.parser.get_preface()
        self.assertEqual(self.parser.preface, "REGULATION (EU) 2024/903 OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL of 13 March 2024 laying down measures for a high level of public sector interoperability across the Union (Interoperable Europe Act)")
    
    def test_get_preamble(self):
        self.parser.get_preamble()
        self.assertIsNotNone(self.parser.preamble, "Preamble element should not be None")      

    def test_get_formula(self):
        self.parser.get_preamble()
        self.parser.get_formula()
        formula = "THE EUROPEAN PARLIAMENT AND THE COUNCIL OF THE EUROPEAN UNION,"
        self.assertEqual(self.parser.formula, formula, "Formula should match expected value")

    def test_get_citations(self):
        self.parser.get_preamble()
        self.parser.get_citations()
        citations =  [
            {
                "eId": "cit_1",
                "text": "Having regard to the Treaty on the Functioning of the European Union, and in particular Article 172 thereof,"
            },
            {
                "eId": "cit_2",
                "text": "Having regard to the proposal from the European Commission,"
            },
            {
                "eId": "cit_3",
                "text": "After transmission of the draft legislative act to the national parliaments,"
            },
            {
                "eId": "cit_4",
                "text": "Having regard to the opinion of the European Economic and Social Committee,"
            },
            {
                "eId": "cit_5",
                "text": "Having regard to the opinion of the Committee of the Regions,"
            },
            {
                "eId": "cit_6",
                "text": "Acting in accordance with the ordinary legislative procedure,"
            }
        ]
        self.assertEqual(self.parser.citations, citations, "Citations should match expected values")
    
    def test_get_recitals(self):
        self.parser.get_preamble()
        self.parser.get_recitals()
        recital = {
            "eId": "rct_1",
            "text": "It is necessary to strengthen the development of the cross-border interoperability of network and information systems which are used to provide or manage public services in the Union, in order to allow public administrations in the Union to cooperate and make public services function across borders. The existing informal cooperation should be replaced by a clear legal framework to enable interoperability across different administrative levels and sectors and to facilitate seamless cross-border data flows for truly European digital services that strengthen the internal market while respecting the principle of subsidiarity. Public sector interoperability has an important impact on the right to free movement of goods, persons, services and capital laid down in the Treaties, as burdensome administrative procedures can create significant obstacles, especially for small and medium-sized enterprises (SMEs)."
        }
        self.assertEqual(self.parser.recitals[0], recital, "Recitals element should match expected value")
        

    def test_get_preamble_final(self):
        self.parser.get_preamble()
        self.parser.get_preamble_final()
        preamble_final = "HAVE ADOPTED THIS REGULATION:"
        self.assertEqual(self.parser.preamble_final, preamble_final, "Preamble final should match expected value")
    
    def test_get_chapters(self):
        self.parser.get_body()
        self.parser.get_chapters()
        chapters = [
            {
                "eId": "cpt_1",
                "num": "Chapter 1",
                "heading": "General provisions"
            },
            {
                "eId": "cpt_2",
                "num": "Chapter 2",
                "heading": "European Interoperability enablers"
            },
            {
                "eId": "cpt_3",
                "num": "Chapter 3",
                "heading": "Interoperable Europe support measures"
            },
            {
                "eId": "cpt_4",
                "num": "Chapter 4",
                "heading": "Governance of cross-border interoperability"
            },
            {
                "eId": "cpt_5",
                "num": "Chapter 5",
                "heading": "Interoperable Europe planning and monitoring"
            },
            {
                "eId": "cpt_6",
                "num": "Chapter 6",
                "heading": "Final provisions"
            }
        ]
        self.assertEqual(self.parser.chapters, chapters, "Chapters elements should match expected values")        
        

    def test_get_articles(self):
        """Test parsing articles from an HTML file."""
        # Parse the body and articles using the parser
        self.parser.get_body()
        self.parser.get_articles()
        article_1 = {
            "eId": "art_1",
            "num": "Article 1",
            "heading": "Subject matter and scope",
            "children": [
                {
                    "eId": "001.001",
                    "text": "1. This Regulation lays down measures that promote the cross-border interoperability of trans-European digital public services, thus contributing to the interoperability of the underlying network and information systems by establishing common rules and a governance framework."
                },
                {
                    "eId": "001.002",
                    "text": "2. This Regulation applies to Union entities and public sector bodies that regulate, provide, manage or implement trans-European digital public services."
                },
                {
                    "eId": "001.003",
                    "text": "3. This Regulation applies without prejudice to the competence of Member States to define what constitutes public services or to their ability to establish procedural rules for or to provide, manage or implement those services."
                },
                {
                    "eId": "001.004",
                    "text": "4. This Regulation is without prejudice to the competence of Member States with regard to their activities concerning public security, defence and national security."
                },
                {
                    "eId": "001.005",
                    "text": '5. This Regulation does not entail the supply of information the disclosure of which would be contrary to the essential interests of Member States\' public security, defence or national security.'
                }
            ]
        }
        
        article_2 = {
            "eId": "art_2",
            "num": "Article 2",
            "heading": "Definitions",
            "children": [
                {
                    "eId": "002.001",
                    "text": "For the purposes of this Regulation, the following definitions apply:"
                },
                {
                    "eId": "002.002",
                    "text": "'cross-border interoperability' means the ability of Union entities and public sector bodies of Member States to interact with each other across borders by sharing data, information and knowledge through digital processes in line with the legal, organisational, semantic and technical requirements related to such cross-border interaction;"
                },
                {
                    "eId": "002.003",
                    "text": "'trans-European digital public services' means digital services provided by Union entities or public sector bodies to one another or to natural or legal persons in the Union, and requiring interaction across Member State borders, among Union entities or between Union entities and public sector bodies, by means of their network and information systems;"
                },
                {
                    "eId": "002.004",
                    "text": "'network and information system' means a network and information system as defined in Article 6, point (1), of Directive (EU) 2022/2555 of the European Parliament and of the Council;"
                },
                {
                    "eId": "002.005",
                    "text": "'interoperability solution' means a reusable asset concerning legal, organisational, semantic or technical requirements to enable cross-border interoperability, such as conceptual frameworks, guidelines, reference architectures, technical specifications, standards, services and applications, as well as documented technical components, such as source code;"
                },
                {
                    "eId": "002.006",
                    "text": "'Union entities' means the Union institutions, bodies, offices and agencies set up by, or on the basis of, the TEU, the Treaty on the functioning of European Union or the Treaty establishing the European Atomic Energy Community;"
                },
                {
                    "eId": "002.007",
                    "text": "'public sector body' means a public sector body as defined in Article 2, point (1), of Directive (EU) 2019/1024 of the European Parliament and of the Council;"
                },
                {
                    "eId": "002.008",
                    "text": "'data' means data as defined in Article 2, point (1), of Regulation (EU) 2022/868 of the European Parliament and of the Council;"
                },
                {
                    "eId": "002.009",
                    "text": "'machine-readable format' means a machine-readable format as defined in Article 2, point (13), of Directive (EU) 2019/1024;"
                },
                {
                    "eId": "002.010",
                    "text": "'GovTech' means technology-based cooperation between public and private sector actors supporting public sector digital transformation;"
                },
                {
                    "eId": "002.011",
                    "text": "'standard' means a standard as defined in Article 2, point (1), of Regulation (EU) No 1025/2012 of the European Parliament and of the Council;"
                },
                {
                    "eId": "002.012",
                    "text": "'ICT technical specification' means ICT technical specification as defined in Article 2, point (5), of Regulation (EU) No 1025/2012;"
                },
                {
                    "eId": "002.013",
                    "text": "'open source licence' means a licence whereby the reuse, redistribution and modification of software is permitted for all uses on the basis of a unilateral declaration by the right holder that may be subject to certain conditions, and where the source code of the software is made available to users indiscriminately;"
                },
                {
                    "eId": "002.014",
                    "text": "'highest level of management' means a manager, management or coordination and oversight body at the most senior administrative level, taking account of the high-level governance arrangements in each Union entity;"
                },
                {
                    "eId": "002.015",
                    "text": "'interoperability regulatory sandbox' means a controlled environment set up by a Union entity or a public sector body for the development, training, testing and validation of innovative interoperability solutions, where appropriate in real world conditions, supporting the cross-border interoperability of trans-European digital public services for a limited period of time under regulatory supervision;"
                },
                {
                    "eId": "002.016",
                    "text": "'binding requirement' means an obligation, prohibition, condition, criterion or limit of a legal, organisational, semantic or technical nature, which is set by a Union entity or a public sector body concerning one or more trans-European digital public services and which has an effect on cross-border interoperability."
                }
            ]
            }
        
        article_3 = {
            "eId": "art_3",
            "num": "Article 3",
            "heading": "Interoperability assessment",
            "children": [
                {
                    "eId": "003.001",
                    "text": "1. Before taking a decision on new or substantially modified binding requirements, a Union entity or a public sector body shall carry out an interoperability assessment. Where, in relation to binding requirements, an interoperability assessment has already been carried out or where binding requirements are implemented by solutions provided by Union entities, the public sector body concerned shall not be required to carry out a further interoperability assessment in relation to those requirements. A single interoperability assessment may be carried out to address a set of binding requirements. The Union entity or public sector body concerned may also carry out the interoperability assessment in other cases."
                },
                {
                    "eId": "003.002",
                    "text": "2. An interoperability assessment shall, in an appropriate manner, identify and assess the following: (a) the effects of the binding requirements on cross-border interoperability, using the European Interoperability Framework referred to in Article 6as a support tool; (b) the stakeholders to which the binding requirements are relevant; (c) the Interoperable Europe solutions referred to in Article 7 that support the implementation of the binding requirements. The Union entity or public sector body concerned shall publish, in a machine-readable format facilitating automated translation, a report presenting the outcome of the interoperability assessment, including the items listed in the Annex, on an official website. It shall share that report electronically with the Interoperable Europe Board established pursuant to Article 15 (the 'Board'). The requirements laid down in this paragraph shall not restrict existing Member States' rules on access to documents. The publication of that report shall not compromise intellectual property rights or trade secrets, public order or security."
                },
                {
                    "eId": "003.003",
                    "text": "3. Union entities and public sector bodies may decide which body is to provide the necessary support to carry out the interoperability assessment. The Commission shall provide technical tools to support the interoperability assessment, including an online tool to facilitate the completion of the report and its publication on the Interoperable Europe portal referred to in Article 8."
                },
                {
                    "eId": "003.004",
                    "text": "4. The Union entity or public sector body concerned shall consult recipients of the services directly affected, including citizens, or their representatives. That consultation shall be without prejudice to the protection of commercial or public interests or the security of such services."
                },
                {
                    "eId": "003.005",
                    "text": "5. By 12 January 2025, the Board shall adopt the guidelines referred to in Article 15(5), point (a)."
                }
            ]
        }
        self.assertEqual(self.parser.articles[0], article_1, "Article element should match expected value")
        self.assertEqual(self.parser.articles[1], article_2, "Article element should match expected value")
        self.assertEqual(self.parser.articles[2], article_3, "Article element should match expected value")
        
    def test_get_conclusions(self):
        self.parser.get_conclusions()
        self.assertIsNotNone(self.parser.conclusions, "Conclusions element should not be None")      
        
# Run the tests
if __name__ == "__main__":
    unittest.main()

