import logging
import os
import re
import requests
from SPARQLWrapper import JSON, SPARQLWrapper
from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError

LEGILUX_DATA = 'https://data.legilux.public.lu'
SPARQL_ENDPOINT = f'{LEGILUX_DATA}/sparqlendpoint'
JOLUX = 'http://data.legilux.public.lu/resource/ontology/jolux#'
_ACT_PATH = re.compile(r'^(?:https?://(?:data\.)?legilux\.public\.lu/)?(?:eli/)?(etat/[a-z]+/[a-z]+/\d{4}/\d{2}/\d{2}/[\w-]+)')


def act_path(identifier):
    """
    The ELI path of a Luxembourg act, without version.

    'etat/leg/loi/2016/07/23/n21', 'eli/etat/leg/loi/2016/07/23/n21/jo' and
    'http://data.legilux.public.lu/eli/etat/leg/loi/2016/07/23/n21/jo/fr/xml'
    -> 'etat/leg/loi/2016/07/23/n21'
    """
    match = _ACT_PATH.match(identifier.strip())
    if not match:
        raise ValueError(
            f"'{identifier}' is not a Legilux ELI; use e.g. 'etat/leg/loi/2016/07/23/n21'")
    return match.group(1)

class LegiluxClient(Client):
    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.logger = logging.getLogger(self.__class__.__name__)
        #self.endpoint = "https://legilux.public.lu/eli/etat/leg/loi"

    def build_request_url(self, eli) -> str:
        self.logger.info(f"Building request URL for ELI: {eli}")
        # The data API endpoint returns XML by default
        return eli
    
    def fetch_content(self, url):
        self.logger.info(f"Fetching content from URL: {url}")
        headers = {
            "Accept": "application/xml, text/xml, */*",
            "User-Agent": "TulitClient/1.0"
        }
        response = requests.get(url, headers=headers, timeout=30)
        return response

    def download(self, eli):
        file_paths = []
        url = self.build_request_url(eli)
        response = self.fetch_content(url)
        # Extract filename from ELI - handle different document types
        eli_parts = eli.strip('/').split('/')
        if len(eli_parts) >= 6:
            # Standard format: .../eli/etat/leg/loi/2006/07/31/n2/jo
            # Extract meaningful parts for filename
            doc_type = eli_parts[-6] if len(eli_parts) > 6 else 'doc'
            year = eli_parts[-5] if len(eli_parts) > 5 else 'unknown'
            month = eli_parts[-4] if len(eli_parts) > 4 else 'unknown'
            day = eli_parts[-3] if len(eli_parts) > 3 else 'unknown'
            doc_id = eli_parts[-2] if len(eli_parts) > 2 else 'unknown'
            filename = f"{doc_type}_{year}_{month}_{day}_{doc_id}"
        else:
            # Fallback: use last parts of ELI
            filename = '_'.join(eli_parts[-4:])
        
        # Clean filename
        filename = filename.replace('/', '_').replace('?', '_').replace('&', '_')
        if response.status_code == 200:
            file_paths.append(self.handle_response(response, filename=filename))
            self.logger.info(f"Document downloaded successfully and saved to {file_paths}")
            return file_paths
        else:
            self.logger.error(f"Failed to download document. Status code: {response.status_code}")
            raise NetworkError(f"Failed to download document. Status code: {response.status_code}")

    def _sparql(self, query):
        sparql = SPARQLWrapper(SPARQL_ENDPOINT)
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        try:
            return sparql.query().convert()['results']['bindings']
        except Exception as e:
            raise NetworkError(f"Legilux SPARQL query failed: {e}") from e

    def consolidation_dates(self, identifier):
        """ISO dates of the consolidated versions of an act, oldest first."""
        work = f'http://data.legilux.public.lu/eli/{act_path(identifier)}'
        prefix = f'{work}/consolide/'
        # Consolidations are members of the act ('jolux:isMemberOf'); scanning every
        # subject for the prefix instead takes the endpoint some 40 seconds
        rows = self._sparql(
            f'SELECT DISTINCT ?s WHERE {{ ?s <{JOLUX}isMemberOf> <{work}> . '
            f'FILTER(STRSTARTS(STR(?s), "{prefix}")) }}'
        )
        stamps = {m.group(1) for r in rows
                  for m in [re.match(re.escape(prefix) + r'(\d{8})$', r['s']['value'])] if m}
        return [f'{s[:4]}-{s[4:6]}-{s[6:]}' for s in sorted(stamps)]

    def work_metadata(self, identifier):
        """Metadata of the act as published (jolux properties: dateDocument, publicationDate, ...)."""
        work = f'http://data.legilux.public.lu/eli/{act_path(identifier)}/jo'
        rows = self._sparql(f'SELECT ?p ?o WHERE {{ <{work}> ?p ?o }}')
        metadata = {}
        for row in rows:
            prop = row['p']['value']
            if prop.startswith(JOLUX):
                metadata.setdefault(prop[len(JOLUX):], row['o']['value'])
        return metadata

    def download_version(self, identifier, consolidated=None, language='fr'):
        """
        Download the Akoma Ntoso XML of an act from the Legilux filestore.

        ``consolidated`` is the ISO date of a consolidated version, or None for
        the act as published in the Journal officiel. Returns the file path.
        """
        path = act_path(identifier)
        version = f"consolide/{consolidated.replace('-', '')}" if consolidated else 'jo'
        name = f"eli-{path}-{version}-{language}-xml".replace('/', '-')
        url = f'{LEGILUX_DATA}/filestore/eli/{path}/{version}/{language}/xml/{name}.xml'
        target = os.path.join(self.download_dir, 'LU', f'{name}.xml')
        if not os.path.exists(target):
            response = requests.get(url, headers={'User-Agent': 'tulit (+https://github.com/AlessioNar/tulit)'},
                                    timeout=60)
            if response.status_code == 404:
                raise FileLoadError(f"Legilux has no XML for {path} ({version})")
            if response.status_code != 200 or b'akomaNtoso' not in response.content[:2000]:
                raise NetworkError(f"Unexpected Legilux response for {url}: HTTP {response.status_code}")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as f:
                f.write(response.content)
        return target

