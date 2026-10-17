# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added

- **Latvia in `fetch`**: the original version from the official publication in Latvijas Vēstnesis (vestnesis.lv) and the consolidated version from likumi.lv, as in force today or on a date, by likumi.lv identifier or link. Laws, Cabinet regulations (with their attachments) and amending acts, whose amendments are structured.
- **Belgium in `fetch`**: acts as published in the Moniteur belge / Belgisch Staatsblad (from June 1997) and Justel's consolidated texts, in French and Dutch, by ELI (`https://www.ejustice.just.fgov.be/eli/loi/2018/07/30/2018040581`) or 'loi/2018/07/30/2018040581'. The consolidated version in force on a date is chosen among Justel's archived versions (today's by default, as Justel's latest text can hold amendments not yet in force). Federal laws, royal and ministerial orders, Community and Regional decrees and ordinances, with structured amendments, tables and annexes.
- **Cyprus in `fetch`**: laws as published in the Official Gazette of the Republic (Government Printing Office, PDF), by number ('125(I)/2018', 'Ν. 125(Ι)/2018'). The issue is found through the Gazette's full-text search (issues from about 2015) and the law cut out of it; section headings come from the margin notes. Cyprus publishes no official consolidated texts.
- **Italy in `fetch`**: state legislation from Normattiva's Akoma Ntoso export, the original text (Normattiva's export for the date of publication in the Gazzetta Ufficiale) and the consolidated text in force today or on a date, by citation ('decreto legislativo 10 agosto 2018, n. 101', 'D.Lgs. 101/2018', 'L. 160/2019'), URN, Normattiva or Gazzetta Ufficiale link, or Gazzetta date and code. Editorial notes are left out, amendments are structured, and attachments (e.g. ratified treaties) become annexes.
- **`tulit.download`**: the official file of an act without parsing it, for any source. Acts published only as scanned PDFs are returned this way (`fetch` reports them): the Moniteur belge before June 1997 (with the page where the act starts) and the Cypriot Official Gazette before about 2015, whose Annex One issues are found by issue number ('4252/2010', '4252, 23.7.2010') or link.
- **Bulgaria in `fetch`**: acts as published in the official section of the State Gazette (Държавен вестник, National Assembly), since 2003, by issue and title ('ДВ, бр. 38 от 2016 г., Закон за електронната идентификация'), exact title, or material number / link on dv.parliament.bg. Laws, codes, orders and decrees with their chapters and sections, supplementary provisions (§ N, as top-level `provisions` divisions), structured amendments, appendices and annexed texts. Bulgaria publishes no official consolidated texts.
- **France in `fetch`**, without credentials, from the DILA open data (Licence Ouverte): texts as published in the Journal officiel and Légifrance's consolidated texts, by title ('Décret n° 2026-959 du 15 octobre 2026'), ELI, JORFTEXT identifier or NOR. Texts published since the last global dump (13 July 2025) come from the daily JORF archives; their consolidated version, in force on any date, is rebuilt from the daily LEGI archives. Older texts and long consolidations read the global JORF and LEGI dumps once downloaded and extracted (`dump_dir`). A new DILA XML parser (`fr-dila`) gives visas, divisions, articles, annexes, signatures and structured amendments.
- **Romania in `fetch`**: acts as published in Monitorul Oficial from the Ministry of Justice's Portal Legislativ, through its web service, by citation ('Legea nr. 190/2018', 'OUG nr. 57/2019', 'HG nr. 677/2017'). Laws, emergency and simple ordinances and Government decisions, from short acts to the Civil and Administrative Codes, with article titles, annexes, signatures and structured amendments, including the chapters and articles an amending act quotes. The web service gives no consolidated forms.
- **Slovenia in `fetch`**: acts from PISRS (Ministry of Justice), the text as published in the Uradni list RS and PISRS's consolidated versions (neuradno prečiščeno besedilo), the one that applies on a date, by PISRS id ('ZAKO7959'), abbreviation ('ZVOP-2'), Official Gazette number ('2022-01-4187') or link, or Gazette citation ('Uradni list RS, št. 163/22'). Laws and regulations with parts and chapters, article headings and structured amendments.
- **Hungary in `fetch`**: acts from the Nemzeti Jogszabálytár, as promulgated in the Magyar Közlöny (közlönyállapot) and in the time state in force today or on a date, by citation ('2011. évi CXII. törvény', '335/2005. (XII. 29.) Korm. rendelet'), NJT id or link, or ELI (`https://njt.jog.gov.hu/eli/TV/2011/112`). Laws and decrees with parts, chapters, subtitles, sections and annexes; amending provisions carry structured amendments, the act they amend resolved through abbreviations ('Adatvagyontv.') or the title.
- **Lithuania in `fetch`**: acts as published in the Register of Legal Acts (TAR) and its consolidated versions (suvestinės redakcijos), in force today or on a date, through the Seimas portal e-seimas.lrs.lt, by TAR identification code ('2018-11733'), Seimas act number ('I-1374'), document id ('TAIS.29193') or e-seimas link. Laws, Government resolutions and orders with the rules they approve, amending acts with structured amendments; the editorial notes of consolidated versions are left out.
- **Greece in `fetch`**: laws, presidential decrees and acts of legislative content as published in Part A of the Government Gazette (ΦΕΚ, National Printing House, PDF), by number ('ν. 4624/2019', 'π.δ. 70/2015'), by issue ('ΦΕΚ Α 137/29.08.2019') or by the PDF link. The search of search.et.gr finds the issue; a decree sharing its issue with others is picked by its number. The two columns are read in turn, the masthead, page headers and table of contents left out; amendments are structured. Greece publishes no official consolidated texts.

