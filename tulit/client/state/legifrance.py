import logging
import requests
from tulit.client.client import Client
import argparse
import sys
import os
import json
from typing import Optional, Dict, Any, List

class LegifranceClient(Client):
    """
    Client for interacting with the Legifrance API.
    
    The Legifrance API provides access to French legal documents including:
    - Codes
    - Laws and decrees (LODA)
    - Legislative dossiers
    - Official journals (JORF)
    - Collective agreements (KALI)
    - Administrative documents
    - Case law (JURI)
    - Parliamentary debates
    
    This client implements the main controllers:
    - Consult: retrieve specific documents
    - List: list documents with pagination
    - Search: search across documents
    - Suggest: autocomplete suggestions
    - Chrono: versioned content
    """
    
    def __init__(self, client_id, client_secret, download_dir='./data/france/legifrance', log_dir='./data/logs', proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://sandbox-api.piste.gouv.fr/dila/legifrance/lf-engine-app"
        self.oauth_url = "https://sandbox-oauth.piste.gouv.fr/api/oauth/token"
        self.logger = logging.getLogger(self.__class__.__name__)
        self._token = None
        self._token_expiry = None

    def get_token(self):
        """
        Obtain OAuth2 token from the Legifrance authentication service.
        
        Returns
        -------
        str
            Access token for API requests
        """
        payload = {
            'grant_type': 'client_credentials',            
            "scope": "openid",
            "client_id": self.client_id,
            "client_secret": self.client_secret,        
        }
        try:
            self.logger.info("Requesting OAuth token from Legifrance")
            response = requests.post(self.oauth_url, data=payload)
            response.raise_for_status()
            self._token = response.json()['access_token']
            self.logger.info("Successfully obtained OAuth token")
            return self._token
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"Failed to obtain OAuth token: {e}")
            self.logger.error(f"Response content: {e.response.text if hasattr(e, 'response') else 'N/A'}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to obtain OAuth token: {e}")
            raise

    def _make_request(self, endpoint: str, payload: Dict[str, Any], method: str = 'POST') -> Dict[str, Any]:
        """
        Make an authenticated request to the Legifrance API.
        
        Parameters
        ----------
        endpoint : str
            API endpoint (e.g., '/consult/code')
        payload : dict
            Request payload
        method : str, optional
            HTTP method (default: 'POST')
            
        Returns
        -------
        dict
            JSON response from the API
        """
        token = self.get_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        url = f"{self.base_url}{endpoint}"
        
        try:
            self.logger.info(f"Making {method} request to {endpoint}")
            if method == 'POST':
                response = requests.post(url, json=payload, headers=headers)
            elif method == 'GET':
                response = requests.get(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '')
            if 'json' not in content_type:
                self.logger.warning(f"Expected JSON response but got: {content_type}")
            
            return response.json()
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error on {endpoint}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to make request to {endpoint}: {e}")
            raise

    # ==================== CONSULT CONTROLLER ====================
    
    def consult_ping(self) -> Dict[str, Any]:
        """
        Test the consult controller.
        
        Returns
        -------
        dict
            Ping response
        """
        return self._make_request('/consult/ping', {}, method='GET')
    
    def consult_code(self, text_id: str, date: Optional[str] = None, 
                     searched_string: Optional[str] = None, sct_cid: Optional[str] = None,
                     abrogated: bool = False, from_suggest: bool = False) -> Dict[str, Any]:
        """
        Get the content of a Code.
        
        Parameters
        ----------
        text_id : str
            Text identifier (e.g., 'LEGITEXT000006070721' for Code Civil)
        date : str, optional
            Date for versioned content (format: YYYY-MM-DD)
        searched_string : str, optional
            Search string to highlight in the document
        sct_cid : str, optional
            Section CID to retrieve specific section
        abrogated : bool, optional
            Include abrogated versions (default: False)
        from_suggest : bool, optional
            Indicates if request comes from suggest (default: False)
            
        Returns
        -------
        dict
            Code content
        """
        payload = {
            "textId": text_id,
            "abrogated": abrogated,
            "fromSuggest": from_suggest
        }
        if date:
            payload["date"] = date
        if searched_string:
            payload["searchedString"] = searched_string
        if sct_cid:
            payload["sctCid"] = sct_cid
        return self._make_request('/consult/code', payload)
    
    def consult_law_decree(self, text_id: str, date: Optional[str] = None, 
                          searched_string: Optional[str] = None,
                          abrogated: bool = False, from_suggest: bool = False) -> Dict[str, Any]:
        """
        Get the content of a law or decree (LODA).
        
        Parameters
        ----------
        text_id : str
            Text identifier
        date : str, optional
            Date for versioned content (format: YYYY-MM-DD)
        searched_string : str, optional
            Search string to highlight in the document
        abrogated : bool, optional
            Include abrogated versions (default: False)
        from_suggest : bool, optional
            Indicates if request comes from suggest (default: False)
            
        Returns
        -------
        dict
            Law/decree content
        """
        payload = {
            "textId": text_id,
            "abrogated": abrogated,
            "fromSuggest": from_suggest
        }
        if date:
            payload["date"] = date
        if searched_string:
            payload["searchedString"] = searched_string
        return self._make_request('/consult/lawDecree', payload)
    
    def consult_article(self, article_id: str, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the content of an article.
        
        Parameters
        ----------
        article_id : str
            Article identifier
        date : str, optional
            Date for versioned content (format: YYYY-MM-DD)
            
        Returns
        -------
        dict
            Article content
        """
        payload = {"id": article_id}
        if date:
            payload["date"] = date
        return self._make_request('/consult/getArticle', payload)
    
    def consult_article_by_eli_or_alias(self, eli: str) -> Dict[str, Any]:
        """
        Get article content by ELI or alias.
        
        Parameters
        ----------
        eli : str
            European Legislation Identifier or alias
            
        Returns
        -------
        dict
            Article content
        """
        payload = {"eli": eli}
        return self._make_request('/consult/getArticleWithIdEliOrAlias', payload)
    
    def consult_dossier_legislatif(self, text_id: str) -> Dict[str, Any]:
        """
        Get the content of a legislative dossier.
        
        Parameters
        ----------
        text_id : str
            Legislative dossier identifier
            
        Returns
        -------
        dict
            Legislative dossier content
        """
        payload = {"textId": text_id}
        return self._make_request('/consult/dossierLegislatif', payload)
    
    def consult_jorf(self, text_id: str) -> Dict[str, Any]:
        """
        Get the content of a JORF (Journal Officiel) text.
        
        Parameters
        ----------
        text_id : str
            JORF text identifier
            
        Returns
        -------
        dict
            JORF text content
        """
        payload = {"textId": text_id}
        return self._make_request('/consult/jorf', payload)
    
    def consult_jorf_container(self, num: str, date: str) -> Dict[str, Any]:
        """
        Get the JORF table of contents.
        
        Parameters
        ----------
        num : str
            JORF number
        date : str
            Publication date (format: YYYY-MM-DD)
            
        Returns
        -------
        dict
            JORF table of contents
        """
        payload = {"num": num, "date": date}
        return self._make_request('/consult/jorfCont', payload)
    
    def consult_table_matieres(self, text_id: str, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the table of contents for a LODA or CODE text.
        
        Parameters
        ----------
        text_id : str
            Text identifier
        date : str, optional
            Date for versioned content (format: YYYY-MM-DD)
            
        Returns
        -------
        dict
            Table of contents
        """
        payload = {"textId": text_id}
        if date:
            payload["date"] = date
        return self._make_request('/consult/legi/tableMatieres', payload)
    
    def consult_kali_text(self, cid: str) -> Dict[str, Any]:
        """
        Get collective agreement content.
        
        Parameters
        ----------
        cid : str
            Collective agreement identifier
            
        Returns
        -------
        dict
            Collective agreement content
        """
        payload = {"cid": cid}
        return self._make_request('/consult/kaliText', payload)
    
    def consult_juri(self, text_id: str) -> Dict[str, Any]:
        """
        Get case law (JURI) content.
        
        Parameters
        ----------
        text_id : str
            Case law identifier
            
        Returns
        -------
        dict
            Case law content
        """
        payload = {"textId": text_id}
        return self._make_request('/consult/juri', payload)
    
    def consult_circulaire(self, text_id: str) -> Dict[str, Any]:
        """
        Get circular content.
        
        Parameters
        ----------
        text_id : str
            Circular identifier
            
        Returns
        -------
        dict
            Circular content
        """
        payload = {"textId": text_id}
        return self._make_request('/consult/circulaire', payload)
    
    def consult_debat(self, text_id: str) -> Dict[str, Any]:
        """
        Get parliamentary debate content.
        
        Parameters
        ----------
        text_id : str
            Debate identifier
            
        Returns
        -------
        dict
            Debate content
        """
        payload = {"textId": text_id}
        return self._make_request('/consult/debat', payload)
    
    # Additional Consult Methods
    
    def consult_acco(self, text_id: str) -> Dict[str, Any]:
        """
        Get company agreement content.
        
        Parameters
        ----------
        text_id : str
            Company agreement identifier
            
        Returns
        -------
        dict
            Company agreement content
        """
        payload = {"textId": text_id}
        return self._make_request('/consult/acco', payload)
    
    def consult_cnil(self, text_id: str) -> Dict[str, Any]:
        """
        Get CNIL text content.
        
        Parameters
        ----------
        text_id : str
            CNIL text identifier
            
        Returns
        -------
        dict
            CNIL text content
        """
        payload = {"textId": text_id}
        return self._make_request('/consult/cnil', payload)
    
    def consult_legi_part(self, text_id: str, searched_string: Optional[str] = None, 
                         date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get partial LEGI text content (used for text fragment retrieval).
        
        Parameters
        ----------
        text_id : str
            Text identifier
        searched_string : str, optional
            Search string within the text
        date : str, optional
            Date for versioned content (format: YYYY-MM-DD)
            
        Returns
        -------
        dict
            Partial text content
        """
        payload = {"textId": text_id}
        if searched_string:
            payload["searchedString"] = searched_string
        if date:
            payload["date"] = date
        return self._make_request('/consult/legiPart', payload)
    
    def consult_jorf_part(self, text_id: str) -> Dict[str, Any]:
        """
        Get partial JORF text content.
        
        Parameters
        ----------
        text_id : str
            JORF text identifier
            
        Returns
        -------
        dict
            Partial JORF content
        """
        payload = {"textId": text_id}
        return self._make_request('/consult/jorfPart', payload)
    
    def consult_article_by_cid(self, cid: str) -> Dict[str, Any]:
        """
        Get article versions by CID.
        
        Parameters
        ----------
        cid : str
            Article CID (Container ID)
            
        Returns
        -------
        dict
            Article versions
        """
        payload = {"cid": cid}
        return self._make_request('/consult/getArticleByCid', payload)
    
    def consult_article_with_id_and_num(self, article_id: str, article_num: str,
                                        date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get article by ID and number.
        
        Parameters
        ----------
        article_id : str
            Article identifier
        article_num : str
            Article number
        date : str, optional
            Date for versioned content (format: YYYY-MM-DD)
            
        Returns
        -------
        dict
            Article content
        """
        payload = {"id": article_id, "articleNum": article_num}
        if date:
            payload["date"] = date
        return self._make_request('/consult/getArticleWithIdAndNum', payload)
    
    def consult_section_by_cid(self, cid: str, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get section content by CID.
        
        Parameters
        ----------
        cid : str
            Section CID
        date : str, optional
            Date for versioned content (format: YYYY-MM-DD)
            
        Returns
        -------
        dict
            Section content
        """
        payload = {"cid": cid}
        if date:
            payload["date"] = date
        return self._make_request('/consult/getSectionByCid', payload)
    
    def consult_tables(self, start_year: int, end_year: int) -> Dict[str, Any]:
        """
        Get annual tables list for a period.
        
        Parameters
        ----------
        start_year : int
            Start year
        end_year : int
            End year
            
        Returns
        -------
        dict
            Annual tables
        """
        payload = {"startYear": start_year, "endYear": end_year}
        return self._make_request('/consult/getTables', payload)
    
    def consult_kali_article(self, cid: str, article_num: str) -> Dict[str, Any]:
        """
        Get collective agreement content from article.
        
        Parameters
        ----------
        cid : str
            Container ID
        article_num : str
            Article number
            
        Returns
        -------
        dict
            Collective agreement article content
        """
        payload = {"cid": cid, "articleNum": article_num}
        return self._make_request('/consult/kaliArticle', payload)
    
    def consult_kali_section(self, cid: str, section_id: str) -> Dict[str, Any]:
        """
        Get collective agreement content from section.
        
        Parameters
        ----------
        cid : str
            Container ID
        section_id : str
            Section identifier
            
        Returns
        -------
        dict
            Collective agreement section content
        """
        payload = {"cid": cid, "sectionId": section_id}
        return self._make_request('/consult/kaliSection', payload)
    
    def consult_kali_cont(self, idcc: str) -> Dict[str, Any]:
        """
        Get collective agreement containers.
        
        Parameters
        ----------
        idcc : str
            IDCC (Identifiant de Convention Collective)
            
        Returns
        -------
        dict
            Collective agreement containers
        """
        payload = {"idcc": idcc}
        return self._make_request('/consult/kaliCont', payload)
    
    def consult_kali_cont_idcc(self, idcc: str) -> Dict[str, Any]:
        """
        Get collective agreement containers by IDCC.
        
        Parameters
        ----------
        idcc : str
            IDCC identifier
            
        Returns
        -------
        dict
            Collective agreement containers
        """
        payload = {"idcc": idcc}
        return self._make_request('/consult/kaliContIdcc', payload)
    
    def consult_code_with_ancien_id(self, ancien_id: str) -> Dict[str, Any]:
        """
        Get code by ancien ID (legacy identifier).
        
        Parameters
        ----------
        ancien_id : str
            Legacy code identifier
            
        Returns
        -------
        dict
            Code content
        """
        payload = {"ancienId": ancien_id}
        return self._make_request('/consult/getCodeWithAncienId', payload)
    
    def consult_cnil_with_ancien_id(self, ancien_id: str) -> Dict[str, Any]:
        """
        Get CNIL text by ancien ID.
        
        Parameters
        ----------
        ancien_id : str
            Legacy CNIL text identifier
            
        Returns
        -------
        dict
            CNIL text content
        """
        payload = {"ancienId": ancien_id}
        return self._make_request('/consult/getCnilWithAncienId', payload)
    
    def consult_juri_with_ancien_id(self, ancien_id: str) -> Dict[str, Any]:
        """
        Get case law by ancien ID.
        
        Parameters
        ----------
        ancien_id : str
            Legacy case law identifier
            
        Returns
        -------
        dict
            Case law content
        """
        payload = {"ancienId": ancien_id}
        return self._make_request('/consult/getJuriWithAncienId', payload)
    
    def consult_jo_with_nor(self, nor: str) -> Dict[str, Any]:
        """
        Get Official Journal by NOR.
        
        Parameters
        ----------
        nor : str
            NOR (Numéro d'Ordre) identifier
            
        Returns
        -------
        dict
            Official Journal content
        """
        payload = {"nor": nor}
        return self._make_request('/consult/getJoWithNor', payload)
    
    def consult_last_n_jo(self, n: int = 10) -> Dict[str, Any]:
        """
        Get last N Official Journals.
        
        Parameters
        ----------
        n : int, optional
            Number of journals to retrieve (default: 10)
            
        Returns
        -------
        dict
            List of last N Official Journals
        """
        payload = {"n": n}
        return self._make_request('/consult/lastNJo', payload)
    
    def consult_juri_plan_classement(self, text_id: str) -> Dict[str, Any]:
        """
        Get case law classification plan.
        
        Parameters
        ----------
        text_id : str
            Case law text identifier
            
        Returns
        -------
        dict
            Classification plan
        """
        payload = {"textId": text_id}
        return self._make_request('/consult/getJuriPlanClassement', payload)
    
    def consult_eli_alias_redirection(self, eli: str) -> Dict[str, Any]:
        """
        Get Official Journal texts by ELI or alias.
        
        Parameters
        ----------
        eli : str
            European Legislation Identifier or alias
            
        Returns
        -------
        dict
            Official Journal text content
        """
        payload = {"eli": eli}
        return self._make_request('/consult/eliAndAliasRedirectionTexte', payload)
    
    def consult_bocc_text_pdf_metadata(self, text_id: str) -> Dict[str, Any]:
        """
        Get PDF metadata for BOCC unit text.
        
        Parameters
        ----------
        text_id : str
            BOCC text identifier
            
        Returns
        -------
        dict
            PDF metadata
        """
        payload = {"textId": text_id}
        return self._make_request('/consult/getBoccTextPdfMetadata', payload)
    
    # Article Links Methods
    
    def consult_same_num_article(self, article_id: str) -> Dict[str, Any]:
        """
        Get list of articles with the same number.
        
        Parameters
        ----------
        article_id : str
            Article identifier
            
        Returns
        -------
        dict
            List of articles with same number
        """
        payload = {"id": article_id}
        return self._make_request('/consult/sameNumArticle', payload)
    
    def consult_concordance_links_article(self, article_id: str) -> Dict[str, Any]:
        """
        Get concordance links for an article.
        
        Parameters
        ----------
        article_id : str
            Article identifier
            
        Returns
        -------
        dict
            Concordance links
        """
        payload = {"id": article_id}
        return self._make_request('/consult/concordanceLinksArticle', payload)
    
    def consult_related_links_article(self, article_id: str) -> Dict[str, Any]:
        """
        Get related links for an article.
        
        Parameters
        ----------
        article_id : str
            Article identifier
            
        Returns
        -------
        dict
            Related links
        """
        payload = {"id": article_id}
        return self._make_request('/consult/relatedLinksArticle', payload)
    
    def consult_service_public_links_article(self, article_id: str) -> Dict[str, Any]:
        """
        Get public service links for an article.
        
        Parameters
        ----------
        article_id : str
            Article identifier
            
        Returns
        -------
        dict
            Public service links
        """
        payload = {"id": article_id}
        return self._make_request('/consult/servicePublicLinksArticle', payload)
    
    def consult_has_service_public_links_article(self, text_id: str) -> Dict[str, Any]:
        """
        Check which articles have public service links.
        
        Parameters
        ----------
        text_id : str
            Text identifier
            
        Returns
        -------
        dict
            List of articles with public service links
        """
        payload = {"textId": text_id}
        return self._make_request('/consult/hasServicePublicLinksArticle', payload)

    # ==================== LIST CONTROLLER ====================
    
    def list_codes(self, page_number: int = 1, page_size: int = 100, 
                   date: Optional[str] = None) -> Dict[str, Any]:
        """
        List codes with pagination.
        
        Parameters
        ----------
        page_number : int
            Page number (default: 1)
        page_size : int
            Items per page (default: 100)
        date : str, optional
            Filter by date (format: YYYY-MM-DD)
            
        Returns
        -------
        dict
            Paginated list of codes
        """
        payload = {
            "pageNumber": page_number,
            "pageSize": page_size
        }
        if date:
            payload["date"] = date
        return self._make_request('/list/code', payload)
    
    def list_loda(self, page_number: int = 1, page_size: int = 100,
                  date: Optional[str] = None) -> Dict[str, Any]:
        """
        List laws and decrees (LODA) with pagination.
        
        Parameters
        ----------
        page_number : int
            Page number (default: 1)
        page_size : int
            Items per page (default: 100)
        date : str, optional
            Filter by date (format: YYYY-MM-DD)
            
        Returns
        -------
        dict
            Paginated list of LODA texts
        """
        payload = {
            "pageNumber": page_number,
            "pageSize": page_size
        }
        if date:
            payload["date"] = date
        return self._make_request('/list/loda', payload)
    
    def list_dossiers_legislatifs(self, page_number: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """
        List legislative dossiers with pagination.
        
        Parameters
        ----------
        page_number : int
            Page number (default: 1)
        page_size : int
            Items per page (default: 100)
            
        Returns
        -------
        dict
            Paginated list of legislative dossiers
        """
        payload = {
            "pageNumber": page_number,
            "pageSize": page_size
        }
        return self._make_request('/list/dossiersLegislatifs', payload)
    
    def list_conventions(self, page_number: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """
        List collective agreements with pagination.
        
        Parameters
        ----------
        page_number : int
            Page number (default: 1)
        page_size : int
            Items per page (default: 100)
            
        Returns
        -------
        dict
            Paginated list of conventions
        """
        payload = {
            "pageNumber": page_number,
            "pageSize": page_size
        }
        return self._make_request('/list/conventions', payload)
    
    def list_bocc(self, page_number: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """
        List bulletins officiels des conventions collectives (BOCC).
        
        Parameters
        ----------
        page_number : int
            Page number (default: 1)
        page_size : int
            Items per page (default: 100)
            
        Returns
        -------
        dict
            Paginated list of BOCC
        """
        payload = {
            "pageNumber": page_number,
            "pageSize": page_size
        }
        return self._make_request('/list/bocc', payload)
    
    def list_debats_parlementaires(self, legislature: Optional[str] = None,
                                    page_number: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """
        List parliamentary debates.
        
        Parameters
        ----------
        legislature : str, optional
            Legislature identifier
        page_number : int
            Page number (default: 1)
        page_size : int
            Items per page (default: 100)
            
        Returns
        -------
        dict
            List of parliamentary debates
        """
        payload = {
            "pageNumber": page_number,
            "pageSize": page_size
        }
        if legislature:
            payload["legislature"] = legislature
        return self._make_request('/list/debatsParlementaires', payload)
    
    # Additional List Methods
    
    def list_ping(self) -> Dict[str, Any]:
        """
        Test the list controller.
        
        Returns
        -------
        dict
            Ping response
        """
        return self._make_request('/list/ping', {}, method='GET')
    
    def list_docs_admins(self, start_year: int, end_year: int,
                        page_number: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """
        List administrative documents for a period.
        
        Parameters
        ----------
        start_year : int
            Start year
        end_year : int
            End year
        page_number : int
            Page number (default: 1)
        page_size : int
            Items per page (default: 100)
            
        Returns
        -------
        dict
            Paginated list of administrative documents
        """
        payload = {
            "startYear": start_year,
            "endYear": end_year,
            "pageNumber": page_number,
            "pageSize": page_size
        }
        return self._make_request('/list/docsAdmins', payload)
    
    def list_bodmr(self, start_year: int, end_year: int,
                   page_number: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """
        List bulletins officiels des décorations, médailles et récompenses.
        
        Parameters
        ----------
        start_year : int
            Start year
        end_year : int
            End year
        page_number : int
            Page number (default: 1)
        page_size : int
            Items per page (default: 100)
            
        Returns
        -------
        dict
            Paginated list of BODMR bulletins
        """
        payload = {
            "startYear": start_year,
            "endYear": end_year,
            "pageNumber": page_number,
            "pageSize": page_size
        }
        return self._make_request('/list/bodmr', payload)
    
    def list_questions_ecrites_parlementaires(self, page_number: int = 1, 
                                              page_size: int = 100,
                                              filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        List parliamentary written questions with pagination.
        
        Parameters
        ----------
        page_number : int
            Page number (default: 1)
        page_size : int
            Items per page (default: 100)
        filters : dict, optional
            Additional filters (legislature, author, etc.)
            
        Returns
        -------
        dict
            Paginated list of parliamentary written questions
        """
        payload = {
            "pageNumber": page_number,
            "pageSize": page_size
        }
        if filters:
            payload.update(filters)
        return self._make_request('/list/questionsEcritesParlementaires', payload)
    
    def list_legislatures(self) -> Dict[str, Any]:
        """
        List legislatures.
        
        Returns
        -------
        dict
            List of legislatures
        """
        return self._make_request('/list/legislatures', {})
    
    def list_bocc_texts(self, page_number: int = 1, page_size: int = 100,
                       filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        List BOCC unit texts with pagination.
        
        Parameters
        ----------
        page_number : int
            Page number (default: 1)
        page_size : int
            Items per page (default: 100)
        filters : dict, optional
            Additional filters
            
        Returns
        -------
        dict
            Paginated list of BOCC texts
        """
        payload = {
            "pageNumber": page_number,
            "pageSize": page_size
        }
        if filters:
            payload.update(filters)
        return self._make_request('/list/boccTexts', payload)
    
    def list_boccs_and_texts(self, page_number: int = 1, page_size: int = 100,
                            filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        List BOCCs and their texts with pagination.
        
        Parameters
        ----------
        page_number : int
            Page number (default: 1)
        page_size : int
            Items per page (default: 100)
        filters : dict, optional
            Additional filters
            
        Returns
        -------
        dict
            Paginated list of BOCCs and texts
        """
        payload = {
            "pageNumber": page_number,
            "pageSize": page_size
        }
        if filters:
            payload.update(filters)
        return self._make_request('/list/boccsAndTexts', payload)

    # ==================== SEARCH CONTROLLER ====================
    
    def search(self, search_query: str, page_number: int = 1, page_size: int = 10,
               filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generic search across indexed documents.
        
        Parameters
        ----------
        search_query : str
            Search query
        page_number : int
            Page number (default: 1)
        page_size : int
            Items per page (default: 10)
        filters : dict, optional
            Additional filters (e.g., date ranges, document types)
            
        Returns
        -------
        dict
            Search results
        """
        payload = {
            "search": search_query,
            "pageNumber": page_number,
            "pageSize": page_size
        }
        if filters:
            payload.update(filters)
        return self._make_request('/search', payload)
    
    def search_ping(self) -> Dict[str, Any]:
        """
        Test the search controller.
        
        Returns
        -------
        dict
            Ping response
        """
        return self._make_request('/search/ping', {}, method='GET')
    
    def search_canonical_version(self, text_id: str, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get canonical version info for a text.
        
        Parameters
        ----------
        text_id : str
            Text identifier
        date : str, optional
            Date for version lookup (format: YYYY-MM-DD)
            
        Returns
        -------
        dict
            Canonical version information
        """
        payload = {"textId": text_id}
        if date:
            payload["date"] = date
        return self._make_request('/search/canonicalVersion', payload)
    
    def search_canonical_article_version(self, article_id: str, 
                                         date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get canonical article versions.
        
        Parameters
        ----------
        article_id : str
            Article identifier
        date : str, optional
            Date for version lookup (format: YYYY-MM-DD)
            
        Returns
        -------
        dict
            Canonical article versions
        """
        payload = {"id": article_id}
        if date:
            payload["date"] = date
        return self._make_request('/search/canonicalArticleVersion', payload)
    
    def search_nearest_version(self, text_id: str, date: str) -> Dict[str, Any]:
        """
        Get nearest version info for a text at a given date.
        
        Parameters
        ----------
        text_id : str
            Text identifier
        date : str
            Target date (format: YYYY-MM-DD)
            
        Returns
        -------
        dict
            Nearest version information
        """
        payload = {"textId": text_id, "date": date}
        return self._make_request('/search/nearestVersion', payload)

    # ==================== SUGGEST CONTROLLER ====================
    
    def suggest(self, query: str, type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get autocomplete suggestions.
        
        Parameters
        ----------
        query : str
            Search query
        type : str, optional
            Suggestion type filter
            
        Returns
        -------
        dict
            Suggestions
        """
        payload = {"query": query}
        if type:
            payload["type"] = type
        return self._make_request('/suggest', payload)
    
    def suggest_ping(self) -> Dict[str, Any]:
        """
        Test the suggest controller.
        
        Returns
        -------
        dict
            Ping response
        """
        return self._make_request('/suggest/ping', {}, method='GET')
    
    def suggest_acco(self, query: str) -> Dict[str, Any]:
        """
        Get SIRET and company name suggestions for agreements.
        
        Parameters
        ----------
        query : str
            Search query
            
        Returns
        -------
        dict
            SIRET and company name suggestions
        """
        payload = {"query": query}
        return self._make_request('/suggest/acco', payload)
    
    def suggest_pdc(self, query: str) -> Dict[str, Any]:
        """
        Get classification plan label suggestions.
        
        Parameters
        ----------
        query : str
            Search query
            
        Returns
        -------
        dict
            Classification plan suggestions
        """
        payload = {"query": query}
        return self._make_request('/suggest/pdc', payload)
    
    # ==================== CHRONO CONTROLLER ====================
    
    def chrono_ping(self) -> Dict[str, Any]:
        """
        Test the chrono controller.
        
        Returns
        -------
        dict
            Ping response
        """
        return self._make_request('/chrono/ping', {}, method='GET')
    
    def chrono_text_has_versions(self, text_cid: str) -> Dict[str, Any]:
        """
        Check if a text has versions.
        
        Parameters
        ----------
        text_cid : str
            Text CID
            
        Returns
        -------
        dict
            Version existence info
        """
        endpoint = f'/chrono/textCid/{text_cid}'
        return self._make_request(endpoint, {}, method='GET')
    
    def chrono_text_version(self, text_cid: str, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get text version.
        
        Parameters
        ----------
        text_cid : str
            Text CID
        date : str, optional
            Date for specific version (format: YYYY-MM-DD)
            
        Returns
        -------
        dict
            Text version
        """
        payload = {"textCid": text_cid}
        if date:
            payload["date"] = date
        return self._make_request('/chrono/textCid', payload)
    
    def chrono_text_and_element(self, text_cid: str, element_cid: str,
                                date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get extract from a text version.
        
        Parameters
        ----------
        text_cid : str
            Text CID
        element_cid : str
            Element CID
        date : str, optional
            Date for version (format: YYYY-MM-DD)
            
        Returns
        -------
        dict
            Text and element extract
        """
        payload = {"textCid": text_cid, "elementCid": element_cid}
        if date:
            payload["date"] = date
        return self._make_request('/chrono/textCidAndElementCid', payload)
    
    # ==================== MISC CONTROLLER ====================
    
    def misc_commit_id(self) -> Dict[str, Any]:
        """
        Get deployment and versioning information.
        
        Returns
        -------
        dict
            Deployment/version info
        """
        return self._make_request('/misc/commitId', {}, method='GET')
    
    def misc_dates_without_jo(self) -> Dict[str, Any]:
        """
        Get list of dates without Official Journal.
        
        Returns
        -------
        dict
            List of dates without JO
        """
        return self._make_request('/misc/datesWithoutJo', {}, method='GET')
    
    def misc_years_without_table(self) -> Dict[str, Any]:
        """
        Get list of years without tables.
        
        Returns
        -------
        dict
            List of years without tables
        """
        return self._make_request('/misc/yearsWithoutTable', {}, method='GET')

    # ==================== DOWNLOAD METHODS ====================
    
    def download(self, endpoint: str, payload: Dict[str, Any], filename: str) -> str:
        """
        Download document and save to file.
        
        Parameters
        ----------
        endpoint : str
            API endpoint
        payload : dict
            Request payload
        filename : str
            Output filename
            
        Returns
        -------
        str
            Path to saved file
        """
        try:
            result = self._make_request(endpoint, payload)
            
            # Save as JSON
            filepath = os.path.join(self.download_dir, f"{filename}.json")
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Document saved to: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Failed to download document: {e}")
            raise
    
    def download_code(self, text_id: str, date: Optional[str] = None,
                     searched_string: Optional[str] = None, sct_cid: Optional[str] = None,
                     abrogated: bool = True, from_suggest: bool = True,
                     enrich_articles: bool = False) -> str:
        """
        Download a code and save to file.
        
        Parameters
        ----------
        text_id : str
            Code identifier
        date : str, optional
            Date for versioned content
        searched_string : str, optional
            Search string to highlight
        sct_cid : str, optional
            Section CID
        abrogated : bool, optional
            Include abrogated versions (default: True for sandbox compatibility)
        from_suggest : bool, optional
            From suggest (default: True for sandbox compatibility)
        enrich_articles : bool, optional
            Fetch full article content for each article (default: False)
            Warning: Makes one API call per article, can be slow for large codes
            
        Returns
        -------
        str
            Path to saved file
        """
        result = self.consult_code(text_id, date, searched_string, sct_cid, abrogated, from_suggest)
        
        # Enrich articles with full content if requested
        if enrich_articles:
            self.logger.info("Enriching articles with full content...")
            result = self._enrich_articles_recursive(result, date)
        
        # Save as JSON
        filename = f"code_{text_id}_{date if date else 'current'}"
        filepath = os.path.join(self.download_dir, f"{filename}.json")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Code saved to: {filepath}")
        return filepath
    
    def _enrich_articles_recursive(self, obj: Dict[str, Any], date: Optional[str] = None) -> Dict[str, Any]:
        """
        Recursively enrich all articles in a structure with full content.
        
        Parameters
        ----------
        obj : dict
            Object containing articles (code, section, etc.)
        date : str, optional
            Date for article version
            
        Returns
        -------
        dict
            Object with enriched articles
        """
        if 'articles' in obj and isinstance(obj['articles'], list):
            enriched_articles = []
            for article in obj['articles']:
                article_id = article.get('id')
                if article_id:
                    try:
                        # Get full article content
                        article_detail = self.consult_article(article_id, date)
                        # The response has the article nested under 'article' key
                        if 'article' in article_detail:
                            full_article = article_detail['article']
                            # Merge with existing article data, preferring full content
                            article.update(full_article)
                        self.logger.debug(f"Enriched article {article_id}")
                    except Exception as e:
                        self.logger.warning(f"Failed to enrich article {article_id}: {e}")
                enriched_articles.append(article)
            obj['articles'] = enriched_articles
        
        # Recurse into sections
        if 'sections' in obj and isinstance(obj['sections'], list):
            for section in obj['sections']:
                self._enrich_articles_recursive(section, date)
        
        return obj
    
    def download_law_decree(self, text_id: str, date: Optional[str] = None, searched_string: Optional[str] = None) -> str:
        """
        Download a law or decree (LODA) and save to file.
        
        Parameters
        ----------
        text_id : str
            Text identifier (LEGITEXT...)
        date : str, optional
            Date for versioned content (format: YYYY-MM-DD)
        searched_string : str, optional
            Search string to highlight in the document
            
        Returns
        -------
        str
            Path to saved file
        """
        payload = {"textId": text_id}
        if date:
            payload["date"] = date
        if searched_string:
            payload["searchedString"] = searched_string
        filename = f"loda_{text_id}_{date if date else 'current'}"
        return self.download('/consult/lawDecree', payload, filename)
    
    def download_dossier_legislatif(self, text_id: str) -> str:
        """
        Download a legislative dossier and save to file.
        
        Parameters
        ----------
        text_id : str
            Dossier identifier
            
        Returns
        -------
        str
            Path to saved file
        """
        payload = {"textId": text_id}
        filename = f"dossier_{text_id}"
        return self.download('/consult/dossierLegislatif', payload, filename)
