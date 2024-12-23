# Configuration file for the Sphinx documentation builder.

import os
import sys

# -- Project information

project = 'tulit'
author = 'AlessioNar'

release = '0.0.3'
version = '0.0.3'

# -- General configuration
sys.path.insert(0, os.path.abspath('../tulit'))

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',  

]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

# -- Options for HTML output
autodocs_mock_imports = ['tulit']

html_theme = 'sphinx_rtd_theme'

# -- Options for EPUB output
epub_show_urls = 'footnote'