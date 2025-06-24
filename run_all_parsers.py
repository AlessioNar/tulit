import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

failed_parsers = []

def run_parser(name, args):
    try:
        result = subprocess.run(args)
        if result.returncode != 0:
            logging.error(f"{name} failed (code {result.returncode})")
            failed_parsers.append(name)
    except Exception as e:
        logging.error(f"Exception while running {name}: {e}")
        failed_parsers.append(name)

# Formex XML
run_parser('Formex XML', [
    sys.executable, 'tulit/parsers/xml/formex.py',
    '--input', 'tests/data/formex/c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.02/DOC_1/L_202400903EN.000101.fmx.xml',
    '--output', 'tests/data/json/iopa.json'
])

# Akoma Ntoso XML
run_parser('Akoma Ntoso XML', [
    sys.executable, 'tulit/parsers/xml/akomantoso.py',
    '--input', 'tests/data/akn/eu/32014L0092.akn',
    '--output', 'tests/data/json/akn.json'
])

# Cellar HTML
run_parser('Cellar HTML', [
    sys.executable, 'tulit/parsers/html/cellar.py',
    '--input', 'tests/data/html/c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.03/DOC_1.html',
    '--output', 'tests/data/json/iopa_html.json'
])

# Veneto HTML
run_parser('Veneto HTML', [
    sys.executable, 'tulit/parsers/html/veneto.py',
    '--input', 'tests/data/html/veneto/esg.html',
    '--output', 'tests/data/json/esg.json'
])

# Veneto HTML (biogas)
run_parser('Veneto HTML (biogas)', [
    sys.executable, 'tulit/parsers/html/veneto.py',
    '--input', 'tests/data/html/veneto/biogas.html',
    '--output', 'tests/data/json/biogas.json'
])

# Veneto HTML (pbc)
run_parser('Veneto HTML (pbc)', [
    sys.executable, 'tulit/parsers/html/veneto.py',
    '--input', 'tests/data/html/veneto/pbc.html',
    '--output', 'tests/data/json/pbc.json'
])

# Veneto JSON (fontane)
run_parser('Veneto HTML (fontane)', [
    sys.executable, 'tulit/parsers/html/veneto.py',
    '--input', 'tests/data/html/veneto/fontane.html',
    '--output', 'tests/data/json/fontane.json'
])

if failed_parsers:
    logging.error(f"The following parsers failed: {', '.join(failed_parsers)}")
else:
    logging.info('All parsers executed successfully.')
