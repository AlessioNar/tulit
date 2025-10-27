import requests
from SPARQLWrapper import SPARQLWrapper, JSON, POST

# First, let's query what's available for a simple CELEX
sparql = SPARQLWrapper("http://publications.europa.eu/webapi/rdf/sparql")

# Query for CELEX 32008R1137 (a known older regulation)
sparql_query = """
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
PREFIX purl: <http://purl.org/dc/elements/1.1/>

SELECT DISTINCT ?cellarURIs, ?manif, ?format
WHERE {
    ?work owl:sameAs <http://publications.europa.eu/resource/celex/32008R1137> .
    ?expr cdm:expression_belongs_to_work ?work ;
           cdm:expression_uses_language ?lang .
    ?lang purl:identifier ?langCode .
    ?manif cdm:manifestation_manifests_expression ?expr;
           cdm:manifestation_type ?format.
    ?cellarURIs cdm:item_belongs_to_manifestation ?manif.

    FILTER(str(?langCode)="ENG")
}
ORDER BY ?cellarURIs
LIMIT 5
"""

sparql.setQuery(sparql_query)
sparql.setMethod(POST)
sparql.setReturnFormat(JSON)

print("=" * 60)
print("SPARQL Query Results for 32008R1137:")
print("=" * 60)

try:
    results = sparql.query().convert()
    bindings = results["results"]["bindings"]
    print(f"Found {len(bindings)} results\n")
    
    for binding in bindings:
        cellar = binding['cellarURIs']['value'].split('cellar/')[1]
        fmt = binding['format']['value']
        print(f"Format: {fmt}")
        print(f"Cellar ID: {cellar}")
        print()
        
        # Now test accessing this cellar ID
        test_urls = [
            f'https://publications.europa.eu/resource/cellar/{cellar}',
            f'https://publications.europa.eu/resource/cellar/{cellar}.zip',
            f'https://publications.europa.eu/resource/cellar/{cellar}/{fmt}.zip',
        ]
        
        for url in test_urls:
            r = requests.head(url, timeout=5, allow_redirects=False)
            print(f"  {url.split('cellar/')[-1]}")
            print(f"    Status: {r.status_code}")
            if r.status_code in [200, 302, 301]:
                print(f"    -> SUCCESS!")
        print()
        
except Exception as e:
    print(f"Error: {e}")
