"""
Integration tests for the CivitAI Model Downloader
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

from src.config.manager import ConfigManager
from src.api.client import CivitAIApiClient
from src.downloader.file_downloader import FileDownloader, ProgressManager
from src.utils.model_manager import ModelManager
from src.preprocess.preprocessor import URLPreprocessor


class TestIntegration:
    """Integration tests for the complete download workflow"""
    
    @pytest.mark.asyncio
    async def test_basic_download_workflow(self, temp_dir, sample_config_data):
        """Test basic download workflow components"""
        # Setup configuration
        config_path = temp_dir / "config.json"
        with open(config_path, 'w') as f:
            import json
            json.dump(sample_config_data, f)
        
        config_manager = ConfigManager(config_path)
        
        # Setup CSV file
        csv_dir = temp_dir / "CSVs"
        csv_dir.mkdir()
        csv_content = """SrNo,Model_ID,Model_Name,Model_URL
1,12345,Test Model 1,https://civitai.com/api/download/models/12345"""
        
        csv_path = csv_dir / "checkpoint.csv"
        with open(csv_path, 'w') as f:
            f.write(csv_content)
        
        # Test model manager workflow
        with patch.object(Path, 'cwd', return_value=temp_dir):
            model_manager = ModelManager(config_manager)
            download_tasks = model_manager.prepare_download_tasks("checkpoint", temp_dir)
            
            # Verify tasks are prepared correctly
            assert len(download_tasks) == 1
            assert download_tasks[0][0] == "https://civitai.com/api/download/models/12345"
            
            # Test that FileDownloader can be created
            downloader = FileDownloader(
                api_key=config_manager.get_api_key(),
                download_settings=config_manager.get_download_settings()
            )
            
            assert downloader.api_key == "test_api_key_123"
    
    @pytest.mark.asyncio
    async def test_url_preprocessing_integration(self, temp_dir):
        """Test URL preprocessing basic functionality"""
        # Create test CSV with various URL types
        csv_content = """SrNo,Model_ID,Model_Name,Model_URL
1,12345,Test Model 1,https://civitai.com/models/12345
2,67890,Test Model 2,https://civitai.com/api/download/models/67890"""
        
        csv_path = temp_dir / "test.csv"
        with open(csv_path, 'w') as f:
            f.write(csv_content)
        
        # Create preprocessor and test basic functionality
        preprocessor = URLPreprocessor(api_key="test_key")
        
        # Test URL identification
        url_type, data = preprocessor.identify_url_type("https://civitai.com/models/12345")
        assert url_type == "model_page"
        assert data.get("model_id") == "12345"
    
    @pytest.mark.asyncio
    async def test_api_client_basic_functionality(self):
        """Test API client basic functionality"""
        # Test initialization
        client = CivitAIApiClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert client.session is None
    
    def test_config_manager_integration(self, temp_dir):
        """Test configuration manager with all components"""
        # Create config manager
        config_manager = ConfigManager(temp_dir / "config.json")
        
        # Test all getter methods
        api_key = config_manager.get_api_key()
        csvs_dir = config_manager.get_csvs_directory()
        model_paths = config_manager.get_model_paths()
        download_settings = config_manager.get_download_settings()
        
        # Verify types and basic structure
        assert isinstance(api_key, str)
        assert isinstance(csvs_dir, str)
        assert isinstance(model_paths, dict)
        assert isinstance(download_settings, dict)
        
        # Test model manager integration
        model_manager = ModelManager(config_manager)
        assert model_manager.config_manager == config_manager
        
        # Test download path resolution
        test_path = model_manager.get_download_path("checkpoint", temp_dir)
        expected_path = temp_dir / model_paths["checkpoint"]
        assert test_path == expected_path
    
    @pytest.mark.asyncio
    async def test_basic_error_handling(self, temp_dir, sample_config_data):
        """Test basic error handling across components"""
        config_manager = ConfigManager(temp_dir / "config.json")
        
        # Test downloader initialization
        downloader = FileDownloader(download_settings=config_manager.get_download_settings())
        assert downloader.api_key is None
        
        # Test that it can be used as context manager
        async with downloader:
            assert downloader.session is not None
    
    def test_basic_csv_processing_edge_cases(self, temp_dir):
        """Test CSV processing with various edge cases"""
        # Create CSV with edge cases
        csv_content = """SrNo,Model_ID,Model_Name,Model_URL
1,12345,"Model with, comma",https://civitai.com/api/download/models/12345
2,67890,Model with "quotes",https://civitai.com/models/67890
3,,,
4,11111,Valid Model,https://civitai.com/api/download/models/11111"""
        
        csv_path = temp_dir / "edge_cases.csv"
        with open(csv_path, 'w') as f:
            f.write(csv_content)
        
        from src.utils.model_manager import CSVProcessor
        models = CSVProcessor.read_model_csv(csv_path)
        
        # Should handle the edge cases appropriately
        assert len(models) >= 2  # At least the valid entries
        
        # Find the valid entries
        valid_models = [m for m in models if m[2] and (m[3] or m[1])]
        assert len(valid_models) >= 2
