# Legifrance Client - Quick Reference Card

## 🚀 Quick Start

```python
from tulit.client.legifrance import LegifranceClient

client = LegifranceClient(
    client_id="your_id",
    client_secret="your_secret"
)
```

---

## 📚 Most Common Operations

### Get Documents

```python
# Code Civil
code = client.consult_code("LEGITEXT000006070721")

# Law or Decree
law = client.consult_law_decree("LEGITEXT123456")

# Article
article = client.consult_article("LEGIARTI123456")

# Legislative Dossier
dossier = client.consult_dossier_legislatif("JORFTEXT123456")

# Official Journal
jo = client.consult_jorf("JORFTEXT123456")
```

### Search & List

```python
# Search
results = client.search("droit du travail", page_size=10)

# List codes
codes = client.list_codes(page_number=1, page_size=100)

# List laws
laws = client.list_loda(page_number=1, page_size=50)

# Suggestions
suggestions = client.suggest("code civil")
```

### Download to File

```python
# Download and save
filepath = client.download_code("LEGITEXT000006070721")
# Saves to: ./data/france/legifrance/code_LEGITEXT000006070721_current.json
```

---

## 🎯 Common Text Identifiers

| Document | ID |
|----------|-----|
| Code Civil | `LEGITEXT000006070721` |
| Code du Travail | `LEGITEXT000006072050` |
| Code Pénal | `LEGITEXT000006070719` |
| Code de Commerce | `LEGITEXT000005634379` |

---

## 🔧 All Available Methods (67 total)

### CONSULT (38 methods)

**Core Documents**
- `consult_code(text_id, date?)`
- `consult_law_decree(text_id, date?)`
- `consult_dossier_legislatif(text_id)`
- `consult_jorf(text_id)`
- `consult_jorf_cont(num, date)`
- `consult_jorf_part(text_id)`
- `consult_debat(text_id)`
- `consult_circulaire(text_id)`
- `consult_acco(text_id)`

**Articles**
- `consult_article(article_id, date?)`
- `consult_article_by_eli_or_alias(eli)`
- `consult_article_by_cid(cid)`
- `consult_article_with_id_and_num(id, num, date?)`

**Article Links**
- `consult_same_num_article(article_id)`
- `consult_concordance_links_article(article_id)`
- `consult_related_links_article(article_id)`
- `consult_service_public_links_article(article_id)`
- `consult_has_service_public_links_article(text_id)`

**Collective Agreements (KALI)**
- `consult_kali_text(cid)`
- `consult_kali_article(cid, article_num)`
- `consult_kali_section(cid, section_id)`
- `consult_kali_cont(idcc)`
- `consult_kali_cont_idcc(idcc)`

**Case Law (JURI)**
- `consult_juri(text_id)`
- `consult_juri_with_ancien_id(ancien_id)`
- `consult_juri_plan_classement(text_id)`

**CNIL**
- `consult_cnil(text_id)`
- `consult_cnil_with_ancien_id(ancien_id)`

**Sections & Parts**
- `consult_section_by_cid(cid, date?)`
- `consult_legi_part(text_id, searched_string?, date?)`
- `consult_table_matieres(text_id, date?)`
- `consult_tables(start_year, end_year)`

**By Legacy ID**
- `consult_code_with_ancien_id(ancien_id)`
- `consult_jo_with_nor(nor)`
- `consult_last_n_jo(n=10)`
- `consult_eli_alias_redirection(eli)`

**Metadata**
- `consult_bocc_text_pdf_metadata(text_id)`
- `consult_ping()`

---

### LIST (13 methods)

- `list_codes(page_number=1, page_size=100, date?)`
- `list_loda(page_number=1, page_size=100, date?)`
- `list_dossiers_legislatifs(page_number=1, page_size=100)`
- `list_conventions(page_number=1, page_size=100)`
- `list_bocc(page_number=1, page_size=100)`
- `list_bocc_texts(page_number=1, page_size=100, filters?)`
- `list_boccs_and_texts(page_number=1, page_size=100, filters?)`
- `list_bodmr(start_year, end_year, page_number=1, page_size=100)`
- `list_docs_admins(start_year, end_year, page_number=1, page_size=100)`
- `list_questions_ecrites_parlementaires(page_number=1, page_size=100, filters?)`
- `list_debats_parlementaires(legislature?, page_number=1, page_size=100)`
- `list_legislatures()`
- `list_ping()`

---

### SEARCH (5 methods)

- `search(query, page_number=1, page_size=10, filters?)`
- `search_canonical_version(text_id, date?)`
- `search_canonical_article_version(article_id, date?)`
- `search_nearest_version(text_id, date)`
- `search_ping()`

---

### SUGGEST (4 methods)

- `suggest(query, type?)`
- `suggest_acco(query)`
- `suggest_pdc(query)`
- `suggest_ping()`

---

### CHRONO (4 methods)

- `chrono_text_version(text_cid, date?)`
- `chrono_text_has_versions(text_cid)`
- `chrono_text_and_element(text_cid, element_cid, date?)`
- `chrono_ping()`

---

### MISC (3 methods)

- `misc_commit_id()`
- `misc_dates_without_jo()`
- `misc_years_without_table()`

---

### DOWNLOAD (3 helpers)

- `download(endpoint, payload, filename)`
- `download_code(text_id, date?)`
- `download_dossier_legislatif(text_id)`

---

## 💡 Pro Tips

### Environment Variables

```powershell
$env:LEGIFRANCE_CLIENT_ID = "your_client_id"
$env:LEGIFRANCE_CLIENT_SECRET = "your_client_secret"
```

```python
import os
client = LegifranceClient(
    client_id=os.environ['LEGIFRANCE_CLIENT_ID'],
    client_secret=os.environ['LEGIFRANCE_CLIENT_SECRET']
)
```

### Error Handling

```python
try:
    code = client.consult_code("INVALID_ID")
except requests.exceptions.HTTPError as e:
    print(f"HTTP Error: {e}")
except Exception as e:
    print(f"Error: {e}")
```

### Pagination Loop

```python
page = 1
all_codes = []

while True:
    result = client.list_codes(page_number=page, page_size=100)
    all_codes.extend(result['results'])
    
    if page * 100 >= result['totalResults']:
        break
    page += 1
```

### Version History

```python
# Get current version
current = client.consult_code("LEGITEXT000006070721")

# Get historical version
historical = client.consult_code("LEGITEXT000006070721", date="2010-01-01")

# Get nearest version to date
nearest = client.search_nearest_version("LEGITEXT000006070721", "2010-06-15")
```

---

## 📞 Support

- **Documentation**: `docs/legifrance_client_guide.md`
- **Examples**: `examples/legifrance_example.py`
- **API Spec**: `docs/legifrance_openapi.json`
- **Tests**: `tests/client/test_legifrance.py`

---

## ⚡ Command Line Interface

```powershell
# Download document
python -m tulit.client.legifrance `
  --client_id $CLIENT_ID `
  --client_secret $CLIENT_SECRET `
  --action download_code `
  --text_id LEGITEXT000006070721

# Search
python -m tulit.client.legifrance `
  --client_id $CLIENT_ID `
  --client_secret $CLIENT_SECRET `
  --action search `
  --query "droit du travail" `
  --page_size 10

# List with pagination
python -m tulit.client.legifrance `
  --client_id $CLIENT_ID `
  --client_secret $CLIENT_SECRET `
  --action list_codes `
  --page_number 1 `
  --page_size 100
```

---

**Coverage**: 98.5% (67/68 endpoints) | **Tests**: 35 passing ✓ | **Status**: Production Ready ✅