## [0.9.0] - 2026-10-17
### Added

- **Seven new jurisdictions in `fetch`**, each with a parser to legalJSON and per-country tests (17 of 28 now):
  - Croatia: acts as published in Narodne novine, with their ELI metadata (dates, repealed and amended acts). Croatia publishes no official consolidated texts.
  - Czechia: original and consolidated versions from e-Sbírka, the version in force on any date; consolidated versions are legally binding since 2024.
  - Estonia: the original text and every consolidated text from Riigi Teataja, by abbreviation ('IKS'), text id or URL, the text in force on a date.
  - Malta: consolidated Chapters ('Cap. 586', in English or Maltese) and Acts as passed ('Act XII of 2018') from Legislation Malta PDFs; the original of a Chapter is the Act that enacted it. Article headings come from the side notes.
  - Poland: acts as published in the Journal of Laws and their official consolidated texts (tekst jednolity) through the Sejm ELI API, by 'Dz.U. 2018 poz. 1000', 'DU/2018/1000' or ELI.
  - Portugal: acts as published in the Diário da República PDF, by citation ('Lei n.º 58/2019, de 8 de agosto') or ELI, in the current layout and the older two-column one.
  - Sweden: consolidated statutes (SFS) from the Riksdag open data; where an amendment is pending, the version of each section in force on the date is kept.
- **Original versions for Austria and the Netherlands**: laws as adopted from the authentic Federal Law Gazette (BGBl., from 2004) and from the Staatsblad (from 1995), by gazette reference or from a consolidated law's identifier.
- **`pdf` extra**: `pip install 'tulit[pdf]'` installs pdfplumber for sources published only as PDF. `tulit.parser.pdf.layout` reads positioned lines, two-column pages column by column, and side notes apart from the body.
- **Structured amendments** in the new parsers (Austria BGBl., Netherlands Staatsblad, Estonia, Poland, Croatia, Czechia, Portugal): each amending instruction carries its action (replace, insert, add, delete), the amended act and the quoted new text.
- **GitHub releases**: the publish workflow creates a GitHub release for each tag, with the package files and the version's changelog section.
- `BodyBuilder.division` accepts an explicit nesting rank and `ChildrenBuilder.add` an eId token, for formats whose structure is explicit; eIds accept Roman numbers with a letter suffix (`art_XIIIA`).

### Changed

- Read the Docs builds the package from the repository instead of installing it from PyPI, so the API reference matches the code of each version.
- Austria and the Netherlands infer the version from the identifier: a gazette reference gives the law as adopted, a consolidated identifier the law in force.

### Known limitations

