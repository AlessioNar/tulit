import subprocess
import sys
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

failed_parsers = []

def run_parser(name, args):
    # Ensure output directory exists
    for i, arg in enumerate(args):
        if arg in ('--output', '-o') and i + 1 < len(args):
            output_path = args[i + 1]
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
    try:
        result = subprocess.run(args)
        if result.returncode != 0:
            logging.error(f"{name} failed (code {result.returncode})")
            failed_parsers.append(name)
    except Exception as e:
        logging.error(f"Exception while running {name}: {e}")
        failed_parsers.append(name)


# Akoma Ntoso XML (EU)
run_parser('Akoma Ntoso XML (EU)', [
    sys.executable, 'tulit/parsers/xml/akomantoso.py',
    '--input', 'tests/data/akn/eu/32014L0092.akn',
    '--output', 'tests/data/json/xml/akn_eu.json'
])

# Akoma Ntoso XML (France)
run_parser('Akoma Ntoso XML (France)', [
    sys.executable, 'tulit/parsers/xml/akomantoso.py',
    '--input', 'tests/data/akn/france/tas24-021.akn.xml',
    '--output', 'tests/data/json/xml/akn_france.json'
])


# === CLIENT-DOWNLOADED FILES ===

# BOE XML (from client)
run_parser('BOE XML (client)', [
    sys.executable, 'tulit/parsers/xml/boe.py',
    'tests/data/clients/boe/BOE-A-1942-2205.xml',
    'tests/data/json/clients/boe.json'
])

# Formex XML (from Cellar client)
run_parser('Formex XML (Cellar client)', [
    sys.executable, 'tulit/parsers/xml/formex.py',
    '--input', 'tests/data/clients/cellar/c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.02/DOC_1/L_202400903EN.000101.fmx.xml',
    '--output', 'tests/data/json/xml/cellar_formex.json'
])

# Finlex XML (from client)
run_parser('Finlex XML (client)', [
    sys.executable, 'tulit/parsers/xml/akomantoso.py',
    '--input', 'tests/data/clients/finlex/finlex_2024_123.xml',
    '--output', 'tests/data/json/xml/finlex.json'
])

# Germany HTML (from client)
run_parser('Germany HTML (client)', [
    sys.executable, 'tulit/parsers/html/xhtml.py',
    '--input', 'tests/data/clients/germany/germany_eli.html',
    '--output', 'tests/data/json/html/germany.json'
])

# Portugal HTML (from client)
run_parser('Portugal HTML (client)', [
    sys.executable, 'tulit/parsers/html/xhtml.py',
    '--input', 'tests/data/clients/portugal/dre_act_lei_39_2016_12_19_p_pt.html',
    '--output', 'tests/data/json/html/portugal.json'
])

# Veneto HTML (from client)
run_parser('Veneto HTML (client)', [
    sys.executable, 'tulit/parsers/html/veneto.py',
    '--input', 'tests/data/clients/veneto/esg.html',
    '--output', 'tests/data/json/html/veneto.json'
])

if failed_parsers:
    logging.error(f"The following parsers failed: {', '.join(failed_parsers)}")
else:
    logging.info('All parsers executed successfully.')
