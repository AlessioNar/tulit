# Germany RIS Client Guide

## Overview

The Germany client provides access to the German Rechtsinformationssystem (RIS) API, which offers comprehensive access to German legal documents including:

- **Legislation** (Normen) - Laws, decrees, and regulations
- **Case Law** (Rechtsprechung) - Court decisions and judgments
- **Literature** (Literatur) - Legal literature and commentary

**API Base URL**: https://testphase.rechtsinformationen.bund.de  
**API Documentation**: https://testphase.rechtsinformationen.bund.de/swagger-ui/index.html

## Features

### Document Types

1. **Legislation**
   - Search by ELI (European Legislation Identifier)
   - Filter by temporal coverage (when laws were in force)
   - Download in HTML, XML (LegalDocML), or ZIP format
   - Access to all versions and manifestations

2. **Case Law**
   - Search by court, file number, ECLI, or full-text
   - Filter by decision type, date, and legal effect
   - Download in HTML, XML, or ZIP format
   - Includes court decisions from federal and supreme courts

3. **Literature**
   - Search legal literature and commentary
   - Filter by author, publication year, document type
   - Download in HTML or XML format

### Supported Formats

- **HTML**: Rendered, human-readable format
- **XML**: LegalDocML format for machine processing
- **ZIP**: Complete package with XML and all attachments

## Installation

The client is part of the `tulit` package:

```bash
pip install tulit
```

Or install from source:

```bash
cd tulit
pip install -e .
```

## Usage

### Command Line Interface

#### Download Legislation

```bash
# Download legislation by ELI URL (HTML)
python -m tulit.client.germany \
  --type legislation \
  --eli-url "https://testphase.rechtsinformationen.bund.de/v1/legislation/eli/bund/bgbl-1/1979/s1325/2020-06-19/2/deu/2020-06-19/regelungstext-1.html" \
  --format html \
  --dir ./downloads/germany

# Download legislation as ZIP with XML and attachments
python -m tulit.client.germany \
  --type legislation \
  --eli-url "https://testphase.rechtsinformationen.bund.de/v1/legislation/eli/bund/bgbl-1/1979/s1325/2020-06-19/2/deu/2020-06-19" \
  --format zip \
  --dir ./downloads/germany

# Search and download legislation
python -m tulit.client.germany \
  --type legislation \
  --search "Kakaoverordnung" \
  --format xml \
  --dir ./downloads/germany
```

#### Download Case Law

```bash
# Download case law by document number (HTML)
python -m tulit.client.germany \
  --type case-law \
  --document-number STRE201770751 \
  --format html \
  --dir ./downloads/germany

# Download case law as XML
python -m tulit.client.germany \
  --type case-law \
  --document-number STRE201770751 \
  --format xml \
  --dir ./downloads/germany

# Download case law as ZIP (with attachments)
python -m tulit.client.germany \
  --type case-law \
  --document-number STRE201770751 \
  --format zip \
  --dir ./downloads/germany
```

#### Download Literature

```bash
# Download literature (HTML)
python -m tulit.client.germany \
  --type literature \
  --document-number BJLU075748788 \
  --format html \
  --dir ./downloads/germany

# Download literature (XML)
python -m tulit.client.germany \
  --type literature \
  --document-number BJLU075748788 \
  --format xml \
  --dir ./downloads/germany
```

#### Global Search

```bash
# Search across all document types
python -m tulit.client.germany \
  --type search \
  --search "Grundgesetz" \
  --dir ./downloads/germany
```

### Python API

#### Initialize Client

```python
from tulit.client.germany import GermanyClient

client = GermanyClient(
    download_dir="./downloads/germany",
    log_dir="./logs"
)
```

#### Search and Download Legislation

```python
# Search for legislation
results = client.search_legislation(
    search_term="Kakaoverordnung",
    temporal_coverage_from="2020-01-01",
    size=10
)

print(f"Found {results['totalItems']} items")
for member in results['member']:
    item = member['item']
    print(f"- {item['name']} (ELI: {item['legislationIdentifier']})")

# Download specific legislation (HTML)
file_path = client.download_legislation_html(
    jurisdiction='bund',
    agent='bgbl-1',
    year='1979',
    natural_identifier='s1325',
    point_in_time='2020-06-19',
    version=2,
    language='deu',
    point_in_time_manifestation='2020-06-19',
    subtype='regelungstext-1'
)
print(f"Downloaded to: {file_path}")

# Download from ELI URL
file_path = client.download_from_eli(
    eli_url="https://testphase.rechtsinformationen.bund.de/v1/legislation/eli/bund/bgbl-1/1979/s1325/2020-06-19/2/deu/2020-06-19/regelungstext-1.html",
    fmt='html'
)
```

#### Search and Download Case Law

```python
# Search for case law
results = client.search_case_law(
    search_term="Arbeitsrecht",
    court="Bundesarbeitsgericht",
    date_from="2020-01-01",
    size=10
)

print(f"Found {results['totalItems']} decisions")
for member in results['member']:
    item = member['item']
    print(f"- {item.get('headline', 'N/A')} ({item['documentNumber']})")

# Download specific case law
file_path = client.download_case_law_html('STRE201770751')
print(f"Downloaded to: {file_path}")

# Download as ZIP with attachments
file_path = client.download_case_law_zip('STRE201770751')
print(f"Downloaded ZIP to: {file_path}")

# Get metadata
metadata = client.get_case_law_metadata('STRE201770751')
print(f"ECLI: {metadata.get('ecli', 'N/A')}")
print(f"Court: {metadata.get('courtName', 'N/A')}")
print(f"Decision Date: {metadata.get('decisionDate', 'N/A')}")
```

