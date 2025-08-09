"""
Tests for CivitAI API Client
"""

import pytest
import asyncio
import aiohttp
from unittest.mock import AsyncMock, patch, MagicMock

from src.api.client import CivitAIApiClient


class TestCivitAIApiClient:
    """Test cases for CivitAIApiClient class"""
    
    def test_client_initialization(self):
        """Test client initialization with and without API key"""
        # Without API key
        client = CivitAIApiClient()
        assert client.api_key is None
        assert client.session is None
        
        # With API key
        client = CivitAIApiClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert client.session is None
    
    @pytest.mark.asyncio
    async def test_context_manager_entry_with_api_key(self):
        """Test context manager entry with API key"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value = mock_session_instance
            
            client = CivitAIApiClient(api_key="test_key")
            async with client:
                assert client.session is not None
                
                # Check that session was created with correct headers
                mock_session.assert_called_once()
                call_args = mock_session.call_args
                headers = call_args[1]['headers']
                assert headers["Authorization"] == "Bearer test_key"
                assert headers["Content-Type"] == "application/json"
    
    @pytest.mark.asyncio
    async def test_context_manager_entry_without_api_key(self):
        """Test context manager entry without API key"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value = mock_session_instance
            
            client = CivitAIApiClient()
            async with client:
                assert client.session is not None
                
                # Check that session was created without Authorization header
                call_args = mock_session.call_args
                headers = call_args[1]['headers']
                assert "Authorization" not in headers
                assert headers["Content-Type"] == "application/json"
    
    @pytest.mark.asyncio
    async def test_context_manager_exit(self):
        """Test context manager exit"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value = mock_session_instance
            
            client = CivitAIApiClient()
            async with client:
                pass
            
            # Should close session on exit
            mock_session_instance.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_make_request_success(self, sample_api_responses):
        """Test successful API request"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=sample_api_responses["model_info"])
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        # Make get() return the response directly (not as a coroutine)
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.close = AsyncMock()

        client = CivitAIApiClient(api_key="test_key")
        client.session = mock_session  # Direct assignment
        result = await client._make_request("models/12345")
        assert result == sample_api_responses["model_info"]
    
    @pytest.mark.asyncio
    async def test_make_request_http_error(self):
        """Test API request with HTTP error"""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="Not Found")
        mock_response.request_info = AsyncMock()
        mock_response.history = AsyncMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        # Make get() return the response directly (not as a coroutine)
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.close = AsyncMock()

        client = CivitAIApiClient(api_key="test_key")
        client.session = mock_session  # Direct assignment
        with pytest.raises(aiohttp.ClientResponseError):
            await client._make_request("models/nonexistent")

    @pytest.mark.asyncio
    async def test_make_request_timeout(self):
        """Test API request timeout"""
        mock_session = AsyncMock()
        # Make get() raise TimeoutError directly
        mock_session.get = MagicMock(side_effect=asyncio.TimeoutError())
        mock_session.close = AsyncMock()

        client = CivitAIApiClient(api_key="test_key")
        client.session = mock_session  # Direct assignment
        with pytest.raises(asyncio.TimeoutError):
            await client._make_request("models/12345")
    
    @pytest.mark.asyncio
    async def test_make_request_without_session(self):
        """Test making request without initialized session"""
        client = CivitAIApiClient()
        
        with pytest.raises(RuntimeError, match="API client not initialized"):
            await client._make_request("models/12345")
    
    @pytest.mark.asyncio
    async def test_get_model_by_id(self, sample_api_responses):
        """Test getting model information by ID"""
        with patch.object(CivitAIApiClient, '_make_request') as mock_request:
            mock_request.return_value = sample_api_responses["model_info"]
            
            client = CivitAIApiClient()
            client.session = AsyncMock()  # Mock session to avoid context manager
            
            result = await client.get_model_by_id(12345)
            
            assert result == sample_api_responses["model_info"]
            mock_request.assert_called_once_with("models/12345")
    
    @pytest.mark.asyncio
    async def test_get_model_version(self, sample_api_responses):
        """Test getting model version information"""
        with patch.object(CivitAIApiClient, '_make_request') as mock_request:
            mock_request.return_value = sample_api_responses["model_version_info"]
            
            client = CivitAIApiClient()
            client.session = AsyncMock()  # Mock session to avoid context manager
            
            result = await client.get_model_version(67890)
            
            assert result == sample_api_responses["model_version_info"]
            mock_request.assert_called_once_with("model-versions/67890")
    
    @pytest.mark.asyncio
    async def test_search_models_by_name(self):
        """Test searching for models by name"""
        search_results = {
            "items": [
                {"id": 1, "name": "Test Model 1"},
                {"id": 2, "name": "Test Model 2"}
            ],
            "metadata": {"totalItems": 2}
        }
        
        with patch.object(CivitAIApiClient, '_make_request') as mock_request:
            mock_request.return_value = search_results
            
            client = CivitAIApiClient()
            client.session = AsyncMock()
            
            result = await client.search_models_by_name("test")
            
            assert result == search_results["items"]
            mock_request.assert_called_once_with(
                "models", 
                {"query": "test", "limit": 10}
            )
    
    @pytest.mark.asyncio
    async def test_extract_download_url(self, sample_api_responses):
        """Test extracting download URL from model data"""
        client = CivitAIApiClient()
        
        download_url = client.extract_download_url(sample_api_responses["model_info"])
        
        expected_url = "https://civitai.com/api/download/models/67890"
        assert download_url == expected_url
    
    @pytest.mark.asyncio
    async def test_extract_download_url_no_files(self):
        """Test extracting download URL when no files are available"""
        model_data = {
            "id": 12345,
            "modelVersions": [
                {
                    "id": 67890,
                    "files": []
                }
            ]
        }
        
        client = CivitAIApiClient()
        download_url = client.extract_download_url(model_data)
        
        assert download_url is None
    
    @pytest.mark.asyncio
    async def test_find_download_url_by_id(self, sample_api_responses):
        """Test finding download URL using model ID"""
        with patch.object(CivitAIApiClient, 'get_model_by_id') as mock_get_model:
            mock_get_model.return_value = sample_api_responses["model_info"]
            
            client = CivitAIApiClient()
            
            download_url = await client.find_download_url("Test Model", "12345")
            
            expected_url = "https://civitai.com/api/download/models/67890"
            assert download_url == expected_url
            mock_get_model.assert_called_once_with(12345)
    
    @pytest.mark.asyncio
    async def test_find_download_url_by_name(self, sample_api_responses):
        """Test finding download URL by searching name"""
        with patch.object(CivitAIApiClient, 'search_models_by_name') as mock_search:
            mock_search.return_value = [sample_api_responses["model_info"]]
            
            client = CivitAIApiClient()
            
            download_url = await client.find_download_url("Test Model")
            
            expected_url = "https://civitai.com/api/download/models/67890"
            assert download_url == expected_url
            mock_search.assert_called_once_with("Test Model", None)