- Italy (Normattiva's new API) and France (Légifrance, which needs PISTE API credentials) are still not in `fetch`.
- Portuguese consolidated texts are published only as a JavaScript application; Swedish originals only as PDF.
- Maltese Acts and Legal Notices are printed in Maltese and English side by side: use `language='eng'`.
- Polish consolidated texts are the official teksty jednolite: amendments published after the latest one are not included; one without HTML yet falls back to the previous one.
- Austrian gazette issues before 2004 and Dutch Staatsblad issues before 1995 are scanned PDFs and not available.

## [0.8.0] - 2026-10-17
### Added

- **One `fetch` for every jurisdiction**: `tulit.fetch(identifier, jurisdiction=..., version=..., date=..., language=...)` retrieves an act from the official source of the EU or a Member State, addressed by its national identifier or ELI (the jurisdiction is inferred from ELI URIs), in its **original** version (as adopted) or its **consolidated** version (in force on a date). Unsupported versions, languages and options raise `ValueError` before anything is downloaded.
- **Sources** (`tulit.sources`): one `Source` per jurisdiction with a common interface (`retrieve()` returning a `Retrieval`), a registry (`get_source`, `list_sources`, `source_for_eli`) and the `tulit sources` command. The CLI `get` command takes `-j/--jurisdiction`, `--version` and `--date`.
- **New jurisdictions**, each with a parser to legalJSON and per-country tests:
  - Austria: consolidated federal law from RIS (OGD API), parsed from RIS XML.
  - Denmark: acts and consolidations (lovbekendtgørelser) from Retsinformation, parsed from LexDania XML.
  - Finland: original and consolidated statutes from the Finlex Akoma Ntoso API, in Finnish or Swedish.
  - Germany: the version in force of federal acts from Rechtsinformationen des Bundes (test phase), parsed from LegalDocML.de.
  - Ireland: Acts as enacted from the Irish Statute Book and Revised Acts from the Law Reform Commission, parsed from their XML.
  - Luxembourg: original and consolidated acts from Legilux, choosing the consolidation in force on a date.
  - The Netherlands: consolidated acts from the Basiswettenbestand (SRU), parsed from BWB XML.
  - Slovakia: original and consolidated acts from Slov-Lex, parsed from MetaLex XML.
  - Spain: original and consolidated acts from the BOE consolidated-legislation API, choosing the version in force on a date.
- **EU consolidated texts**: `fetch("32016R0679", version="consolidated", date=...)` finds the consolidated version in Cellar. EU ELIs are accepted as identifiers.
- **FRBR metadata**: `meta` records `jurisdiction`, `language`, `version` and `version_date`, identifying the expression of the act, in preparation for Akoma Ntoso and `.leg` export.
- **Structure builders** (`tulit.parser.structure`): shared helpers that number divisions, articles and their children with ELI-style eIds, used by the new parsers.
- **Access to law**: the README explains the basis for reusing legislation retrieved by tulit, and tracks coverage of the 27 Member States and the EU.

### Fixed

- **Clients no longer exit the program**: the Finlex, Normattiva, Veneto, Legilux, Portugal, Irish Statute Book and Malta clients raised `SystemExit` on errors; they now raise `NetworkError`, `FileLoadError` or `ContentTypeError`.
- **Finlex**: requests send a User-Agent (the API rejects them otherwise); Akoma Ntoso sections and subsections count as divisions only when they contain articles.
- **Portugal**: the Diário da República HTML is now a JavaScript application with no text, so the client downloads PDF by default and reports the HTML shell as `ContentTypeError`.
- **German LegalDocML parser**: documents from the federal portal produced no output (the namespace was hard-coded and the document root was never loaded). The parser now reads the namespace from the document, keeps title and short title apart, and returns one child per Absatz with its list items in order.
- **Akoma Ntoso parser**: a missing preamble no longer raises when the preface is read.

### Known limitations

- Austria, Germany and the Netherlands provide consolidated texts only; original versions (BGBl, Staatsblad) are planned for 0.9.0.
- Denmark, Finland, Ireland and Germany return the current consolidated version; a date cannot be selected.
- Italy and France have clients and parsers but are not yet available through `fetch`.
- In EU consolidated texts, the divisions above article level (chapters, sections) are not yet recognised. The children of annexes and of legacy Cellar HTML documents use positional eIds.

## [0.7.0] - 2026-10-17
### Added

- **`tulit.fetch()`**: one call turns a CELEX number into validated legalJSON. It downloads the act from Cellar in the requested format (`fmx4`, `xhtml`, `html`) and language, parses it with the matching parser, attaches the work metadata as `meta` and validates the result against the legalJSON schema.
- **Command-line interface**: `tulit get <CELEX>` downloads an act as legalJSON, `tulit parse <path> --format <id>` converts local files, and `tulit formats` lists the available parsers. Also available as `python -m tulit`.
- **Cellar metadata**: `CellarClient.get_metadata()` returns the legalJSON `meta` object for an act: ELI, Cellar UUID, document date, in-force status and the acts it amends, repeals and corrects.
- **Language selection**: `CellarClient.download()` takes a `language` argument (three-letter code, default `ENG`) instead of always downloading English.

### Fixed

- **Parser registry**: `get_parser_registry()` returned an empty registry, so `get_parser()` could not work. The built-in parsers are now registered under format ids and aliases (`formex`/`fmx4`, `akn`, `xhtml`, `html`, ...). `register_parser()` no longer raises `TypeError`, and `create_akn_parser()` falls back to the standard parser as intended.
- **Logging**: clients no longer call `logging.basicConfig`, which printed INFO logs in every application using tulit; the proposal, Veneto and Formex parsers and the Legilux client log through loggers instead of `print()`. `log_dir` is now optional for all clients.
- **Formex paragraph text**: block elements are separated when article text is flattened, so paragraphs read `1. This Regulation ...` instead of `1.This Regulation ...` and list points `(a) first` instead of `(a)first`.

### Changed

- The getting-started guide is rewritten around `fetch`, the CLI and the legalJSON structure, with examples checked against the current API.

## [0.6.0] - 2026-10-17
### Added

- **Parser Parity Across Formats**: The Akoma Ntoso and Cellar HTML parsers now emit the same legalJSON features as the Formex parser: typed divisions above article level (part/title/chapter/section/subsection) with parent links, ELI-resolvable eIds (`cpt_I`, `art_1`, `par_2`, `unp_N`), per-article `parent` links, and the hybrid `structure` skeleton tree.

- **Cellar HTML Annexes and Attachments**: `CellarHTMLParser` extracts annexes (`anx_*` divs at any nesting) uniform with articles, plus attached material published with the act — agreements, joint declarations, additional acts in multi-act OJ pieces, and wrapper-level content — as `att_N` annex entries.

- **Cellar HTML Corpus-Grade Extraction**: generic document-order block walk for OJ xhtml articles (mixed paragraph/table content folded into `par_N`/`unp_N` children), narrative preambles (State-aid decisions) mapped onto citations/recitals, enacting-terms content outside articles kept as a pseudo-article, conclusions from the final-provisions block, symmetric footnote policy (dropped act-side, kept annex-side, inline markers always preserved).

- **Old-Format (TXT_TE) Extraction Rework**: title-block preface, generalized citation forms, all three recital styles ('Whereas:' + numbered, bare 'Whereas', narrative '(N)'), signature-block conclusions, annex/agreement capture after the signature, a whole-flow fallback for non-legislative documents and a lossless leftover net so no document text is dropped.

- **AKN Variant Unification**: the three near-duplicate `get_articles` implementations (base, AKN4EU, Luxembourg) merged into one template with `_extractor_id_attr` and `_extract_article_children` hooks; AKN children are aggregated to paragraph level (`par_N`/`unp_N`) and quoted structures are excluded from article/division discovery.

- **Corpus-Scale Verification (HTML)**: the Cellar HTML parser was verified against the in-force legislation HTML dump with the same alphanumeric-coverage gate used for Formex.

### Fixed

- **cellar_standard Validation Drift**: `parse(validate=True)` now validates the canonical `to_dict()` output instead of a hand-rolled dict that had drifted from the schema (and unpacked the validator's boolean as a tuple); `parse()` on an empty directory returns the parser, not a dict.
- **Nested Table Double-Counting**: HTML tables render only their own rows; nested tables are no longer counted twice.
- **Article Truncation in Old Format**: article extraction no longer stops at ordinary prose starting with 'For the …'.
- **PyPI Release Workflow**: publishing now uses PyPI trusted publishing (`pypa/gh-action-pypi-publish`) and runs only on tag pushes; the previous job failed on every release because Poetry was not installed in the publish job.
- **Test Isolation**: client tests download into a temporary directory instead of overwriting tracked fixtures in `tests/data`, and the obsolete coverage-badge hook no longer writes `.github/badges/` on every run.

### Changed

- CI runs unit tests on `development-*` branches too, and GitHub Actions are updated to Node 24 versions.
- `coverage.xml` is no longer tracked (coverage is reported through Codecov).

## [0.5.0] - 2026-07-24
### Added

- **Formex Annex Extraction**: `Formex4Parser` now extracts annexes, uniform with articles (`eId`, `num`, `heading`, `children`). Handles multi-file documents, `INCL.ELEMENT` file inclusions (resolved and deduplicated), standalone-annex and corrigendum documents, structured tables (`table` key with caption, rows and notes), definition lists, nested lists and annotation groups.

- **Structured Amendment Representation**: Amending provisions in articles and annexes carry a structured `amendment` object modelled on the Akoma Ntoso mod/quotedText/quotedStructure pattern: `{action, instruction, amended_act, quoted: [{kind: structure|text, ...}]}`. Detection distinguishes genuine amendments from definitions and other quoted text (verb-frame plus structural-referent analysis; `QUOT.S` blocks as strong evidence).

- **ELI-Resolvable Identifiers**: All eIds follow the EU Publications Office *subdivision* authority table used in ELI subdivision URIs: divisions `prt_`/`tit_`/`cpt_`/`sct_`/`sbs_`, articles `art_1`/`art_16a`, paragraphs `par_N`, unnumbered blocks `unp_N`, annexes by position — so JSON fragments map directly onto resolvable ELI URIs.

- **Typed Division Hierarchy**: `chapters` now lists every division above article level (part/title/chapter/section/subsection) with `type`, `num`, `heading` and a `parent` link; each article carries a `parent` link to its nearest enclosing division.

- **Hybrid Structure Tree**: New top-level `structure` key with the nested skeleton of the enacting terms (division nodes with article leaves, references only) alongside the flat `chapters`/`articles` lists.

- **Structured Preamble**: `preamble` is now a container object `{formula, citations, recitals_intro, recitals, final}` instead of a raw text dump that duplicated its parts.

- **Document Metadata Object**: New optional top-level `meta` object in the legalJSON schema (`celex`, `eli`, `cellar_uuid`, `date_document`, `in_force`, `amends`, `repeals`, `corrects`, `source`, `valid`) for enrichment from Cellar/ELI metadata records.

- **Corpus-Scale Quality Verification**: The Formex parser was verified against the complete corpus of in-force EU legislation in Formex 4 format (29,790 documents): alphanumeric text coverage between 0.97 and 1.03 of the source for every act (n=27,988) and every annex set (n=15,102), zero parse errors, and 100% of the generated legalJSON validating against the schema.

- **Enhanced Exception Hierarchy**: Added 8 new custom exception classes for granular error handling:
  - `NetworkError`: Network-related failures (replaces generic `RequestException`)
  - `AuthenticationError`: Authentication failures with APIs
  - `RateLimitError`: API rate limit exceedances
  - `SPARQLError`: SPARQL query execution failures
  - `SchemaValidationError`: XML schema validation failures with detailed error messages
  - `ContentTypeError`: Unexpected content type errors with content type information
  - `ElementNotFoundError`: Missing XML/HTML elements with element name and XPath
  - `ParserConfigurationError`: Parser misconfiguration errors

- **Comprehensive Exception Testing**: Added 14 new tests covering:
  - Exception hierarchy verification
  - Individual exception class functionality
  - Exception attribute validation
  - Exception chaining and propagation
  - Real-world usage in parsers and validators

### Changed

- **Improved Error Handling in Cellar Client**: 
  - `fetch_content()` now raises `NetworkError` instead of returning `None`
  - `send_sparql_query()` raises `SPARQLError` for query failures
  - Better error messages with context information

- **Enhanced XML Validation**: 
  - `XMLValidator.validate()` now raises `SchemaValidationError` for validation failures
  - `XMLValidator.load_schema()` raises `FileLoadError` for missing schemas
  - Proper exception chaining preserves original error context

- **Robust Parser Error Handling**:
  - `AkomaNtosoParser.get_articles()` raises `ParserConfigurationError` for missing body
  - `AKNArticleExtractor.extract_article_metadata()` raises `ElementNotFoundError` for missing elements
  - `Parser.to_dict()` raises `ParseError` for serialization failures

- **Improved Exception Propagation**:
  - Specific exceptions are re-raised instead of being wrapped
  - Better exception chaining with `from e` syntax
  - More informative error messages throughout the codebase

### Enhanced

- **Documentation Improvements**:
  - **Client Module**: Complete rewrite of `tulit/client/__init__.py` with:
    - Comprehensive module overview
    - Available clients organized by jurisdiction
    - Usage examples for key clients
    - Error handling and authentication notes
  - **HTML Parser**: Extensive documentation for `HTMLParser` class including:
    - Design patterns and key features
    - Abstract methods and implementation requirements
    - Usage examples with code snippets
    - Performance considerations and best practices

- **Error Messages with Context**:
  - XML extractors include element names and XPath in error messages
  - Parser methods include document and element IDs in error messages
  - Validation errors include line numbers and specific issues

### Fixed

- **XML Schema Validation Actually Runs**: `XMLParser.validate()` previously called the validator with a wrong signature and silently skipped validation; it now parses the tree, validates it and records errors. Bare schema filenames (e.g. `formex4.xsd`) resolve against the package's bundled `assets` directory.
- **Footnote Tail Text**: Removing `NOTE` elements no longer drops the remainder of the sentence following a footnote reference (fixed across article extraction, formula, titles and instruction text).
- **Nested-Element Double Extraction**: Nested `ALINEA`/`PARAG`/`CONSID`/`NP` structures are extracted exactly once (ownership checks and `not(ancestor::…)` filters), and content quoted inside `QUOT.S` is no longer mistaken for the document's own numbering or headings.
- **Table Cell Fidelity**: Table cells keep their separators and literal cell values such as `(043)` are no longer stripped by the point-number normalizer.
- **Cellar CELEX Suffixes**: Fixed double `{CELEX}` placeholder replacement in Cellar SPARQL queries that prevented parenthesis encoding, so suffixed CELEX numbers (e.g. `32012D0004(01)`) download correctly.
- **Empty Recitals**: Acts without whereas-clauses (e.g. old international agreements) emit an empty `recitals` list instead of `null`.
- **Conclusions Uniformity**: `to_dict()` normalises string conclusions from HTML parsers into the schema's object form (`{conclusion_text}`); Formex conclusions carry `signature` details including a `signatories` list for multi-signatory acts.
- **Exception Wrapping Issues**: Fixed cases where specific exceptions were being wrapped in generic `ParserConfigurationError`
- **Local Variable Scope**: Fixed `UnboundLocalError` in `XMLValidator.load_schema()` by moving imports to method level
- **Test Compatibility**: Updated existing tests to work with new exception-based error handling

## [0.4.6] - 2026-07-07
### Changed
- **Dependencies**: Bumped `lxml` from `^5.3.0` to `^6.1.0` (resolves to 6.1.1). All lxml usage relies on the stable `etree` API; the full test suite passes unchanged.

## [0.4.5] - 2026-06-03
### Fixed
- **Cellar SPARQL queries**: Removed `LIMIT` clause from all four production query files (`formex_query.rq`, `formex_eli_query.rq`, `html_query.rq`, `html_standard_query.rq`) so all results are returned instead of an arbitrary subset.

### Changed
- **CI**: Replaced committed coverage badge artifact with Codecov integration. No more bot commits on every push.

## [0.4.4] - 2026-01-07
### Fixed
- **AKN4EU Parser Article ID Extraction**: Fixed bug where `AKN4EUParser` was not correctly extracting `xml:id` attributes for articles. The `AKNArticleExtractor` now properly receives the `id_attr='{http://www.w3.org/XML/1998/namespace}id'` parameter for AKN4EU documents.

### Added
- **Chained Intro Extraction for AKN4EU**: New `extract_content_with_chained_intro` method in `AKNArticleExtractor` that properly combines list intro text (subparagraph) with all its points into a single paragraph entry, preserving the logical structure of legal provisions.

## [0.4.3] - 2026-01-05
### Fixed
- **Formex Article eID Parsing**: Fixed bug in `FormexArticleStrategy` where articles with IDs starting with `3` (e.g., Article 300, 333) were incorrectly parsed. The `lstrip('3')` method was stripping all leading `3` characters instead of just the legacy prefix. Now correctly handles both normal 3-digit article numbers (300, 333, etc.) and legacy 4-digit prefixed IDs (3001 -> 001).

## [0.4.2] - 2026-01-04
### Changed
- Released version 0.4.2 with bug fixes and improvements for cellar standard parsing and proposal parsing.

## [0.4.1] - 2024-12-22
### Added
- **End-to-End Test Suite**: Comprehensive E2E tests for all clients and parsers:
  - EU Cellar client tests with multiple formats and error handling
  - Member state client tests (Finland, France, Germany, Italy, Luxembourg, Portugal)
  - Parser E2E tests for Cellar HTML, Veneto, Legifrance JSON, AKN, Finlex XML, Formex, German legislation, Italy Normattiva, and Luxembourg
- **GitHub Actions CI/CD**: Automated testing workflow with coverage reporting:
  - Unit test execution with Poetry
  - Coverage badge generation and automatic updates
  - Codecov integration for detailed coverage reports
- **Client Module Enhancements**:
  - New regional client: `VenetoClient` for Italian regional legislation
  - Enhanced Germany client with comprehensive RIS integration
  - New Portugal ELI portal client
  - Unit tests for Legilux, Malta, Normattiva, and other state clients
- **Coverage Tracking**: Automated coverage badge generation from `coverage.xml`

### Changed
- **Package Restructuring**: Major reorganization for clarity and maintainability:
  - Renamed `tulit.parsers` → `tulit.parser` (singular for consistency)
  - Reorganized client modules by jurisdiction:
    - `tulit.client.eu/` for EU-level clients (Cellar)
    - `tulit.client.state/` for national clients (Finlex, Legifrance, etc.)
    - `tulit.client.regional/` for regional clients (Veneto)
  - Reorganized test structure:
    - `tests/unit/` for unit tests
    - `tests/e2e/` for end-to-end tests
    - Organized by module type (client, parser)
- **Test Organization**: Comprehensive test restructuring:
  - Split tests into unit and E2E categories
  - Organized client tests by jurisdiction (eu, state, regional)
  - Enhanced test fixtures with shared conftest configurations
  - Improved file path handling using `locate_data_dir` for portability

### Improved
- **Test Coverage**: Significantly expanded test suite:
  - Added unit tests for all major parser classes
  - Enhanced coverage for Akoma Ntoso parsers (AKN4EU, German LegalDocML, Luxembourg)
  - Comprehensive tests for HTML parsers (Cellar variants, Veneto)
  - Formex4Parser tests with additional assertions
  - XML parser helper tests
- **Code Quality**: Enhanced maintainability and structure:
  - Better separation of concerns in client modules
  - Improved error handling in parser implementations
  - Enhanced documentation and inline comments
  - Consistent import patterns across modules

### Fixed
- **Parser Implementations**:
  - Removed `base_dir` parameter from `xml.py` parser
  - Enhanced Akoma Ntoso parser for article and section validation
  - Improved Luxembourg AKN parser functionality
  - Fixed RelaxNG schema structure in XML validation tests

### Removed
- **Deprecated Scripts**: Cleaned up obsolete test and migration scripts:
  - Removed `scripts/run_all_clients.py` and `scripts/run_all_parsers.py`
  - Removed old migration and structure analysis reports
  - Removed obsolete HTML parsing scripts
  - Cleaned up deprecated test files for better codebase clarity

### Technical Details
- **CI/CD Pipeline**: Comprehensive GitHub Actions workflow for automated testing
- **Test Framework**: pytest-based test suite with enhanced fixtures
- **Coverage Reporting**: Integrated coverage tracking with badge generation
- **Module Structure**: Clear separation between unit and E2E tests
- **Backward Compatibility**: Import aliases maintained for smooth migration

### Migration Notes
- Update imports from `tulit.parsers` to `tulit.parser` (backward compatible)
- Client imports now organized by jurisdiction:
  - `from tulit.client.eu.cellar import CellarClient`
  - `from tulit.client.state.finlex import FinlexClient`
  - `from tulit.client.regional.veneto import VenetoClient`

## [0.4.0] - 2025-12-10

### Added
- **Parser Registry System**: New `ParserRegistry` class for dynamic parser selection and management
- **Domain Models**: Type-safe domain objects (`Article`, `Citation`, `Recital`, `Chapter`, `ArticleChild`) using dataclasses
- **Text Normalization Strategies**: Comprehensive normalization system with composable strategies:
  - `WhitespaceNormalizer` for whitespace handling
  - `UnicodeNormalizer` for character normalization
  - `PatternReplacementNormalizer` for custom replacements
  - `CompositeNormalizer` for combining strategies
- **Article Extraction Strategies**: Strategy pattern implementation for parser-specific article extraction
- **Custom Exception Hierarchy**: Granular error handling with `ParserError`, `ParseError`, `ValidationError`, `ExtractionError`, and `FileLoadError`
- **XML Utilities Package**: Centralized `XMLNodeExtractor` and `XMLValidator` classes
- **Akoma Ntoso Package**: Modular structure for Akoma Ntoso parsers:
  - `AkomaNtosoParser` base class
  - `AKN4EUParser` for EU documents
  - `GermanLegalDocMLParser` for German documents
  - `LuxembourgAKNParser` for Luxembourg documents
  - Factory functions for automatic format detection
- **Cellar HTML Parsers Package**: Organized EU Cellar parsers into dedicated package:
  - `CellarHTMLParser` for semantic XHTML
  - `CellarStandardHTMLParser` for simple HTML structure
  - `ProposalHTMLParser` for EU legislative proposals
- **Comprehensive Documentation**: New architecture guide and updated API documentation
- **Sphinx Documentation**: Integrated documentation build system

### Changed
- **Major Refactoring**: Reorganized codebase following SOLID principles and design patterns
- **Module Organization**: Split large monolithic files into focused modules:
  - `parser.py`: Reduced from 825 to 315 lines
  - `xml.py`: Reduced from 907 to 663 lines
  - `akomantoso.py`: Split into 7 focused modules
  - HTML parsers organized into `cellar/` package
- **Import Paths**: Updated structure with backward-compatible re-exports:
  - `tulit.parsers.html.html_parser` replaces `tulit.parsers.html.xhtml`
  - `tulit.parsers.html.cellar` package for Cellar parsers
  - `tulit.parsers.xml.akomantoso` package for Akoma Ntoso variants
- **HTMLParser Base Class**: Moved from `xhtml.py` to `html_parser.py` for clarity
- **Package Documentation**: Complete rewrite focusing on current architecture rather than migration

### Improved
- **Code Quality**: Better separation of concerns and single responsibility principle
- **Maintainability**: Smaller, more focused modules (average 200-300 lines)
- **Extensibility**: Easy to add new parsers through registry and strategy patterns
- **Type Safety**: Domain models provide IDE autocompletion and type checking
- **Error Handling**: Specific exception types for better debugging
- **Testing**: Maintained 100% test coverage (126 tests passing)

### Technical Details
- **Design Patterns**: Registry, Strategy, Factory, Template Method
- **Architecture**: Clean separation between parsing logic, data models, and utilities
- **Backward Compatibility**: All existing code works without changes through re-exports
- **Documentation**: Comprehensive architecture guide with examples

### Fixed
- Module import paths updated throughout test suite
- Consistent namespace handling in XML parsers
- Improved error messages in validation failures

### Deprecated
- `tulit.parsers.html.xhtml`: Use `tulit.parsers.html.html_parser` instead (backward compatible)

## [0.3.2] - Previous Release

### Previous Features
- Basic parser implementations for Formex, Akoma Ntoso, and HTML formats
- Client implementations for Cellar, Normattiva, and other legal databases
- Initial SPARQL query support
- Basic JSON export functionality

---

[0.4.0]: https://github.com/AlessioNar/tulit/compare/v0.3.2...v0.4.0
[0.3.2]: https://github.com/AlessioNar/tulit/releases/tag/v0.3.2
