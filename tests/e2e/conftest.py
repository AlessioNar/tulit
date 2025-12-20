"""
Shared fixtures and configuration for end-to-end tests.
"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path
import logging

# Configure logging for tests
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

@pytest.fixture(scope="session")
def temp_db_base():
    """Create a persistent database directory structure for e2e tests."""
    db_dir = Path.cwd() / "database" / "e2e_results"
    
    # Create directory structure
    dirs = [
        db_dir / 'sources' / 'eu' / 'eurlex' / 'formex',
        db_dir / 'sources' / 'eu' / 'eurlex' / 'akn',
        db_dir / 'sources' / 'eu' / 'eurlex' / 'regulations' / 'html',
        db_dir / 'sources' / 'eu' / 'eurlex' / 'commission_proposals',
        db_dir / 'sources' / 'member_states' / 'portugal' / 'dre',
        db_dir / 'sources' / 'member_states' / 'italy' / 'normattiva',
        db_dir / 'sources' / 'member_states' / 'luxembourg' / 'legilux',
        db_dir / 'sources' / 'member_states' / 'france' / 'legifrance',
        db_dir / 'sources' / 'member_states' / 'finland' / 'finlex',
        db_dir / 'sources' / 'member_states' / 'malta' / 'moj',
        db_dir / 'sources' / 'member_states' / 'germany' / 'gesetze' / 'legislation',
        db_dir / 'sources' / 'member_states' / 'germany' / 'gesetze' / 'case-law',
        db_dir / 'sources' / 'member_states' / 'germany' / 'gesetze' / 'literature',
        db_dir / 'sources' / 'regional_authorities' / 'italy' / 'veneto',
        db_dir / 'results' / 'eu' / 'proposals',
        db_dir / 'results' / 'eu' / 'formex',
        db_dir / 'results' / 'eu' / 'html',
        db_dir / 'results' / 'eu' / 'akn',
        db_dir / 'results' / 'member_states' / 'portugal',
        db_dir / 'results' / 'member_states' / 'italy',
        db_dir / 'results' / 'member_states' / 'luxembourg',
        db_dir / 'results' / 'member_states' / 'france',
        db_dir / 'results' / 'member_states' / 'finland',
        db_dir / 'results' / 'member_states' / 'malta',
        db_dir / 'results' / 'member_states' / 'germany' / 'legislation',
        db_dir / 'results' / 'member_states' / 'germany' / 'case-law',
        db_dir / 'results' / 'member_states' / 'germany' / 'literature',
        db_dir / 'results' / 'regional' / 'italy' / 'veneto',
        db_dir / 'logs'
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    return db_dir


@pytest.fixture
def db_paths(temp_db_base):
    """Provide database paths as a dictionary."""
    return {
        'base': temp_db_base,
        'sources': temp_db_base / 'sources',
        'results': temp_db_base / 'results',
        'logs': temp_db_base / 'logs'
    }


@pytest.fixture
def sample_files(db_paths):
    """Create sample test files for parser tests."""
    # Create sample HTML proposal file
    proposal_html = """
    <html>
    <body>
        <div class="doc-proposal">
            <h1>COMMISSION PROPOSAL</h1>
            <p>Having regard to the Treaty on the Functioning of the European Union,</p>
            <div class="recitals">
                <p>(1) This is a recital.</p>
                <p>(2) This is another recital.</p>
            </div>
            <div class="chapters">
                <div class="chapter">
                    <h2>Chapter 1</h2>
                    <div class="article">
                        <h3>Article 1</h3>
                        <p>This is the content of article 1.</p>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    proposal_file = db_paths['sources'] / 'eu' / 'eurlex' / 'commission_proposals' / 'sample_proposal.html'
    proposal_file.write_text(proposal_html)

    # Create sample FORMEX file
    formex_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <FORMEX>
        <NOTICE>
            <TF>
                <P>REGULATION (EU) 2024/1234 OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL</P>
            </TF>
            <PREAMBLE>
                <TI>Laying down harmonised rules on artificial intelligence</TI>
                <STI>THE EUROPEAN PARLIAMENT AND THE COUNCIL OF THE EUROPEAN UNION,</STI>
                <P>Having regard to the Treaty on the Functioning of the European Union, and in particular Article 114 thereof,</P>
                <P>Having regard to the proposal from the European Commission,</P>
            </PREAMBLE>
            <BODY>
                <DIVISION TYPE="CHAPTER">
                    <TI>CHAPTER I</TI>
                    <TI>GENERAL PROVISIONS</TI>
                    <DIVISION TYPE="ARTICLE">
                        <TI>Article 1</TI>
                        <TI>Subject matter</TI>
                        <PARA>
                            <NUM>1.</NUM>
                            <CONTENT>
                                <P>The purpose of this Regulation is to improve the functioning of the internal market by laying down a uniform legal framework for the development, placing on the market and use of artificial intelligence systems in the Union.</P>
                            </CONTENT>
                        </PARA>
                    </DIVISION>
                </DIVISION>
            </BODY>
        </NOTICE>
    </FORMEX>"""

    formex_file = db_paths['sources'] / 'eu' / 'eurlex' / 'formex' / 'DOC_1' / 'sample_formex.fmx.xml'
    formex_file.parent.mkdir(exist_ok=True)
    formex_file.write_text(formex_xml)

    return {
        'proposal_html': proposal_file,
        'formex_xml': formex_file
    }


@pytest.fixture(autouse=True)
def setup_environment():
    """Set up environment variables and configuration for e2e tests."""
    # Set test environment variables
    os.environ.setdefault('TULIT_TEST_MODE', 'true')

    # Load .env file if it exists
    try:
        from dotenv import load_dotenv
        env_file = Path(__file__).parent.parent.parent / '.env'
        if env_file.exists():
            load_dotenv(env_file)
    except ImportError:
        pass


# Custom markers
def pytest_configure(config):
    """Add custom markers for e2e tests."""
    config.addinivalue_line("markers", "e2e: End-to-end integration tests")
    config.addinivalue_line("markers", "client_download: Tests that download from external APIs")
    config.addinivalue_line("markers", "parser_integration: Tests that parse downloaded documents")
    config.addinivalue_line("markers", "requires_credentials: Tests that require API credentials")
    config.addinivalue_line("markers", "slow: Tests that take longer than 30 seconds")