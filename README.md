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

## Coverage

The goal of tulit is to cover the legislation of all 27 EU Member States and the EU itself, from **official sources only**, with both the **original** text and the **consolidated** (in-force) text wherever the source publishes them.

Status levels:

- 🟢 **Parsed**: downloads and converts to schema-valid legalJSON with ELI-style identifiers
- 🟡 **Partial**: downloads, parsing incomplete or limited to one text version
- ⚪ **Planned**: not yet implemented

| | Jurisdiction | Official source | Best format | Original | Consolidated | Status | Target |
|---|---|---|---|---|---|---|---|
| 🇪🇺 | European Union | Cellar / EUR-Lex | Formex 4, XHTML | ✅ | ✅ (Formex) | 🟢 Parsed (originals; verified on the full in-force corpus) | 0.8.0 consolidated |
| 🇦🇹 | Austria | RIS | RIS XML | ✅ | ✅ | ⚪ Planned | 0.8.0 |
| 🇧🇪 | Belgium | Justel / Moniteur belge | HTML | ✅ | ✅ | ⚪ Planned | 0.10.0 |
| 🇧🇬 | Bulgaria | Държавен вестник | HTML | ✅ | — | ⚪ Planned | 0.10.0 |
| 🇭🇷 | Croatia | Narodne novine | HTML + RDFa | ✅ | — | ⚪ Planned | 0.9.0 |
| 🇨🇾 | Cyprus | Official Gazette | PDF | ✅ | — | ⚪ Planned | 0.10.0 |
| 🇨🇿 | Czechia | e-Sbírka | JSON | ✅ | ✅ | ⚪ Planned | 0.9.0 |
| 🇩🇰 | Denmark | Retsinformation | LexDania XML | ✅ | ✅ | ⚪ Planned | 0.8.0 |
| 🇪🇪 | Estonia | Riigi Teataja | Riigi Teataja XML | ✅ | ✅ | ⚪ Planned | 0.9.0 |
| 🇫🇮 | Finland | Finlex | Akoma Ntoso | ✅ | ✅ | 🟢 Parsed | 0.8.0 consolidated |
| 🇫🇷 | France | Légifrance (DILA) | LEGI XML, JSON | ✅ | ✅ | 🟡 Partial | 0.8.0 |
| 🇩🇪 | Germany | Rechtsinformationen des Bundes | LegalDocML.de | ✅ | ✅ | 🟢 Parsed | 0.8.0 consolidated |
| 🇬🇷 | Greece | Εθνικό Τυπογραφείο (ΦΕΚ) | PDF | ✅ | — | ⚪ Planned | 0.10.0 |
| 🇭🇺 | Hungary | Nemzeti Jogszabálytár | HTML | ✅ | ✅ | ⚪ Planned | 0.10.0 |
| 🇮🇪 | Ireland | Irish Statute Book / Revised Acts | XML | ✅ | ✅ | 🟡 Partial (download only) | 0.8.0 |
| 🇮🇹 | Italy | Normattiva | Akoma Ntoso | ✅ | ✅ | 🟢 Parsed | 0.8.0 new API |
| 🇱🇻 | Latvia | Likumi.lv | HTML | ✅ | ✅ | ⚪ Planned | 0.10.0 |
| 🇱🇹 | Lithuania | Teisės aktų registras / e-seimas | Text, DOCX | ✅ | ✅ | ⚪ Planned | 0.10.0 |
| 🇱🇺 | Luxembourg | Legilux | Akoma Ntoso | ✅ | ✅ | 🟢 Parsed | 0.8.0 consolidated |
| 🇲🇹 | Malta | Legislation Malta | PDF | ✅ | ✅ | 🟡 Partial (download only) | 0.9.0 |
| 🇳🇱 | Netherlands | wetten.overheid.nl (BWB) | BWB XML | ✅ | ✅ | ⚪ Planned | 0.8.0 |
| 🇵🇱 | Poland | Dziennik Ustaw / ISAP | HTML, JSON, PDF | ✅ | ✅ (PDF) | ⚪ Planned | 0.9.0 |
| 🇵🇹 | Portugal | Diário da República | PDF | ✅ | ✅ (JS only) | 🟡 Partial (download only) | 0.9.0 |
| 🇷🇴 | Romania | Portal Legislativ | Text | ✅ | ✅ | ⚪ Planned | 0.10.0 |
| 🇸🇰 | Slovakia | Slov-Lex | MetaLex XML | ✅ | ✅ | ⚪ Planned | 0.8.0 |
| 🇸🇮 | Slovenia | PISRS | HTML (JS only) | ✅ | ✅ | ⚪ Planned | 0.10.0 |
| 🇪🇸 | Spain | BOE | BOE XML | ✅ | ✅ | 🟢 Parsed (originals) | 0.8.0 consolidated |
| 🇸🇪 | Sweden | Riksdagen / Regeringskansliet | Text | ✅ | ✅ | ⚪ Planned | 0.9.0 |

**Progress: 6 of 28 parsed, 4 partial, 18 planned.** Regional legislation is also available for Veneto (Italy). Sources published only as PDF or as JavaScript applications need the optional PDF and browser extras planned for 0.9.0.

### Roadmap

- **0.8.0**:
  - one `tulit.fetch()` for every jurisdiction, addressed by ELI or national identifier, with a choice of original or consolidated text
  - a common client interface and per-country tests
  - updated clients for Italy, Finland, Spain, Ireland and Portugal
  - Austria, Denmark, the Netherlands and Slovakia
- **0.9.0**:
  - optional `tulit[pdf]` and browser extras
  - Croatia, Czechia, Estonia, Poland, Sweden, Malta and Portugal
- **0.10.0**: Belgium, Bulgaria, Cyprus, Greece, Hungary, Latvia, Lithuania, Romania and Slovenia

### Access to law and reuse

Everyone has the right to know the law that binds them. The Union is founded on the rule of law (Article 2 TEU), and legal certainty requires that laws be published and accessible to the people they apply to: the Court of Justice has held that an act not properly published in the Official Journal cannot be enforced against individuals (Case C-161/06, *Skoma-Lux*). EU citizens can live, work, study and do business in any Member State (Articles 20, 21 and 45 TFEU; Article 45 of the Charter of Fundamental Rights), so the laws they need to know are not only their own country's but those of all 27 Member States and of the Union.

That is the basis for tulit's approach to reuse:

- **Official texts are public.** Legislation, as published by the authority that enacted it, is there to be read, quoted and shared. Most Member States exclude official legislative texts from copyright (for example Germany, § 5 UrhG; Austria, § 7 UrhG; Italy, Article 5 of the Copyright Act), as the Berne Convention allows (Article 2(4)). EU legislation may be reused free of charge (Commission Decision 2011/833/EU), and the Open Data Directive ((EU) 2019/1024) encourages the reuse of public-sector data.
- **tulit only fetches from official sources.** It retrieves each act directly from the publishing authority and changes its form, not its content. Every legalJSON document records where it came from in `meta.source` and `meta.eli`.
- **Attribution travels with the data.** tulit treats the texts it retrieves as reusable under CC BY 4.0, with attribution to the official source.

The terms of each portal still apply to the portal itself: its database, its editorial additions such as annotations and summaries, and its rate limits. Please use the sources considerately.

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
