# `tulit`, The Universal Legal Informatics Toolkit

[![PyPI](https://img.shields.io/pypi/v/tulit)](https://pypi.org/project/tulit/)
[![Python](https://img.shields.io/pypi/pyversions/tulit)](https://pypi.org/project/tulit/)
[![Tests (status)](https://img.shields.io/github/actions/workflow/status/AlessioNar/tulit/test.yml?branch=development&label=Tests&logo=github)](https://github.com/AlessioNar/tulit/actions/workflows/test.yml)
[![codecov](https://codecov.io/github/AlessioNar/tulit/graph/badge.svg?token=IBLO3JZCZ5)](https://codecov.io/github/AlessioNar/tulit)
[![License: EUPL 1.2](https://img.shields.io/badge/license-EUPL%201.2-blue)](LICENSE)

`tulit` retrieves legislation from the official sources of the EU and its Member States and turns it into **legalJSON**: one structured, schema-validated representation of a legal act, whatever format it was published in.

- **Retrieve** documents from the EU Publications Office (Cellar) and from national and regional legislation portals.
- **Parse** Formex 4, Akoma Ntoso, EUR-Lex HTML and national formats into the same structure: preface, preamble (citations and recitals), divisions, articles, paragraphs, conclusions and annexes.
- **Address** divisions, articles, paragraphs and annexes with ELI-resolvable identifiers (`cpt_II`, `art_5`, `par_2`, `anx_1`), so a JSON fragment maps directly onto its ELI subdivision URI.
- **Capture amendments** as structured objects (action, target act, quoted text or structure) instead of plain prose.
- **Export** any act to Akoma Ntoso 3.0 or a LEOS `.leg` package, or get the official Akoma Ntoso where the source publishes it.

The Formex parser has been verified against the complete corpus of in-force EU legislation (29,790 documents): every act keeps between 97% and 103% of the source text, with no parse errors and 100% schema-valid output.

## Installation

```console
pip install tulit
pip install 'tulit[pdf]'   # also read sources published as PDF (Cyprus, Greece, Malta, Portugal; German and Swedish originals)
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

`fetch` downloads the act from Cellar (Formex by default, or `format="xhtml"` / `"html"`), in any language (`language="fra"`), parses it and attaches its metadata: ELI, document date, in-force status and the acts it amends, repeals or corrects.

The same call works for every supported Member State, with the national identifier or an ELI, and either the text as adopted or the consolidated text in force:

```python
dsgvo_at = tulit.fetch("10001597", jurisdiction="AT")                  # Datenschutzgesetz, in force today
lopd = tulit.fetch("BOE-A-2018-16673", jurisdiction="ES",
                   version="consolidated", date="2021-01-01")          # as in force on that date
dpa_ie = tulit.fetch("http://www.irishstatutebook.ie/eli/2018/act/7")  # jurisdiction inferred from the ELI

print(lopd["meta"]["jurisdiction"], lopd["meta"]["version"], lopd["meta"]["version_date"])

# The official file itself, without parsing (also for scanned PDFs tulit cannot read)
scan = tulit.download("constitution/1994/02/17/1994021048", jurisdiction="BE")
scan["path"], scan["meta"]["source"]
```

Any act converts to Akoma Ntoso 3.0 or a LEOS `.leg` package (a zip of Akoma Ntoso documents, as exchanged by LEOS and AKN4EU), both valid against the Akoma Ntoso schema and readable back by tulit; where the source publishes Akoma Ntoso itself (Italy, Finland, Luxembourg, Germany), `native=True` returns its file unchanged:

```python
xml = tulit.export(dsgvo_at, to="akn")
tulit.export(lopd, to="leg", path="lopd.leg")
official = tulit.export(tulit.fetch("L. 160/2019", jurisdiction="IT"), native=True)
```

Every error derives from `tulit.errors.TulitError` (`UnsupportedError` for a jurisdiction, version or identifier a source does not support, `FileLoadError` when it has no such act, `NetworkError` when it cannot be reached).

From the command line:

```console
tulit get 32024R0903 -o 32024R0903.json
tulit get 32016R0679 --format xhtml --language fra
tulit get BOE-A-2018-16673 -j ES --version consolidated --date 2021-01-01
tulit sources
tulit get 300099 -j LV --to leg -o 300099.leg
tulit export 32024R0903.json --to akn -o 32024R0903.xml
tulit dump legi --dir ./dila                     # France: the DILA dump for older texts
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

- 🟢 **Parsed**: available through `tulit.fetch()`, converted to schema-valid legalJSON with ELI-style identifiers
- 🟡 **Partial**: a client or parser exists, but the jurisdiction is not yet available through `fetch`
- ⚪ **Planned**: not yet implemented

In the *Original* and *Consolidated* columns, ✅ means tulit retrieves that version, ⏳ that the source publishes it and support is planned, and — that the source does not publish it.

| | Jurisdiction | Official source | Format | Original | Consolidated | Status | Release |
|---|---|---|---|---|---|---|---|
| 🇪🇺 | European Union | Cellar (Publications Office) | Formex 4, XHTML | ✅ | ✅ | 🟢 Parsed | 0.7.0 |
| 🇦🇹 | Austria | RIS | RIS XML | ✅ | ✅ | 🟢 Parsed | 0.8.0 |
| 🇧🇪 | Belgium | Moniteur belge / Justel (FPS Justice) | HTML | ✅ | ✅ | 🟢 Parsed | 0.10.0 |
| 🇧🇬 | Bulgaria | Държавен вестник (National Assembly) | HTML | ✅ | — | 🟢 Parsed | 0.10.0 |
| 🇭🇷 | Croatia | Narodne novine | HTML + ELI RDF | ✅ | — | 🟢 Parsed | 0.9.0 |
| 🇨🇾 | Cyprus | Official Gazette (Government Printing Office) | PDF | ✅ | — | 🟢 Parsed (`pdf` extra) | 0.10.0 |
| 🇨🇿 | Czechia | e-Sbírka | JSON | ✅ | ✅ | 🟢 Parsed | 0.9.0 |
| 🇩🇰 | Denmark | Retsinformation | LexDania XML | ✅ | ✅ | 🟢 Parsed | 0.8.0 |
| 🇪🇪 | Estonia | Riigi Teataja | Riigi Teataja XML | ✅ | ✅ | 🟢 Parsed | 0.9.0 |
| 🇫🇮 | Finland | Finlex | Akoma Ntoso | ✅ | ✅ | 🟢 Parsed | 0.8.0 |
| 🇫🇷 | France | Journal officiel and Légifrance (DILA open data) | JORF / LEGI XML | ✅ | ✅ | 🟢 Parsed | 0.10.0 |
| 🇩🇪 | Germany | Bundesgesetzblatt (recht.bund.de, bgbl.de archive); Rechtsinformationen des Bundes (test phase) | PDF (original); LegalDocML.de (consolidated) | ✅ | ✅ | 🟢 Parsed (`pdf` extra for originals) | 0.8.0 |
| 🇬🇷 | Greece | Εθνικό Τυπογραφείο (ΦΕΚ) | PDF | ✅ | — | 🟢 Parsed (`pdf` extra) | 0.10.0 |
| 🇭🇺 | Hungary | Nemzeti Jogszabálytár | HTML | ✅ | ✅ | 🟢 Parsed | 0.10.0 |
| 🇮🇪 | Ireland | Irish Statute Book / Revised Acts | ISB XML | ✅ | ✅ | 🟢 Parsed | 0.8.0 |
| 🇮🇹 | Italy | Normattiva | Akoma Ntoso | ✅ | ✅ | 🟢 Parsed | 0.10.0 |
| 🇱🇻 | Latvia | Latvijas Vēstnesis / Likumi.lv | HTML | ✅ | ✅ | 🟢 Parsed | 0.10.0 |
| 🇱🇹 | Lithuania | Teisės aktų registras (e-seimas) | HTML | ✅ | ✅ | 🟢 Parsed | 0.10.0 |
| 🇱🇺 | Luxembourg | Legilux | Akoma Ntoso | ✅ | ✅ | 🟢 Parsed | 0.8.0 |
| 🇲🇹 | Malta | Legislation Malta | PDF | ✅ | ✅ | 🟢 Parsed (`pdf` extra) | 0.9.0 |
| 🇳🇱 | Netherlands | wetten.overheid.nl (BWB) / Staatsblad | BWB XML | ✅ | ✅ | 🟢 Parsed | 0.8.0 |
| 🇵🇱 | Poland | Dziennik Ustaw (Sejm ELI API) | HTML | ✅ | ✅ | 🟢 Parsed | 0.9.0 |
| 🇵🇹 | Portugal | Diário da República (gazette and Legislação Consolidada) | PDF, JSON | ✅ | ✅ | 🟢 Parsed (originals: `pdf` extra) | 0.9.0 |
| 🇷🇴 | Romania | Portal Legislativ (Ministry of Justice) | XML (SOAP), HTML | ✅ | ✅ | 🟢 Parsed | 0.10.0 |
| 🇸🇰 | Slovakia | Slov-Lex | MetaLex XML | ✅ | ✅ | 🟢 Parsed | 0.8.0 |
| 🇸🇮 | Slovenia | PISRS (Ministry of Justice) | HTML | ✅ | ✅ | 🟢 Parsed | 0.10.0 |
| 🇪🇸 | Spain | BOE | BOE XML | ✅ | ✅ | 🟢 Parsed | 0.8.0 |
| 🇸🇪 | Sweden | Svensk författningssamling (Government Offices) / Riksdagen open data | PDF, HTML | ✅ | ✅ | 🟢 Parsed (`pdf` extra for originals) | 0.9.0 |

**Progress: 28 of 28 parsed.** Every Member State and the EU is available through `tulit.fetch()`. Regional legislation is also available for Veneto (Italy). Cyprus, Greece, Malta and Portugal publish PDF, and so do the German Bundesgesetzblatt (German acts as promulgated) and Svensk författningssamling (Swedish acts as adopted, electronic since 1 April 2018: earlier acts are available only consolidated); they need the optional `pdf` extra (`pip install 'tulit[pdf]'`). Portuguese consolidated texts (the codes, the Constitution and the laws the Diário da República consolidates) come as JSON and need no extra. Some acts exist only as scanned PDFs without text (the Moniteur belge before June 1997, the Cypriot Gazette before about 2015, the Bundesgesetzblatt before about 1998); `tulit.download()` returns their official file. `tulit sources` lists what the installed version supports.

### Roadmap

- **0.8.0**:
  - one `tulit.fetch()` for every jurisdiction, addressed by ELI or national identifier, with a choice of original or consolidated text
  - FRBR metadata in `meta` (`jurisdiction`, `language`, `version`, `version_date`)
  - Austria, Denmark, Finland, Germany, Ireland, Luxembourg, the Netherlands, Slovakia and Spain; EU consolidated texts
- **0.9.0**:
  - Croatia, Czechia, Estonia, Malta, Poland, Portugal and Sweden
  - original versions for Austria and the Netherlands
  - optional `pdf` extra for sources published only as PDF
  - structured amendments in the new parsers
- **0.10.0**:
  - Belgium, Bulgaria, Cyprus, France, Greece, Hungary, Italy, Latvia, Lithuania, Romania and Slovenia: all 28 jurisdictions in `fetch`
  - `tulit.download()` for the official file of an act, including scanned PDFs tulit cannot parse
- **1.0.0** (this release):
  - export to Akoma Ntoso 3.0 and LEOS `.leg` packages, and the official Akoma Ntoso where a source publishes it
  - original versions for Germany and Sweden; consolidated texts for Portugal and Romania
  - `tulit dump` for the French DILA dumps
  - a stable API and legalJSON schema (1.0), `tulit.errors`, and a live corpus of 397 real acts checked weekly

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
