# Legifrance API Complete Endpoint Map

**API Version:** 2.4.2  
**Base URL:** `https://sandbox-api.piste.gouv.fr/dila/legifrance/lf-engine-app`  
**Total Endpoints:** 68

## Implementation Status

Legend:
- ✅ Implemented
- ⚠️ Partially implemented (basic version exists)
- ❌ Not yet implemented

---

## CHRONO Controller (4 endpoints)

Version management for texts.

| Status | Method | Endpoint | Description |
|--------|--------|----------|-------------|
| ✅ | GET | `/chrono/ping` | Test controller |
| ❌ | POST | `/chrono/textCid` | Get text version |
| ❌ | GET | `/chrono/textCid/{textCid}` | Check if text has versions |
| ❌ | POST | `/chrono/textCidAndElementCid` | Extract from text version |

---

## CONSULT Controller (39 endpoints)

Retrieve specific legal documents.

| Status | Method | Endpoint | Description |
|--------|--------|----------|-------------|
| ❌ | POST | `/consult/acco` | Company agreement content |
| ✅ | POST | `/consult/circulaire` | Circular content |
| ❌ | POST | `/consult/cnil` | CNIL text content |
| ✅ | POST | `/consult/code` | Code content (e.g., Code Civil) |
| ❌ | POST | `/consult/code/tableMatieres` | Code table of contents (deprecated) |
| ❌ | POST | `/consult/concordanceLinksArticle` | Article concordance links |
| ✅ | POST | `/consult/debat` | Parliamentary debate content |
| ✅ | POST | `/consult/dossierLegislatif` | Legislative dossier content |
| ❌ | POST | `/consult/eliAndAliasRedirectionTexte` | Official Journal texts by ELI |
| ✅ | POST | `/consult/getArticle` | Article content |
| ❌ | POST | `/consult/getArticleByCid` | Article versions by CID |
| ❌ | POST | `/consult/getArticleWithIdAndNum` | Article by ID and number |
| ✅ | POST | `/consult/getArticleWithIdEliOrAlias` | Article by ELI or alias |
| ❌ | POST | `/consult/getBoccTextPdfMetadata` | BOCC PDF metadata |
| ❌ | POST | `/consult/getCnilWithAncienId` | CNIL text by ancien ID |
| ❌ | POST | `/consult/getCodeWithAncienId` | Code by ancien ID |
| ❌ | POST | `/consult/getJoWithNor` | Official Journal by NOR |
| ❌ | POST | `/consult/getJuriPlanClassement` | Case law classification plan |
| ❌ | POST | `/consult/getJuriWithAncienId` | Case law by ancien ID |
| ❌ | POST | `/consult/getSectionByCid` | Section by CID |
| ❌ | POST | `/consult/getTables` | Annual tables list |
| ❌ | POST | `/consult/hasServicePublicLinksArticle` | Articles with public service links |
| ✅ | POST | `/consult/jorf` | JORF text content |
| ✅ | POST | `/consult/jorfCont` | JORF table of contents |
| ❌ | POST | `/consult/jorfPart` | JORF partial content |
| ✅ | POST | `/consult/juri` | Case law content |
| ❌ | POST | `/consult/kaliArticle` | Collective agreement from article |
| ❌ | POST | `/consult/kaliCont` | Collective agreement containers |
| ❌ | POST | `/consult/kaliContIdcc` | Collective agreement containers by IDCC |
| ❌ | POST | `/consult/kaliSection` | Collective agreement from section |
| ✅ | POST | `/consult/kaliText` | Collective agreement content |
| ❌ | POST | `/consult/lastNJo` | Last N Official Journals |
| ✅ | POST | `/consult/lawDecree` | Law/decree content (LODA) |
| ✅ | POST | `/consult/legi/tableMatieres` | LODA/CODE table of contents |
| ❌ | POST | `/consult/legiPart` | LEGI partial content |
| ✅ | GET | `/consult/ping` | Test controller |
| ❌ | POST | `/consult/relatedLinksArticle` | Article related links |
| ❌ | POST | `/consult/sameNumArticle` | Articles with same number |
| ❌ | POST | `/consult/servicePublicLinksArticle` | Article public service links |

**Implemented:** 12/39 (31%)

---

## LIST Controller (13 endpoints)

List documents with pagination.

| Status | Method | Endpoint | Description |
|--------|--------|----------|-------------|
| ✅ | POST | `/list/bocc` | Collective agreement bulletins (paginated) |
| ❌ | POST | `/list/boccTexts` | BOCC unit texts (paginated) |
| ❌ | POST | `/list/boccsAndTexts` | BOCC and texts (paginated) |
| ❌ | POST | `/list/bodmr` | Decorations/medals bulletins |
| ✅ | POST | `/list/code` | Codes (paginated) |
| ✅ | POST | `/list/conventions` | Conventions (paginated) |
| ✅ | POST | `/list/debatsParlementaires` | Parliamentary debates |
| ❌ | POST | `/list/docsAdmins` | Administrative documents |
| ✅ | POST | `/list/dossiersLegislatifs` | Legislative dossiers (paginated) |
| ❌ | POST | `/list/legislatures` | Legislatures |
| ✅ | POST | `/list/loda` | LODA texts (paginated) |
| ❌ | GET | `/list/ping` | Test controller |
| ❌ | POST | `/list/questionsEcritesParlementaires` | Parliamentary written questions (paginated) |

