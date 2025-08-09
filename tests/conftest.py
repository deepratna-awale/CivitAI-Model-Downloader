"""
Fixtures and utilities for testing CivitAI Model Downloader
"""

try:
    import pytest
    import asyncio
    import tempfile
    import json
    from pathlib import Path
    from unittest.mock import AsyncMock, MagicMock, patch
    from typing import Dict, Any
except ImportError as e:
    print(f"Import error in conftest.py: {e}")
    print("Please install test requirements: pip install -r requirements-test.txt")
    raise

try:
    from src.config.manager import ConfigManager
    from src.api.client import CivitAIApiClient
    from src.preprocess.preprocessor import URLPreprocessor
    from src.utils.model_manager import ModelManager, CSVProcessor
    from src.downloader.file_downloader import FileDownloader, ProgressManager
except ImportError as e:
    print(f"Import error for source modules: {e}")
    print("Make sure the src modules are available in PYTHONPATH")
    raise


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_data():
    """Sample configuration data for testing"""
    return {
        "civitai_api_key": "test_api_key_123",
        "csvs_directory": "CSVs",
        "model_paths": {
            "checkpoint": "models/Stable-diffusion",
            "lora": "models/Lora",
            "locon": "models/Lora",
            "lycoris": "models/Lora",
            "controlnet": "models/ControlNet",
            "hypernetwork": "models/hypernetworks",
            "vae": "models/VAE",
            "poses": "models/Poses",
            "textualinversion": "Embeddings",
            "upscaler": "models/ESRGAN",
            "aestheticgradient": "extensions/stable-diffusion-webui-aesthetic-gradients/aesthetic_embeddings",
            "motionmodule": "extensions/sd-webui-animatediff/model",
            "other": "models/Other"
        },
        "download_settings": {
            "max_concurrent_downloads": 4,
            "timeout": 30,
            "retry_attempts": 3,
            "chunk_size": 8192
        },
        "stable_diffusion_path": ""
    }


@pytest.fixture
def config_manager(temp_dir, sample_config_data):
    """Create a ConfigManager instance with test data"""
    config_path = temp_dir / "config.json"
    with open(config_path, 'w') as f:
        json.dump(sample_config_data, f)
    
    return ConfigManager(config_path)


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing"""
    return """SrNo,Model_ID,Model_Name,Model_URL
1,12345,Test Model 1,https://civitai.com/api/download/models/12345
2,67890,Test Model 2,https://civitai.com/models/67890
3,11111,Test Model 3,
4,22222,Test Model 4,https://civitai.com/models/22222?modelVersionId=33333"""


@pytest.fixture
def csv_file(temp_dir, sample_csv_content):
    """Create a test CSV file"""
    csv_path = temp_dir / "test_models.csv"
    with open(csv_path, 'w') as f:
        f.write(sample_csv_content)
    return csv_path


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session for testing API calls"""
    session = AsyncMock()
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={"test": "data"})
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    session.get.return_value = response
    return session


@pytest.fixture
def api_client():
    """Create an API client instance for testing"""
    return CivitAIApiClient(api_key="test_api_key")


@pytest.fixture
def url_preprocessor():
    """Create a URL preprocessor instance for testing"""
    return URLPreprocessor(api_key="test_api_key")


@pytest.fixture
def sample_api_responses():
    """Sample API responses for testing"""
    return {
        "model_info": {
            "id": 12345,
            "name": "Test Model",
            "type": "Checkpoint",
            "modelVersions": [
                {
                    "id": 67890,
                    "name": "v1.0",
                    "files": [
                        {
                            "id": 11111,
                            "name": "test_model.safetensors",
                            "type": "Model",
                            "downloadUrl": "https://civitai.com/api/download/models/67890"
                        }
                    ]
                }
            ]
        },
        "model_version_info": {
            "id": 67890,
            "name": "v1.0",
            "modelId": 12345,
            "files": [
                {
                    "id": 11111,
                    "name": "test_model.safetensors",
                    "type": "Model",
                    "downloadUrl": "https://civitai.com/api/download/models/67890"
                }
            ]
        }
    }


@pytest.fixture
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_file_download():
    """Mock file download for testing"""
    def _mock_download(url: str, file_path: Path, total_size: int = 1024):
        # Simulate file creation
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"mock_file_content")
        return True
    return _mock_download


@pytest.fixture
def progress_manager():
    """Create a ProgressManager for testing"""
    return ProgressManager(max_concurrent=2)
