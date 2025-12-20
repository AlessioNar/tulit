import subprocess
import sys
import logging
import os
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logging.warning("python-dotenv not installed. Using system environment variables only.")

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

failed_clients = []

# Create database directory structure outside the package
DB_BASE = Path(__file__).parent.parent / 'database'
DB_SOURCES = DB_BASE / 'sources'
DB_RESULTS = DB_BASE / 'results'
DB_LOGS = DB_BASE / 'logs'

# Create directory structure following the same hierarchy as tests
def ensure_dirs():
    """Ensure database directory structure exists"""
    dirs = [
        DB_SOURCES / 'eu' / 'eurlex' / 'formex',
        DB_SOURCES / 'eu' / 'eurlex' / 'akn',
        DB_SOURCES / 'eu' / 'eurlex' / 'regulations' / 'html',
        DB_SOURCES / 'member_states' / 'portugal' / 'dre',
        DB_SOURCES / 'member_states' / 'italy' / 'normattiva',
        DB_SOURCES / 'member_states' / 'luxembourg' / 'legilux',
        DB_SOURCES / 'member_states' / 'france' / 'legifrance',
        DB_SOURCES / 'member_states' / 'finland' / 'finlex',
        DB_SOURCES / 'member_states' / 'malta' / 'moj',
        DB_SOURCES / 'member_states' / 'germany' / 'gesetze' / 'legislation',
        DB_SOURCES / 'member_states' / 'germany' / 'gesetze' / 'case-law',
        DB_SOURCES / 'member_states' / 'germany' / 'gesetze' / 'literature',
        DB_SOURCES / 'regional_authorities' / 'italy' / 'veneto',
        DB_RESULTS / 'eu',
        DB_RESULTS / 'member_states',
        DB_RESULTS / 'regional',
        DB_LOGS
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    logging.info(f"Database directories created at: {DB_BASE}")

ensure_dirs()

def run_client(name, args):
    # Ensure output directories exist for client data
    for i, arg in enumerate(args):
        if arg in ('--dir', '--file') and i + 1 < len(args):
            path = args[i + 1]
            if arg == '--dir':
                os.makedirs(path, exist_ok=True)
            elif arg == '--file':
                output_dir = os.path.dirname(path)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
    try:
        result = subprocess.run(args)
        if result.returncode != 0:
            logging.error(f"{name} failed (code {result.returncode})")
            failed_clients.append(name)
    except Exception as e:
        logging.error(f"Exception while running {name}: {e}")
        failed_clients.append(name)

# Portugal DRE
run_client('Portugal DRE', [
    sys.executable, '-m', 'tulit.client.portugal', 'act', 
    '--type', 'lei', '--number', '39', '--year', '2016', '--month', '12', '--day', '19', 
    '--region', 'p', '--lang', 'pt', '--fmt', 'html', 
    '--dir', str(DB_SOURCES / 'member_states' / 'portugal' / 'dre'), 
    '--logdir', str(DB_LOGS)
])

# Veneto (Note: Veneto client doesn't support --dir parameter yet)
run_client('Veneto', [
    sys.executable, '-m', 'tulit.client.veneto', 
    '--url', 'https://www.consiglioveneto.it/web/crv/dettaglio-legge?numeroDocumento=10&id=69599315', 
    '--file', str(DB_SOURCES / 'regional_authorities' / 'italy' / 'veneto' / 'esg.html')
])

# Malta - DISABLED: API returning HTML instead of expected PDF format
# Issue: Expected PDF response but got text/html; charset=utf-8
# TODO: Check Malta MOJ API documentation for correct endpoint or format
# run_client('Malta', [
#     sys.executable, '-m', 'tulit.client.malta', 
#     '--eli_path', 'cap/9', '--lang', 'eng', '--fmt', 'pdf', 
#     '--dir', str(DB_SOURCES / 'member_states' / 'malta' / 'moj'), 
#     '--logdir', str(DB_LOGS)
# ])

# Finlex
run_client('Finlex', [
    sys.executable, '-m', 'tulit.client.finlex', 
    '--year', '2024', '--number', '123', 
    '--dir', str(DB_SOURCES / 'member_states' / 'finland' / 'finlex'), 
    '--logdir', str(DB_LOGS)
])

# Normattiva (Italy) - Example with specific document
run_client('Normattiva', [
    sys.executable, '-m', 'tulit.client.normattiva',
    '--dataGU', '20241231',  # Format: YYYYMMDD
    '--codiceRedaz', '24G00229',
    '--dataVigenza', '20251020',
    '--dir', str(DB_SOURCES / 'member_states' / 'italy' / 'normattiva'),
    '--logdir', str(DB_LOGS)
])

# Legilux (Luxembourg) - Example with valid ELI using data API endpoint
run_client('Legilux', [
    sys.executable, '-m', 'tulit.client.legilux',
    '--eli', 'http://data.legilux.public.lu/eli/etat/leg/loi/2006/07/31/n2/jo',
    '--dir', str(DB_SOURCES / 'member_states' / 'luxembourg' / 'legilux'),
    '--logdir', str(DB_LOGS)
])

# Legifrance (France) - Download Code Civil (requires credentials)
# To use: Set environment variables LEGIFRANCE_CLIENT_ID and LEGIFRANCE_CLIENT_SECRET
# Or uncomment and fill in your credentials
legifrance_client_id = os.environ.get('LEGIFRANCE_CLIENT_ID')
legifrance_client_secret = os.environ.get('LEGIFRANCE_CLIENT_SECRET')

if legifrance_client_id and legifrance_client_secret:
    run_client('Legifrance', [
        sys.executable, '-m', 'tulit.client.legifrance',
        '--client_id', legifrance_client_id,
        '--client_secret', legifrance_client_secret,
        '--action', 'download_code',
        '--text_id', 'LEGITEXT000006070721',  # Code Civil
        '--dir', str(DB_SOURCES / 'member_states' / 'france' / 'legifrance'),
        '--logdir', str(DB_LOGS)
    ])
else:
    logging.warning('Legifrance client skipped - set LEGIFRANCE_CLIENT_ID and LEGIFRANCE_CLIENT_SECRET environment variables to enable')

# Alternative: Search example (also requires credentials)
# if legifrance_client_id and legifrance_client_secret:
#     run_client('Legifrance Search', [
#         sys.executable, '-m', 'tulit.client.legifrance',
#         '--client_id', legifrance_client_id,
#         '--client_secret', legifrance_client_secret,
#         '--action', 'search',
#         '--query', 'droit du travail',
#         '--page_size', '5',
#         '--dir', str(DB_SOURCES / 'member_states' / 'france' / 'legifrance'),
#         '--logdir', str(DB_LOGS)
#     ])


# Cellar - Download FMX4 document by CELEX number
run_client('Cellar', [
    sys.executable, '-m', 'tulit.client.cellar', 
    '--celex', '32024R0903', '--format', 'fmx4', 
    '--dir', str(DB_SOURCES / 'eu' / 'eurlex' / 'formex'),
    '--logdir', str(DB_LOGS)
])

# Germany - Search and download recent legislation (XML - LegalDocML format)
run_client('Germany Legislation', [
    sys.executable, '-m', 'tulit.client.germany', 
    '--type', 'legislation',
    '--search', 'Auslandszuschlagsverordnung',
    '--format', 'xml',
    '--dir', str(DB_SOURCES / 'member_states' / 'germany' / 'gesetze' / 'legislation'), 
    '--logdir', str(DB_LOGS)
])

if failed_clients:
    logging.error(f"The following clients failed: {', '.join(failed_clients)}")
else:
    logging.info('All clients executed successfully.')
