import subprocess
import sys
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

failed_clients = []

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
    sys.executable, '-m', 'tulit.client.portugal', 'act', '--type', 'lei', '--number', '39', '--year', '2016', '--month', '12', '--day', '19', '--region', 'p', '--lang', 'pt', '--fmt', 'html', '--dir', './tests/data/clients/portugal', '--logdir', './tests/logs/clients'
])

# Veneto
run_client('Veneto', [
    sys.executable, '-m', 'tulit.client.veneto', '--url', 'https://www.consiglioveneto.it/web/crv/dettaglio-legge?numeroDocumento=10&id=69599315', '--file', './tests/data/clients/veneto/esg.html'
])

# Malta
run_client('Malta', [
    sys.executable, '-m', 'tulit.client.malta', '--eli_path', 'cap/9', '--lang', 'eng', '--fmt', 'xml', '--dir', './tests/data/clients/malta', '--logdir', './tests/logs/clients'
])

# Finlex
run_client('Finlex', [
    sys.executable, '-m', 'tulit.client.finlex', '--year', '2024', '--number', '123', '--dir', './tests/data/clients/finlex', '--logdir', './tests/logs/clients'
])

# Normattiva
run_client('Normattiva', [
    sys.executable, '-m', 'tulit.client.normattiva', '--dir', './tests/data/clients/normattiva', '--logdir', './tests/logs/clients'
])

# Legilux
run_client('Legilux', [
    sys.executable, '-m', 'tulit.client.legilux', '--dir', './tests/data/clients/legilux', '--logdir', './tests/logs/clients'
])

# Legifrance (requires client_id, client_secret, and dossier_id)
# Uncomment and fill in your credentials to use
# run_client('Legifrance', [
#     sys.executable, '-m', 'tulit.client.legifrance', '--client_id', '<YOUR_CLIENT_ID>', '--client_secret', '<YOUR_CLIENT_SECRET>', '--dossier_id', '<DOSSIER_ID>', '--dir', './tests/data/clients/legifrance', '--logdir', './tests/logs/clients'
# ])

# Cellar
run_client('Cellar', [
    sys.executable, '-m', 'tulit.client.cellar', '--celex', '32024R0903', '--format', 'fmx4', '--dir', './tests/data/clients/cellar'
])

# Germany ELI
run_client('Germany ELI', [
    sys.executable, '-m', 'tulit.client.germany', '--eli_url', 'https://testphase.rechtsinformationen.bund.de/norms/eli/bund/banz-at/2025/130/2025-05-05/1/deu/regelungstext-1', '--file', './tests/data/clients/germany/germany_eli.html', '--dir', './tests/data/clients/germany', '--logdir', './tests/logs/clients'
])

# BOE (Spain)
run_client('BOE Spain', [
    sys.executable, '-m', 'tulit.client.boe', '--id', 'BOE-A-1942-2205', '--file', './tests/data/clients/boe/BOE-A-1942-2205.xml'
])

if failed_clients:
    logging.error(f"The following clients failed: {', '.join(failed_clients)}")
else:
    logging.info('All clients executed successfully.')
