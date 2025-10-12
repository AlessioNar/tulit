# `tulit`, The Universal Legal Informatics Toolkit

[![Publish Package to PyPI](https://github.com/AlessioNar/op_cellar/actions/workflows/publish.yml/badge.svg)](https://github.com/AlessioNar/op_cellar/actions/workflows/publish.yml)

## 1. Introduction

The `tulit` package provides utilities to work with legal data in a way that legal informatics practitioners can focus on adding value. 

## 2. Getting started

Full documentation is available at [https://tulit-docs.readthedocs.io/en/latest/index.html](https://tulit-docs.readthedocs.io/en/latest/index.html)

### 2.1 Installation

To install the `tulit` package, you can use the following command:

```bash
pip install tulit
```

or using poetry:

```bash
poetry add tulit
```

## 3. Database Structure

The `tulit` package uses a hierarchical database structure to organize legal documents from various sources.

### 3.1 Directory Organization

The database is located **outside the package** at `../database/` to keep production data separate from the codebase:

```
database/
├── sources/           # Raw downloaded documents
│   ├── eu/
│   │   └── eurlex/
│   │       ├── formex/              # FORMEX XML files from Cellar
│   │       ├── akn/                 # Akoma Ntoso XML files
│   │       ├── regulations/html/    # HTML regulations
│   │       └── commission_proposals/ # Commission proposals
│   ├── member_states/
│   │   ├── portugal/dre/            # Portuguese legal gazette
│   │   ├── italy/normattiva/        # Italian Normattiva
│   │   ├── luxembourg/legilux/      # Luxembourg Legilux
│   │   ├── france/legifrance/       # French Legifrance
│   │   ├── finland/finlex/          # Finnish Finlex
│   │   ├── malta/moj/               # Malta Ministry of Justice
│   │   ├── germany/gesetze/         # German legislation
│   │   └── spain/boe/               # Spanish Official Gazette
│   └── regional_authorities/
│       └── italy/veneto/            # Veneto regional laws
├── results/           # Parsed JSON documents
│   ├── eu/
│   │   ├── proposals/               # Parsed proposals
│   │   ├── formex/                  # Parsed FORMEX
│   │   ├── html/                    # Parsed regulations
│   │   └── akn/                     # Parsed AKN
│   ├── member_states/               # Parsed national docs
│   └── regional/                    # Parsed regional docs
└── logs/              # Download and processing logs
```

### 3.2 Hierarchical Principle

The structure follows a **jurisdictional hierarchy**:

1. **EU Level** (`eu/`): European Union institutions and bodies
2. **Member State Level** (`member_states/`): National governments
3. **Regional Level** (`regional_authorities/`): Sub-national authorities

### 3.3 Data Collection and Processing

#### Collecting Documents

Download legal documents from various sources:

```bash
python run_all_clients.py
```

This script:
- Creates the database directory structure automatically
- Downloads documents from EU and national legal information systems
- Saves raw documents to `database/sources/`
- Logs operations to `database/logs/`

#### Parsing Documents

Process downloaded documents into structured JSON:

```bash
python run_all_parsers.py
```

This script:
- Reads documents from `database/sources/`
- Parses using appropriate parsers (HTML, FORMEX, AKN)
- Saves structured JSON to `database/results/`
- Maintains the same hierarchical organization

### 3.4 Separation of Concerns

- **`sources/`**: Raw documents as downloaded (immutable, not committed to git)
- **`results/`**: Parsed/structured documents (reproducible, not committed to git)
- **`tests/data/`**: Sample fixtures for unit tests (committed to git)

This separation ensures:
- Data preservation
- Reproducibility
- Clear data lineage
- Version control hygiene (production data stays local)

## 4. Standards and Formats

### 4.1 Supported Standards

The `tulit` package is designed to work with existing standards and structured formats in the legal informatics domain. The following are some of the standards and formats that the package supports:

* [LegalDocML (Akoma Ntoso)](https://groups.oasis-open.org/communities/tc-community-home2?CommunityKey=3425f20f-b704-4076-9fab-018dc7d3efbe)
* [FORMEX](https://op.europa.eu/documents/3938058/5910419/formex_manual_on_screen_version.html)

### 4.2 Future Standards

Further standards and formats will be added in the future such as:

* [LegalHTML](https://art.uniroma2.it/legalhtml/)
* [NormeInRete](https://www.cambridge.org/core/journals/international-journal-of-legal-information/article/abs/norme-in-rete-project-standards-and-tools-for-italian-legislation/483BA5BF2EC4E9DD6636E761FE84AE15)

## 5. Acknowledgements

The `tulit` package has been inspired by a series of existing resources and builds upon some of their architectures and workflows. We would like to acknowledge their work and thank them for their contributions to the legal informatics community.

* The [eu_corpus_compiler](https://github.com/seljaseppala/eu_corpus_compiler) repository by Selja Seppala concerning the methods used to query the CELLAR SPARQL API and WEB APIs
* The [sortis](https://code.europa.eu/regulatory-reporting/sortis) project results from the European Commission
* The [EURLEX package](https://github.com/step21/eurlex) by step 21
* The [eurlex package](https://github.com/kevin91nl/eurlex/) by kevin91nl
* The [extraction_libraries](https://github.com/maastrichtlawtech/extraction_libraries) by the Maastricht Law and Tech Lab
* The [closer library](https://github.com/maastrichtlawtech/closer) by the Maastricht Law and Tech Lab

