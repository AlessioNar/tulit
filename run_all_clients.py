import subprocess
import sys
import logging
import os
from pathlib import Path

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
        DB_SOURCES / 'member_states' / 'germany' / 'gesetze',
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

# Malta
run_client('Malta', [
    sys.executable, '-m', 'tulit.client.malta', 
    '--eli_path', 'cap/9', '--lang', 'eng', '--fmt', 'xml', 
    '--dir', str(DB_SOURCES / 'member_states' / 'malta' / 'moj'), 
    '--logdir', str(DB_LOGS)
])

# Finlex
run_client('Finlex', [
    sys.executable, '-m', 'tulit.client.finlex', 
    '--year', '2024', '--number', '123', 
    '--dir', str(DB_SOURCES / 'member_states' / 'finland' / 'finlex'), 
    '--logdir', str(DB_LOGS)
])

# Normattiva
run_client('Normattiva', [
    sys.executable, '-m', 'tulit.client.normattiva',
    '--dir', str(DB_SOURCES / 'member_states' / 'italy' / 'normattiva'),
    '--logdir', str(DB_LOGS)
])

# Legilux
run_client('Legilux', [
    sys.executable, '-m', 'tulit.client.legilux',
    '--dir', str(DB_SOURCES / 'member_states' / 'luxembourg' / 'legilux'),
    '--logdir', str(DB_LOGS)
])

# Legifrance (requires client_id, client_secret, and dossier_id)
# Uncomment and fill in your credentials to use
# run_client('Legifrance', [
#     sys.executable, '-m', 'tulit.client.legifrance', 
#     '--client_id', '<YOUR_CLIENT_ID>', 
#     '--client_secret', '<YOUR_CLIENT_SECRET>', 
#     '--dossier_id', '<DOSSIER_ID>',
#     '--dir', str(DB_SOURCES / 'member_states' / 'france' / 'legifrance'),
#     '--logdir', str(DB_LOGS)
# ])

# Cellar
run_client('Cellar', [
    sys.executable, '-m', 'tulit.client.cellar', 
    '--celex', '32024R0903', '--format', 'fmx4', 
    '--dir', str(DB_SOURCES / 'eu' / 'eurlex' / 'formex'),
    '--logdir', str(DB_LOGS)
])

# Germany ELI
run_client('Germany ELI', [
    sys.executable, '-m', 'tulit.client.germany', 
    '--eli_url', 'https://testphase.rechtsinformationen.bund.de/norms/eli/bund/banz-at/2025/130/2025-05-05/1/deu/regelungstext-1', 
    '--file', 'germany_eli.html', 
    '--dir', str(DB_SOURCES / 'member_states' / 'germany' / 'gesetze'), 
    '--logdir', str(DB_LOGS)
])

if failed_clients:
    logging.error(f"The following clients failed: {', '.join(failed_clients)}")
else:
    logging.info('All clients executed successfully.')
