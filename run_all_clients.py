import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

failed_clients = []

def run_client(name, args):
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
    sys.executable, '-m', 'tulit.client.portugal', 'act', '--type', 'lei', '--number', '39', '--year', '2016', '--month', '12', '--day', '19', '--region', 'p', '--lang', 'pt', '--fmt', 'html', '--dir', './tests/data/portugal', '--logdir', './tests/logs'
])

# Veneto
run_client('Veneto', [
    sys.executable, '-m', 'tulit.client.veneto', '--url', 'https://www.consiglioveneto.it/web/crv/dettaglio-legge?numeroDocumento=10&id=69599315', '--file', 'esg.html'
])

# Malta
run_client('Malta', [
    sys.executable, '-m', 'tulit.client.malta', '--eli_path', 'cap/9', '--lang', 'eng', '--fmt', 'xml', '--dir', './tests/data/malta', '--logdir', './tests/logs'
])

# Finlex
run_client('Finlex', [
    sys.executable, '-m', 'tulit.client.finlex', '--year', '2024', '--number', '123', '--dir', './tests/data/finlex', '--logdir', './tests/logs'
])

# Normattiva
run_client('Normattiva', [
    sys.executable, '-m', 'tulit.client.normattiva'
])

# Legilux
run_client('Legilux', [
    sys.executable, '-m', 'tulit.client.legilux'
])

# Legifrance (requires client_id, client_secret, and dossier_id)
# Uncomment and fill in your credentials to use
# run_client('Legifrance', [
#     sys.executable, '-m', 'tulit.client.legifrance', '--client_id', '<YOUR_CLIENT_ID>', '--client_secret', '<YOUR_CLIENT_SECRET>', '--dossier_id', '<DOSSIER_ID>'
# ])

# Cellar
run_client('Cellar', [
    sys.executable, '-m', 'tulit.client.cellar', '--celex', '32024R0903', '--format', 'fmx4', '--dir', './tests/data/formex'
])

if failed_clients:
    logging.error(f"The following clients failed: {', '.join(failed_clients)}")
else:
    logging.info('All clients executed successfully.')
