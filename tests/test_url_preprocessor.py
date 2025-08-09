"""
Tests for URL Preprocessor
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from src.preprocess.preprocessor import URLPreprocessor


class TestURLPreprocessor:
    """Test cases for URLPreprocessor class"""
    
    def test_initialization(self):
        """Test URLPreprocessor initialization"""
        # Without API key
        preprocessor = URLPreprocessor()
        assert preprocessor.api_key is None
        
        # With API key
        preprocessor = URLPreprocessor(api_key="test_key")
        assert preprocessor.api_key == "test_key"
        assert preprocessor.base_url == "https://civitai.com/api/v1"
    
    def test_identify_url_type_download_url(self):
        """Test identifying download URLs"""
        preprocessor = URLPreprocessor()
        
        url = "https://civitai.com/api/download/models/12345"
        url_type, data = preprocessor.identify_url_type(url)
        
        assert url_type == "download_url"
        assert data["model_version_id"] == "12345"
    
    def test_identify_url_type_model_page(self):
        """Test identifying model page URLs"""
        preprocessor = URLPreprocessor()
        
        url = "https://civitai.com/models/67890"
        url_type, data = preprocessor.identify_url_type(url)
        
        assert url_type == "model_page"
        assert data["model_id"] == "67890"
    
    def test_identify_url_type_model_version_page(self):
        """Test identifying model version page URLs"""
        preprocessor = URLPreprocessor()
        
        url = "https://civitai.com/models/12345/test-model?modelVersionId=67890"
        url_type, data = preprocessor.identify_url_type(url)
        
        assert url_type == "model_version_page"
        assert data["model_id"] == "12345"
        assert data["model_version_id"] == "67890"
    
    def test_identify_url_type_model_id_only(self):
        """Test identifying model ID only"""
        preprocessor = URLPreprocessor()
        
        url = "12345"
        url_type, data = preprocessor.identify_url_type(url)
        
        assert url_type == "model_id_only"
        assert data["model_id"] == "12345"
    
    def test_identify_url_type_unknown(self):
        """Test identifying unknown URL type"""
        preprocessor = URLPreprocessor()
        
        url = "https://example.com/unknown"
        url_type, data = preprocessor.identify_url_type(url)
        
        assert url_type == "unknown"
        assert data == {"original_url": "https://example.com/unknown"}
    
    def test_extract_model_id_from_url(self):
        """Test extracting model ID from download URL"""
        preprocessor = URLPreprocessor()
        
        url = "https://civitai.com/api/download/models/12345"
        model_id = preprocessor.extract_model_id_from_url(url)
        
        assert model_id == "12345"
    
    def test_extract_model_id_from_url_invalid(self):
        """Test extracting model ID from invalid download URL"""
        preprocessor = URLPreprocessor()
        
        url = "https://example.com/invalid"
        model_id = preprocessor.extract_model_id_from_url(url)
        
        assert model_id is None
    
    @pytest.mark.asyncio
    async def test_resolve_url_download_url(self):
        """Test resolving URL that's already a download URL"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session_instance = AsyncMock()
            preprocessor = URLPreprocessor()
            
            url = "https://civitai.com/api/download/models/12345"
            success, result = await preprocessor.resolve_url(mock_session_instance, url, "Test Model")
            
            assert success is True
            assert result == url
    
    @pytest.mark.asyncio
    async def test_process_csv_file_basic(self, temp_dir):
        """Test processing CSV file with URLs"""
        # Create test CSV
        csv_content = """SrNo,Model_ID,Model_Name,Model_URL
1,12345,Test Model 1,https://civitai.com/api/download/models/12345
2,67890,Test Model 2,https://civitai.com/models/67890"""
        
        csv_path = temp_dir / "test.csv"
        with open(csv_path, 'w') as f:
            f.write(csv_content)
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            
            preprocessor = URLPreprocessor()
            total, success, failed = await preprocessor.process_csv_file(csv_path)
            
            assert total == 2
