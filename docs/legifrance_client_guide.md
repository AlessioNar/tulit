# Legifrance Client Guide

The Legifrance client provides access to the official French legal database through the PISTE API.

## Overview

The Legifrance API provides access to:
- **Codes** (Code Civil, Code du Travail, etc.)
- **Laws and Decrees** (LODA - Lois et Décrets)
- **Legislative Dossiers**
- **Official Journals** (JORF - Journal Officiel de la République Française)
- **Collective Agreements** (KALI - Conventions Collectives)
- **Case Law** (JURI - Jurisprudence)
- **Administrative Documents**
- **Parliamentary Debates**

## Authentication

The Legifrance API uses OAuth2 client credentials flow. You need:
1. A `client_id`
2. A `client_secret`

These can be obtained by registering for API access at [piste.gouv.fr](https://piste.gouv.fr).

### Setting up credentials

You can provide credentials in two ways:

1. **Environment variables** (recommended):
```powershell
$env:LEGIFRANCE_CLIENT_ID = "your_client_id"
$env:LEGIFRANCE_CLIENT_SECRET = "your_client_secret"
```

2. **Command-line arguments**:
```powershell
python -m tulit.client.legifrance --client_id your_client_id --client_secret your_client_secret ...
```

## API Controllers

The client implements the following API controllers:

### 1. Consult Controller
Retrieve specific documents by identifier.

#### Available Methods:
- `consult_code()` - Get code content (e.g., Code Civil)
- `consult_law_decree()` - Get law/decree content (LODA)
- `consult_article()` - Get article content
- `consult_article_by_eli_or_alias()` - Get article by ELI
- `consult_dossier_legislatif()` - Get legislative dossier
- `consult_jorf()` - Get JORF text
- `consult_jorf_container()` - Get JORF table of contents
- `consult_table_matieres()` - Get table of contents for LODA/CODE
- `consult_kali_text()` - Get collective agreement
- `consult_juri()` - Get case law
- `consult_circulaire()` - Get circular
- `consult_debat()` - Get parliamentary debate

### 2. List Controller
List documents with pagination.

#### Available Methods:
- `list_codes()` - List all codes
- `list_loda()` - List laws and decrees
- `list_dossiers_legislatifs()` - List legislative dossiers
- `list_conventions()` - List collective agreements
- `list_bocc()` - List bulletins of collective agreements
- `list_debats_parlementaires()` - List parliamentary debates

### 3. Search Controller
Search across indexed documents.

#### Available Methods:
- `search()` - Generic search with filters

### 4. Suggest Controller
Autocomplete suggestions.

#### Available Methods:
- `suggest()` - Get suggestions for a query

## Usage Examples

### Example 1: Download Code Civil
```powershell
python -m tulit.client.legifrance `
  --client_id YOUR_CLIENT_ID `
  --client_secret YOUR_CLIENT_SECRET `
  --action download_code `
  --text_id LEGITEXT000006070721 `
  --dir ./data/france/legifrance `
  --logdir ./logs
```

### Example 2: Download Code Civil at a specific date
```powershell
python -m tulit.client.legifrance `
  --client_id YOUR_CLIENT_ID `
  --client_secret YOUR_CLIENT_SECRET `
  --action download_code `
  --text_id LEGITEXT000006070721 `
  --date 2020-01-01 `
  --dir ./data/france/legifrance `
  --logdir ./logs
```

### Example 3: Search for documents
```powershell
python -m tulit.client.legifrance `
  --client_id YOUR_CLIENT_ID `
  --client_secret YOUR_CLIENT_SECRET `
  --action search `
  --query "droit du travail" `
  --page_number 1 `
  --page_size 10 `
  --dir ./data/france/legifrance `
  --logdir ./logs
```

### Example 4: List codes with pagination
```powershell
python -m tulit.client.legifrance `
  --client_id YOUR_CLIENT_ID `
  --client_secret YOUR_CLIENT_SECRET `
  --action list_codes `
  --page_number 1 `
  --page_size 10 `
  --dir ./data/france/legifrance `
  --logdir ./logs
```

### Example 5: Download a legislative dossier
```powershell
python -m tulit.client.legifrance `
  --client_id YOUR_CLIENT_ID `
  --client_secret YOUR_CLIENT_SECRET `
  --action download_dossier `
  --text_id JORFTEXT000012345678 `
  --dir ./data/france/legifrance `
  --logdir ./logs
```

### Example 6: Get suggestions
```powershell
python -m tulit.client.legifrance `
  --client_id YOUR_CLIENT_ID `
  --client_secret YOUR_CLIENT_SECRET `
  --action suggest `
  --query "code civ" `
  --dir ./data/france/legifrance `
  --logdir ./logs
```

## Common Text Identifiers

### Popular Codes:
- **Code Civil**: `LEGITEXT000006070721`
- **Code du Travail**: `LEGITEXT000006072050`
- **Code Pénal**: `LEGITEXT000006070719`
- **Code de Commerce**: `LEGITEXT000005634379`
- **Code de Procédure Civile**: `LEGITEXT000006070716`
- **Code de la Santé Publique**: `LEGITEXT000006072665`

## Actions Available

| Action | Description | Required Args |
|--------|-------------|---------------|
| `download_code` | Download a code and save to file | `--text_id` |
| `download_dossier` | Download a legislative dossier | `--text_id` |
| `consult_code` | View code content (stdout) | `--text_id` |
| `consult_article` | View article content | `--article_id` |
| `consult_dossier` | View dossier content | `--text_id` |
| `list_codes` | List codes with pagination | - |
| `list_loda` | List laws/decrees with pagination | - |
| `list_dossiers` | List legislative dossiers | - |
| `search` | Search documents | `--query` |
| `suggest` | Get autocomplete suggestions | `--query` |

## Optional Parameters

- `--date` - Date for versioned content (format: `YYYY-MM-DD`)
- `--page_number` - Page number for list operations (default: 1)
- `--page_size` - Items per page for list operations (default: 10)
- `--dir` - Download directory (default: `./data/france/legifrance`)
- `--logdir` - Log directory (default: `./logs`)

## Python API Usage

You can also use the client programmatically in your Python code:

```python
from tulit.client.legifrance import LegifranceClient

# Initialize client
client = LegifranceClient(
    client_id="your_client_id",
    client_secret="your_client_secret",
    download_dir="./data/france/legifrance",
    log_dir="./logs"
)

# Download Code Civil
filepath = client.download_code("LEGITEXT000006070721")
print(f"Downloaded to: {filepath}")

# Search for documents
results = client.search("droit du travail", page_number=1, page_size=10)
print(results)

# List codes
codes = client.list_codes(page_number=1, page_size=100)
print(codes)

# Get specific article
article = client.consult_article("LEGIARTI000006419283")
print(article)
```

## Output Format

All results are saved as JSON files with UTF-8 encoding and proper indentation for readability.

Example output structure:
```
./data/france/legifrance/
├── code_LEGITEXT000006070721_current.json
├── dossier_JORFTEXT000012345678.json
└── ...
```

## Error Handling

The client includes comprehensive error handling and logging:
- OAuth token failures are logged and re-raised
- HTTP errors include endpoint information
- Content-type mismatches are logged as warnings
- All operations are logged to `./logs/client.log`

## API Rate Limits

Be aware of API rate limits when making multiple requests. The sandbox API may have different limits than the production API.

## Troubleshooting

### "Failed to obtain OAuth token"
- Check your `client_id` and `client_secret`
- Verify your API access is active
- Check network connectivity

### "Expected JSON response but got: text/html"
- The endpoint may not exist or may have changed
- Check the Legifrance API documentation for updates
- Verify the text_id or other identifiers are correct

### "HTTP error on /consult/..."
- Check that the text_id or other identifier exists
- Verify the date format (YYYY-MM-DD)
- Some documents may not be available for all dates

## Additional Resources

- [Legifrance Official Site](https://www.legifrance.gouv.fr/)
- [PISTE API Portal](https://piste.gouv.fr/)
- [API Documentation](https://api.piste.gouv.fr/dila/legifrance-beta/latest/guide.html)

## Notes

- The client uses the **sandbox** API by default. For production, update `base_url` and `oauth_url` in the client.
- All dates use the format `YYYY-MM-DD`
- Text identifiers typically start with `LEGITEXT` (codes/laws) or `JORFTEXT` (official journal)
- Article identifiers typically start with `LEGIARTI`
