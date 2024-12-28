# `tulit`, The Universal Legal Informatics Toolkit

[![Publish Package to PyPI](https://github.com/AlessioNar/op_cellar/actions/workflows/publish.yml/badge.svg)](https://github.com/AlessioNar/op_cellar/actions/workflows/publish.yml)

## 1. Introduction

The `tulit` package provides utilities to work with legal data in a way that legal informatics practitioners can focus on adding value. 

## 2. Getting started

Documentation is available at [https://tulit-docs.readthedocs.io/en/latest/index.html](https://tulit-docs.readthedocs.io/en/latest/index.html)

### 2.1 Installation

To install the `tulit` package, you can use the following command:

```bash
pip install tulit
```

or using poetry:

```bash
poetry add tulit
```

### 2.2 Basic usage

The `tulit` package main components are:
* a client to query and retrieve data from a variety of legal data sources. Currently the package supports the Cellar, LegiLux and Normattiva.
* a parser to convert legal documents from a variety of formats to a json representation.

#### Retrieving legal documents

The `tulit` package provides a client to query and retrieve data from a variety of legal data sources. The following code snippet shows how to use the `tulit` package to retrieve a legal document from Cellar, given its CELEX number:

```python

from tulit.download.cellar import CellarDownloader

client = CellarDownloader()
downloader = CellarDownloader(download_dir='./tests/data/formex', log_dir='./tests/logs')
with open('./tests/metadata/query_results/query_results.json', 'r') as f:
    results = json.loads(f.read())
documents = downloader.download(results, format='fmx4')

print(documents)
```

#### Parsing legal documents

The `tulit` parsers support exclusively legislative documents which were adopted in the following formats:
* Akoma Ntoso 3.0
* FORMEX 4
* XHTML originated from Cellar

The following code snippet shows how to use the `tulit` package to parse a legal document in Akoma Ntoso format:

```python
from tulit.parsers.xml.akomantoso import AkomaNtosoParser

parser = AkomaNtosoParser()
    
file_to_parse = 'tests/data/akn/eu/32014L0092.akn'
parser.parse(file_to_parse)

# The various attributes of the parser can be accessed as follows
print(parser.preface)
print(parser.citations)
print(parser.recitals)
print(parser.chapters)
print(parser.articles

```

A similar approach can be used to parse a legal document in FORMEX and XHTML format:

```python

from tulit.parsers.xml.formex import FormexParser

formex_file = 'tests/data/formex/c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.02/DOC_1/L_202400903EN.000101.fmx.xml'
parser = FormexParser()

parser.parse(formex_file)

from tulit.parsers.html.xhtml import HTMLParser

html_file = 'tests/data/html/c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.03/DOC_1.html'

parser = HTMLParser()
parser.parse(html_file)

```


### Use of existing standards and structured formats

The `tulit` package is designed to work with existing standards and structured formats in the legal informatics domain. The following are some of the standards and formats that the package is designed to work with:

* [LegalDocML (Akoma Ntoso)](https://groups.oasis-open.org/communities/tc-community-home2?CommunityKey=3425f20f-b704-4076-9fab-018dc7d3efbe)
* [FORMEX](https://op.europa.eu/documents/3938058/5910419/formex_manual_on_screen_version.html)

Further standards and formats will be added in the future such as:

* [LegalHTML](https://art.uniroma2.it/legalhtml/)
* [NormeInRete](https://www.cambridge.org/core/journals/international-journal-of-legal-information/article/abs/norme-in-rete-project-standards-and-tools-for-italian-legislation/483BA5BF2EC4E9DD6636E761FE84AE15)

## Acknowledgements

The `tulit` package has been inspired by a series of existing resources and builds upon some of their architectures and workflows. We would like to acknowledge their work and thank them for their contributions to the legal informatics community.

* The [eu_corpus_compiler](https://github.com/seljaseppala/eu_corpus_compiler) repository by Selja Seppala concerning the methods used to query the CELLAR SPARQL API and WEB APIs
* The [sortis](https://code.europa.eu/regulatory-reporting/sortis) project results from the European Commission
* The [EURLEX package](https://github.com/step21/eurlex) by step 21
* The [eurlex package](https://github.com/kevin91nl/eurlex/) by kevin91nl
* The [extraction_libraries](https://github.com/maastrichtlawtech/extraction_libraries) by the Maastricht Law and Tech Lab
* The [closer library](https://github.com/maastrichtlawtech/closer) by the Maastricht Law and Tech Lab