**Implemented:** 6/13 (46%)

---

## MISC Controller (3 endpoints)

Miscellaneous services.

| Status | Method | Endpoint | Description |
|--------|--------|----------|-------------|
| ❌ | GET | `/misc/commitId` | Deployment/version info |
| ❌ | GET | `/misc/datesWithoutJo` | Dates without Official Journal |
| ❌ | GET | `/misc/yearsWithoutTable` | Years without tables |

**Implemented:** 0/3 (0%)

---

## SEARCH Controller (5 endpoints)

Search across documents.

| Status | Method | Endpoint | Description |
|--------|--------|----------|-------------|
| ✅ | POST | `/search` | Generic document search |
| ❌ | POST | `/search/canonicalArticleVersion` | Get canonical article versions |
| ❌ | POST | `/search/canonicalVersion` | Get canonical version info |
| ❌ | POST | `/search/nearestVersion` | Get nearest version info |
| ❌ | GET | `/search/ping` | Test controller |

**Implemented:** 1/5 (20%)

---

## SUGGEST Controller (4 endpoints)

Autocomplete/suggestions.

| Status | Method | Endpoint | Description |
|--------|--------|----------|-------------|
| ✅ | POST | `/suggest` | Generic suggestions |
| ❌ | POST | `/suggest/acco` | SIRET/company name suggestions for agreements |
| ❌ | POST | `/suggest/pdc` | Classification plan label suggestions |
| ❌ | GET | `/suggest/ping` | Test controller |

**Implemented:** 1/4 (25%)

---

## Overall Implementation Status

| Controller | Implemented | Total | Percentage |
|------------|-------------|-------|------------|
| CHRONO | 1 | 4 | 25% |
| CONSULT | 12 | 39 | 31% |
| LIST | 6 | 13 | 46% |
| MISC | 0 | 3 | 0% |
| SEARCH | 1 | 5 | 20% |
| SUGGEST | 1 | 4 | 25% |
| **TOTAL** | **21** | **68** | **31%** |

---

## Priority Endpoints to Implement Next

### High Priority (Commonly Used)
1. `/consult/legiPart` - Partial LEGI content (used in searches)
2. `/consult/getArticleByCid` - Article versions (important for history)
3. `/consult/getSectionByCid` - Section content
4. `/consult/getTables` - Annual tables
5. `/list/docsAdmins` - Administrative documents
6. `/list/questionsEcritesParlementaires` - Parliamentary questions
7. `/search/canonicalVersion` - Canonical version info
8. `/chrono/textCid` - Text versioning

### Medium Priority (Specialized Use)
1. `/consult/acco` - Company agreements
2. `/consult/cnil` - CNIL texts
3. `/consult/kaliArticle`, `/kaliSection`, `/kaliCont` - Collective agreement details
4. `/consult/getJoWithNor` - Official Journal by NOR
5. `/list/legislatures` - Legislature list
6. `/list/bodmr` - Decorations bulletins

### Low Priority (Edge Cases / Deprecated)
1. `/consult/code/tableMatieres` - Deprecated (use `/legi/tableMatieres` instead)
2. `/consult/*WithAncienId` - Legacy ID lookups
3. `/misc/*` - Metadata endpoints
4. `*/ping` - Health check endpoints

---

## Notes

- The current implementation covers the **most commonly used endpoints** for retrieving codes, laws, articles, and searching
- Missing endpoints are mostly for:
  - **Versioning/History** (CHRONO controller)
  - **Link management** (concordance, related links, public service links)
  - **Specialized collections** (CNIL, JURI with ancien IDs, KALI sub-resources)
  - **Administrative/metadata** (MISC controller, ping endpoints)
  
- The **core functionality is complete** for most use cases:
  - ✅ Retrieve codes (Code Civil, Code du Travail, etc.)
  - ✅ Retrieve laws and decrees
  - ✅ Retrieve articles
  - ✅ Retrieve legislative dossiers
  - ✅ Search documents
  - ✅ List resources with pagination
  - ✅ Autocomplete suggestions

---

## Recommendations

1. **For production use:** Current implementation is sufficient for most legal research tasks
2. **For comprehensive coverage:** Implement high-priority endpoints listed above
3. **For specialized needs:** Implement specific endpoints as needed (e.g., CHRONO for versioning, KALI sub-endpoints for detailed collective agreement navigation)
