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

Fetch an EU act as validated legalJSON in one call:

```python
import tulit

doc = tulit.fetch("32024R0903")  # Interoperable Europe Act

article = doc["articles"][0]
print(article["eId"], article["heading"])  # art_1 Subject matter and scope
print(doc["meta"]["eli"])                  # http://data.europa.eu/eli/reg/2024/903/oj
```

`fetch` downloads the act from Cellar (Formex by default, or `format="xhtml"` / `"html"`), in any language (`language="FRA"`), parses it and attaches its metadata: ELI, document date, in-force status and the acts it amends, repeals or corrects.

From the command line:

```console
tulit get 32024R0903 -o 32024R0903.json
tulit get 32016R0679 --format xhtml --language FRA
tulit parse --format akn 32014L0092.akn
tulit formats
```

Local files are parsed through the parser registry; Akoma Ntoso variants (AKN4EU, German LegalDocML, Luxembourg) are detected automatically:

```python
from tulit.parser.registry import get_parser

parser = get_parser("akn", file_path="32014L0092.akn")
doc = parser.parse("32014L0092.akn").to_dict()
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
     "children": [{"eId": "par_1", "text": "1. This Regulation lays down ...", "amendment": null}]}
  ],
  "conclusions": {"conclusion_text": "...", "signature": "..."},
  "annexes": [{"eId": "anx_1", "num": "ANNEX", "heading": "...", "children": []}],
  "meta": {"celex": "32024R0903", "eli": "http://data.europa.eu/eli/reg/2024/903/oj",
           "date_document": "2024-03-13", "in_force": true, "amends": [], "repeals": []}
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
