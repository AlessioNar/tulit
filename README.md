# `tulit`, The Universal Legal Informatics Toolkit

[![PyPI](https://img.shields.io/pypi/v/tulit)](https://pypi.org/project/tulit/)
[![Python](https://img.shields.io/pypi/pyversions/tulit)](https://pypi.org/project/tulit/)
[![Tests (status)](https://img.shields.io/github/actions/workflow/status/AlessioNar/tulit/test.yml?branch=development&label=Tests&logo=github)](https://github.com/AlessioNar/tulit/actions/workflows/test.yml)
[![codecov](https://codecov.io/github/AlessioNar/tulit/graph/badge.svg?token=IBLO3JZCZ5)](https://codecov.io/github/AlessioNar/tulit)
[![License: EUPL 1.2](https://img.shields.io/badge/license-EUPL%201.2-blue)](LICENSE)

`tulit` retrieves legislation from official sources in the EU and its Member States and turns it into **legalJSON**: one structured, schema-validated representation of a legal act, whatever format it was published in.

- **Retrieve** documents from the EU Publications Office (Cellar) and from national and regional legislation portals.
- **Parse** Formex 4, Akoma Ntoso, EUR-Lex HTML and national formats into the same structure: preface, preamble (citations and recitals), divisions, articles, paragraphs, conclusions and annexes.
- **Address** divisions, articles, paragraphs and annexes with ELI-resolvable identifiers (`cpt_II`, `art_5`, `par_2`, `anx_1`), so a JSON fragment maps directly onto its ELI subdivision URI.
- **Capture amendments** as structured objects (action, target act, quoted text or structure) instead of plain prose.

The Formex parser has been verified against the complete corpus of in-force EU legislation (29,790 documents): every act keeps between 97% and 103% of the source text, with no parse errors and 100% schema-valid output.

## Installation

```console
pip install tulit
```

`tulit` requires Python 3.11 or later.

## Quick start

Download an EU regulation from Cellar and convert it to legalJSON:

```python
from tulit.client.eu.cellar import CellarClient
from tulit.parser.xml.formex import Formex4Parser

client = CellarClient(download_dir="./database", log_dir="./logs")
paths = client.download(celex="32024R0903", format="fmx4")  # Interoperable Europe Act

doc = Formex4Parser().parse(paths[0]).to_dict()

article = doc["articles"][0]
print(article["eId"], article["heading"])   # art_1 Subject matter and scope
```

Akoma Ntoso documents are parsed the same way; the variant (AKN4EU, German LegalDocML, Luxembourg) is detected automatically:

```python
from tulit.parser.xml.akomantoso import create_akn_parser

parser = create_akn_parser(file_path="32014L0092.akn")
doc = parser.parse("32014L0092.akn").to_dict()
```

Validate any output against the legalJSON schema:

```python
from tulit.parser.parser import LegalJSONValidator

LegalJSONValidator().validate(doc)  # True
```

## legalJSON at a glance

```json
{
  "preface": "Regulation (EU) 2024/903 of the European Parliament and of the Council ...",
  "preamble": {
    "formula": "THE EUROPEAN PARLIAMENT AND THE COUNCIL OF THE EUROPEAN UNION,",
    "citations": [{"eId": "cit_1", "text": "Having regard to ..."}],
    "recitals": [{"eId": "rct_1", "text": "It is necessary to strengthen ..."}],
    "final": "HAVE ADOPTED THIS REGULATION:"
  },
  "structure": [
    {"eId": "cpt_1", "type": "chapter", "num": "Chapter 1",
     "children": [{"eId": "art_1", "type": "article"}]}
  ],
  "chapters": [{"eId": "cpt_1", "type": "chapter", "num": "Chapter 1", "heading": "General provisions", "parent": null}],
  "articles": [
    {"eId": "art_1", "num": "Article 1", "heading": "Subject matter and scope", "parent": "cpt_1",
     "children": [{"eId": "par_1", "text": "This Regulation lays down ...", "amendment": null}]}
  ],
  "conclusions": {"conclusion_text": "...", "signature": "..."},
  "annexes": [{"eId": "anx_1", "num": "ANNEX", "heading": "...", "children": []}]
}
```

`chapters` and `articles` are flat lists for easy iteration; `structure` holds the nested skeleton of the enacting terms. The full schema is in [`tulit/parser/legaljson_schema.json`](tulit/parser/legaljson_schema.json).

## Supported sources

| Jurisdiction | Source | Client | Parsed formats |
|---|---|---|---|
| European Union | Cellar / EUR-Lex | `CellarClient` | Formex 4, Akoma Ntoso (AKN4EU), XHTML, legacy HTML, legislative proposals |
| Finland | Finlex | `FinlexClient` | Akoma Ntoso |
| France | Légifrance | `LegifranceClient` | Légifrance JSON |
| Germany | Rechtsinformationssystem | `GermanyClient` | LegalDocML (Akoma Ntoso) |
| Ireland | Irish Statute Book | `IrishStatuteBookClient` | download only |
| Italy | Normattiva | `NormattivaClient` | Akoma Ntoso |
| Italy (Veneto) | Bollettino Ufficiale | `VenetoClient` | HTML |
| Luxembourg | Legilux | `LegiluxClient` | Akoma Ntoso |
| Malta | Legislation Malta | `MaltaLegislationClient` | download only |
| Portugal | Diário da República | `PortugalDREClient` | download only |
| Spain | BOE | `BOEClient` | BOE XML |

## Documentation

Full documentation is available at [tulit-docs.readthedocs.io](https://tulit-docs.readthedocs.io/en/latest/index.html). Release notes are in [CHANGELOG.md](CHANGELOG.md).

## Development

```console
git clone https://github.com/AlessioNar/tulit.git
cd tulit
poetry install
poetry run pytest tests/unit
```

End-to-end tests in `tests/e2e` call the live sources and need network access.

## License

`tulit` is released under the [European Union Public Licence v1.2](LICENSE).