#### Search and Download Literature

```python
# Search for literature
results = client.search_literature(
    search_term="Verwaltungsrecht",
    author="Schmidt",
    year_of_publication="2020",
    size=10
)

print(f"Found {results['totalItems']} literature items")
for member in results['member']:
    item = member['item']
    print(f"- {item.get('headline', 'N/A')} ({item['documentNumber']})")

# Download literature
file_path = client.download_literature_html('BJLU075748788')
print(f"Downloaded to: {file_path}")
```

#### Global Search

```python
# Search across all document types
results = client.search_all_documents(
    search_term="Datenschutz",
    date_from="2020-01-01",
    size=20
)

print(f"Found {results['totalItems']} documents")
for member in results['member']:
    item = member['item']
    doc_type = item.get('@type', 'Unknown')
    name = item.get('name', item.get('headline', 'N/A'))
    print(f"- [{doc_type}] {name}")

# Search only legislation
results = client.search_all_documents(
    search_term="Verordnung",
    document_kind='N',  # N for Normen (legislation)
    size=10
)

# Search only case law
results = client.search_all_documents(
    search_term="Urteil",
    document_kind='R',  # R for Rechtsprechung (case law)
    size=10
)
```

## ELI Structure

European Legislation Identifiers (ELIs) follow this structure:

```
/v1/legislation/eli/{jurisdiction}/{agent}/{year}/{naturalIdentifier}/{pointInTime}/{version}/{language}/{pointInTimeManifestation}/{subtype}
```

### Parameters

- **jurisdiction**: `bund` (federal level)
- **agent**: Issuing authority (e.g., `bgbl-1` for Bundesgesetzblatt Teil I)
- **year**: Year of enactment (e.g., `1979`)
- **naturalIdentifier**: Natural identifier (e.g., `s1325`)
- **pointInTime**: Point in time date in YYYY-MM-DD format
- **version**: Version number (integer)
- **language**: Language code (e.g., `deu` for German)
- **pointInTimeManifestation**: Manifestation date in YYYY-MM-DD format
- **subtype**: Document subtype (e.g., `regelungstext-1`)

### Example

```
/v1/legislation/eli/bund/bgbl-1/1979/s1325/2020-06-19/2/deu/2020-06-19/regelungstext-1.html
```

This refers to:
- Federal law (`bund`)
- Published in Federal Law Gazette Part I (`bgbl-1`)
- From 1979 (`1979`)
- With identifier s1325 (`s1325`)
- As it stood on 2020-06-19
- Version 2
- In German
- Manifestation from 2020-06-19
- Regulation text subtype
- In HTML format

## Advanced Usage

### Temporal Coverage Filtering

Find all versions of laws that were in force during a specific period:

```python
# Get all laws in force on a specific date
results = client.search_legislation(
    temporal_coverage_from="2020-01-01",
    temporal_coverage_to="2020-01-01"
)

# Get all laws in force during a date range
results = client.search_legislation(
    temporal_coverage_from="2020-01-01",
    temporal_coverage_to="2020-12-31"
)
```

### Pagination

```python
# Get first 100 results
results = client.search_legislation(
    search_term="Gesetz",
    size=100,
    page_index=0
)

# Get next 100 results
results = client.search_legislation(
    search_term="Gesetz",
    size=100,
    page_index=1
)
```

### Sorting

```python
# Sort by date (descending)
results = client.search_legislation(
    search_term="Verordnung",
    sort="-date"
)

# Sort by legislation identifier (ascending)
results = client.search_case_law(
    search_term="Urteil",
    sort="documentNumber"
)
```

### Error Handling

```python
try:
    file_path = client.download_case_law_html('INVALID_NUMBER')
except requests.HTTPError as e:
    if e.response.status_code == 404:
        print("Document not found")
    else:
        print(f"HTTP error: {e}")
except Exception as e:
    print(f"Error: {e}")
```

## API Limits

- Maximum page size: 100 items
- Maximum total results: 10,000 items
- Rate limiting may apply (not documented in API spec)

## Data Formats

### HTML
- Rendered, human-readable format
- Suitable for display and reading
- May include CSS styling

### XML (LegalDocML)
- Structured, machine-readable format
- Follows LegalDocML/Akoma Ntoso standards with German-specific extensions
- Uses namespace: `http://Inhaltsdaten.LegalDocML.de/1.8.2/`
- Suitable for parsing and analysis
- **Note**: The German LegalDocML format uses a German-specific namespace and schema extensions. While based on Akoma Ntoso, it may require a specialized parser or namespace handling to parse correctly with standard Akoma Ntoso parsers.

### ZIP
- Contains XML plus all attachments (images, PDFs, etc.)
- Most complete representation of the document
- Automatically extracted by the client

## Examples

See `tests/test_germany_client.py` for comprehensive examples of all client features.

## Support

For issues or questions:
- GitHub: https://github.com/AlessioNar/tulit
- API Documentation: https://testphase.rechtsinformationen.bund.de/swagger-ui/index.html

## License

See LICENSE file in the repository root.
