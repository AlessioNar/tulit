import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock
from tulit.client.legifrance import LegifranceClient


@pytest.fixture
def client():
    """Create a LegifranceClient instance for testing."""
    return LegifranceClient(
        client_id="test_client_id",
        client_secret="test_client_secret",
        download_dir="./tests/data/legifrance",
        log_dir="./tests/logs"
    )


@pytest.fixture
def mock_token_response():
    """Mock OAuth token response."""
    return {"access_token": "test_token_12345", "expires_in": 3600}


@pytest.fixture
def mock_code_response():
    """Mock code consultation response."""
    return {
        "textId": "LEGITEXT000006070721",
        "title": "Code civil",
        "articles": [
            {"id": "LEGIARTI000006419283", "num": "1", "content": "Article content"}
        ],
        "date": "2024-01-01"
    }


class TestLegifranceClient:
    """Test suite for LegifranceClient."""

    def test_initialization(self, client):
        """Test client initialization."""
        assert client.client_id == "test_client_id"
        assert client.client_secret == "test_client_secret"
        assert client.base_url == "https://sandbox-api.piste.gouv.fr/dila/legifrance/lf-engine-app"
        assert client.oauth_url == "https://sandbox-oauth.piste.gouv.fr/api/oauth/token"

    @patch('requests.post')
    def test_get_token_success(self, mock_post, client, mock_token_response):
        """Test successful OAuth token retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = mock_token_response
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        token = client.get_token()

        assert token == "test_token_12345"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == client.oauth_url
        assert call_args[1]['data']['grant_type'] == 'client_credentials'

    @patch('requests.post')
    def test_get_token_failure(self, mock_post, client):
        """Test OAuth token retrieval failure."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("Auth failed")
        mock_post.return_value = mock_response

        with pytest.raises(Exception, match="Auth failed"):
            client.get_token()

    @patch('requests.post')
    def test_make_request_success(self, mock_post, client, mock_token_response, mock_code_response):
        """Test successful API request."""
        # Mock token request
        mock_token_resp = Mock()
        mock_token_resp.json.return_value = mock_token_response
        mock_token_resp.raise_for_status = Mock()

        # Mock API request
        mock_api_resp = Mock()
        mock_api_resp.json.return_value = mock_code_response
        mock_api_resp.raise_for_status = Mock()
        mock_api_resp.headers = {'Content-Type': 'application/json'}

        mock_post.side_effect = [mock_token_resp, mock_api_resp]

        result = client._make_request('/consult/code', {'textId': 'LEGITEXT000006070721'})

        assert result == mock_code_response
        assert mock_post.call_count == 2

    @patch.object(LegifranceClient, '_make_request')
    def test_consult_code(self, mock_request, client, mock_code_response):
        """Test code consultation."""
        mock_request.return_value = mock_code_response

        result = client.consult_code("LEGITEXT000006070721", date="2024-01-01")

        mock_request.assert_called_once_with(
            '/consult/code',
            {'textId': 'LEGITEXT000006070721', 'date': '2024-01-01'}
        )
        assert result == mock_code_response

    @patch.object(LegifranceClient, '_make_request')
    def test_consult_code_without_date(self, mock_request, client, mock_code_response):
        """Test code consultation without date."""
        mock_request.return_value = mock_code_response

        result = client.consult_code("LEGITEXT000006070721")

        mock_request.assert_called_once_with(
            '/consult/code',
            {'textId': 'LEGITEXT000006070721'}
        )

    @patch.object(LegifranceClient, '_make_request')
    def test_consult_article(self, mock_request, client):
        """Test article consultation."""
        mock_article = {"id": "LEGIARTI000006419283", "content": "Article content"}
        mock_request.return_value = mock_article

        result = client.consult_article("LEGIARTI000006419283")

        mock_request.assert_called_once_with(
            '/consult/getArticle',
            {'id': 'LEGIARTI000006419283'}
        )
        assert result == mock_article

    @patch.object(LegifranceClient, '_make_request')
    def test_consult_dossier_legislatif(self, mock_request, client):
        """Test legislative dossier consultation."""
        mock_dossier = {"textId": "JORFTEXT123", "title": "Dossier test"}
        mock_request.return_value = mock_dossier

        result = client.consult_dossier_legislatif("JORFTEXT123")

        mock_request.assert_called_once_with(
            '/consult/dossierLegislatif',
            {'textId': 'JORFTEXT123'}
        )
        assert result == mock_dossier

    @patch.object(LegifranceClient, '_make_request')
    def test_list_codes(self, mock_request, client):
        """Test listing codes with pagination."""
        mock_list = {
            "results": [
                {"textId": "LEGITEXT000006070721", "title": "Code civil"},
                {"textId": "LEGITEXT000006072050", "title": "Code du travail"}
            ],
            "totalResults": 2,
            "pageNumber": 1,
            "pageSize": 100
        }
        mock_request.return_value = mock_list

        result = client.list_codes(page_number=1, page_size=100)

        mock_request.assert_called_once_with(
            '/list/code',
            {'pageNumber': 1, 'pageSize': 100}
        )
        assert result == mock_list

    @patch.object(LegifranceClient, '_make_request')
    def test_list_loda(self, mock_request, client):
        """Test listing LODA texts."""
        mock_list = {"results": [], "totalResults": 0}
        mock_request.return_value = mock_list

        result = client.list_loda(page_number=1, page_size=50, date="2024-01-01")

        mock_request.assert_called_once_with(
            '/list/loda',
            {'pageNumber': 1, 'pageSize': 50, 'date': '2024-01-01'}
        )

    @patch.object(LegifranceClient, '_make_request')
    def test_search(self, mock_request, client):
        """Test document search."""
        mock_search = {
            "results": [{"textId": "LEGITEXT123", "title": "Result 1"}],
            "totalResults": 1
        }
        mock_request.return_value = mock_search

        result = client.search("droit du travail", page_number=1, page_size=10)

        mock_request.assert_called_once_with(
            '/search',
            {'search': 'droit du travail', 'pageNumber': 1, 'pageSize': 10}
        )
        assert result == mock_search

    @patch.object(LegifranceClient, '_make_request')
    def test_search_with_filters(self, mock_request, client):
        """Test document search with filters."""
        mock_search = {"results": [], "totalResults": 0}
        mock_request.return_value = mock_search

        filters = {"dateDebut": "2020-01-01", "dateFin": "2024-01-01"}
        result = client.search("test", page_number=1, page_size=10, filters=filters)

        expected_payload = {
            'search': 'test',
            'pageNumber': 1,
            'pageSize': 10,
            'dateDebut': '2020-01-01',
            'dateFin': '2024-01-01'
        }
        mock_request.assert_called_once_with('/search', expected_payload)

    @patch.object(LegifranceClient, '_make_request')
    def test_suggest(self, mock_request, client):
        """Test autocomplete suggestions."""
        mock_suggestions = {
            "suggestions": ["code civil", "code du travail", "code pénal"]
        }
        mock_request.return_value = mock_suggestions

        result = client.suggest("code")

        mock_request.assert_called_once_with(
            '/suggest',
            {'query': 'code'}
        )
        assert result == mock_suggestions

    @patch.object(LegifranceClient, '_make_request')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    def test_download(self, mock_makedirs, mock_open, mock_request, client, mock_code_response):
        """Test document download and save."""
        mock_request.return_value = mock_code_response
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        result = client.download('/consult/code', {'textId': 'LEGITEXT000006070721'}, 'test_file')

        assert 'test_file.json' in result
        mock_open.assert_called_once()
        # json.dump writes to the file, so we check that write was called
        assert mock_file.write.call_count > 0

    @patch.object(LegifranceClient, 'download')
    def test_download_code(self, mock_download, client):
        """Test code download convenience method."""
        mock_download.return_value = "/path/to/code.json"

        result = client.download_code("LEGITEXT000006070721", date="2024-01-01")

        mock_download.assert_called_once()
        call_args = mock_download.call_args
        assert call_args[0][0] == '/consult/code'
        assert call_args[0][1] == {'textId': 'LEGITEXT000006070721', 'date': '2024-01-01'}
        assert 'code_LEGITEXT000006070721_2024-01-01' in call_args[0][2]

    @patch.object(LegifranceClient, 'download')
    def test_download_dossier_legislatif(self, mock_download, client):
        """Test dossier download convenience method."""
        mock_download.return_value = "/path/to/dossier.json"

        result = client.download_dossier_legislatif("JORFTEXT123")

        mock_download.assert_called_once()
        call_args = mock_download.call_args
        assert call_args[0][0] == '/consult/dossierLegislatif'
        assert call_args[0][1] == {'textId': 'JORFTEXT123'}
        assert 'dossier_JORFTEXT123' in call_args[0][2]

    @patch.object(LegifranceClient, '_make_request')
    def test_consult_jorf(self, mock_request, client):
        """Test JORF consultation."""
        mock_jorf = {"textId": "JORFTEXT123", "title": "JORF test"}
        mock_request.return_value = mock_jorf

        result = client.consult_jorf("JORFTEXT123")

        mock_request.assert_called_once_with(
            '/consult/jorf',
            {'textId': 'JORFTEXT123'}
        )

    @patch.object(LegifranceClient, '_make_request')
    def test_consult_table_matieres(self, mock_request, client):
        """Test table of contents consultation."""
        mock_toc = {"sections": [{"title": "Section 1"}]}
        mock_request.return_value = mock_toc

        result = client.consult_table_matieres("LEGITEXT000006070721", date="2024-01-01")

        mock_request.assert_called_once_with(
            '/consult/legi/tableMatieres',
            {'textId': 'LEGITEXT000006070721', 'date': '2024-01-01'}
        )

    @patch.object(LegifranceClient, '_make_request')
    def test_list_dossiers_legislatifs(self, mock_request, client):
        """Test listing legislative dossiers."""
        mock_list = {"results": [], "totalResults": 0}
        mock_request.return_value = mock_list

        result = client.list_dossiers_legislatifs(page_number=2, page_size=25)

        mock_request.assert_called_once_with(
            '/list/dossiersLegislatifs',
            {'pageNumber': 2, 'pageSize': 25}
        )

    @patch.object(LegifranceClient, '_make_request')
    def test_list_conventions(self, mock_request, client):
        """Test listing collective agreements."""
        mock_list = {"results": [], "totalResults": 0}
        mock_request.return_value = mock_list

        result = client.list_conventions()

        mock_request.assert_called_once_with(
            '/list/conventions',
            {'pageNumber': 1, 'pageSize': 100}
        )
    
    # ==================== NEW TESTS FOR EXPANDED FUNCTIONALITY ====================
    
    @patch.object(LegifranceClient, '_make_request')
    def test_consult_legi_part(self, mock_request, client):
        """Test partial LEGI content consultation."""
        mock_response = {"textId": "LEGITEXT123", "partial": True}
        mock_request.return_value = mock_response

        result = client.consult_legi_part("LEGITEXT123", searched_string="test", date="2024-01-01")

        mock_request.assert_called_once_with(
            '/consult/legiPart',
            {'textId': 'LEGITEXT123', 'searchedString': 'test', 'date': '2024-01-01'}
        )
    
    @patch.object(LegifranceClient, '_make_request')
    def test_consult_article_by_cid(self, mock_request, client):
        """Test article versions by CID."""
        mock_response = {"versions": []}
        mock_request.return_value = mock_response

        result = client.consult_article_by_cid("CID123")

        mock_request.assert_called_once_with('/consult/getArticleByCid', {'cid': 'CID123'})
    
    @patch.object(LegifranceClient, '_make_request')
    def test_consult_tables(self, mock_request, client):
        """Test annual tables consultation."""
        mock_response = {"tables": []}
        mock_request.return_value = mock_response

        result = client.consult_tables(2020, 2024)

        mock_request.assert_called_once_with(
            '/consult/getTables',
            {'startYear': 2020, 'endYear': 2024}
        )
    
    @patch.object(LegifranceClient, '_make_request')
    def test_list_docs_admins(self, mock_request, client):
        """Test listing administrative documents."""
        mock_response = {"results": [], "totalResults": 0}
        mock_request.return_value = mock_response

        result = client.list_docs_admins(2020, 2024, page_number=1, page_size=50)

        mock_request.assert_called_once_with(
            '/list/docsAdmins',
            {'startYear': 2020, 'endYear': 2024, 'pageNumber': 1, 'pageSize': 50}
        )
    
    @patch.object(LegifranceClient, '_make_request')
    def test_list_legislatures(self, mock_request, client):
        """Test listing legislatures."""
        mock_response = {"legislatures": []}
        mock_request.return_value = mock_response

        result = client.list_legislatures()

        mock_request.assert_called_once_with('/list/legislatures', {})
    
    @patch.object(LegifranceClient, '_make_request')
    def test_search_canonical_version(self, mock_request, client):
        """Test canonical version search."""
        mock_response = {"version": "1.0"}
        mock_request.return_value = mock_response

        result = client.search_canonical_version("LEGITEXT123", date="2024-01-01")

        mock_request.assert_called_once_with(
            '/search/canonicalVersion',
            {'textId': 'LEGITEXT123', 'date': '2024-01-01'}
        )
    
    @patch.object(LegifranceClient, '_make_request')
    def test_search_nearest_version(self, mock_request, client):
        """Test nearest version search."""
        mock_response = {"nearestVersion": "2023-12-01"}
        mock_request.return_value = mock_response

        result = client.search_nearest_version("LEGITEXT123", "2024-01-15")

        mock_request.assert_called_once_with(
            '/search/nearestVersion',
            {'textId': 'LEGITEXT123', 'date': '2024-01-15'}
        )
    
    @patch.object(LegifranceClient, '_make_request')
    def test_chrono_text_version(self, mock_request, client):
        """Test text version retrieval."""
        mock_response = {"version": "current"}
        mock_request.return_value = mock_response

        result = client.chrono_text_version("CID123", date="2024-01-01")

        mock_request.assert_called_once_with(
            '/chrono/textCid',
            {'textCid': 'CID123', 'date': '2024-01-01'}
        )
    
    @patch.object(LegifranceClient, '_make_request')
    def test_suggest_acco(self, mock_request, client):
        """Test company agreement suggestions."""
        mock_response = {"suggestions": ["Company A", "Company B"]}
        mock_request.return_value = mock_response

        result = client.suggest_acco("company")

        mock_request.assert_called_once_with('/suggest/acco', {'query': 'company'})
    
    @patch.object(LegifranceClient, '_make_request')
    def test_misc_commit_id(self, mock_request, client):
        """Test deployment info retrieval."""
        mock_response = {"commitId": "abc123", "version": "2.4.2"}
        mock_request.return_value = mock_response

        result = client.misc_commit_id()

        mock_request.assert_called_once_with('/misc/commitId', {}, method='GET')
    
    @patch.object(LegifranceClient, '_make_request')
    def test_consult_acco(self, mock_request, client):
        """Test company agreement consultation."""
        mock_response = {"textId": "ACCO123", "content": "Agreement content"}
        mock_request.return_value = mock_response

        result = client.consult_acco("ACCO123")

        mock_request.assert_called_once_with('/consult/acco', {'textId': 'ACCO123'})
    
    @patch.object(LegifranceClient, '_make_request')
    def test_consult_last_n_jo(self, mock_request, client):
        """Test last N official journals."""
        mock_response = {"journals": []}
        mock_request.return_value = mock_response

        result = client.consult_last_n_jo(5)

        mock_request.assert_called_once_with('/consult/lastNJo', {'n': 5})
    
    @patch.object(LegifranceClient, '_make_request')
    def test_consult_same_num_article(self, mock_request, client):
        """Test articles with same number."""
        mock_response = {"articles": []}
        mock_request.return_value = mock_response

        result = client.consult_same_num_article("LEGIARTI123")

        mock_request.assert_called_once_with('/consult/sameNumArticle', {'id': 'LEGIARTI123'})
    
    @patch.object(LegifranceClient, '_make_request')
    def test_consult_concordance_links(self, mock_request, client):
        """Test article concordance links."""
        mock_response = {"links": []}
        mock_request.return_value = mock_response

        result = client.consult_concordance_links_article("LEGIARTI123")

        mock_request.assert_called_once_with('/consult/concordanceLinksArticle', {'id': 'LEGIARTI123'})
    
    @patch.object(LegifranceClient, '_make_request')
    def test_ping_endpoints(self, mock_request, client):
        """Test all ping endpoints."""
        mock_response = {"status": "ok"}
        mock_request.return_value = mock_response

        # Test consult ping
        client.consult_ping()
        assert any('/consult/ping' in str(call) for call in mock_request.call_args_list)
        
        # Test list ping
        client.list_ping()
        assert any('/list/ping' in str(call) for call in mock_request.call_args_list)
        
        # Test search ping
        client.search_ping()
        assert any('/search/ping' in str(call) for call in mock_request.call_args_list)
        
        # Test suggest ping
        client.suggest_ping()
        assert any('/suggest/ping' in str(call) for call in mock_request.call_args_list)
        
        # Test chrono ping
        client.chrono_ping()
        assert any('/chrono/ping' in str(call) for call in mock_request.call_args_list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
