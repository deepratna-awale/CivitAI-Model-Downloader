"""
Tests for downloading models directly from CivitAI URLs
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.preprocess.preprocessor import URLPreprocessor, process_single_url
from src.utils.model_manager import ModelManager
from src.config.urls import to_civitai_host, download_url_for


VERSION_DATA = {
    "id": 130072,
    "modelId": 4201,
    "name": "V5.1",
    "downloadUrl": "https://civitai.red/api/download/models/130072",
    "model": {"name": "Realistic Vision", "type": "Checkpoint"},
    "files": [
        {"name": "realisticVision_v51-inpainting.safetensors", "primary": False},
        {"name": "realisticVision_v51.safetensors", "primary": True},
    ],
}

MODEL_DATA = {
    "id": 4201,
    "name": "Realistic Vision",
    "type": "Checkpoint",
    "modelVersions": [
        {
            "id": 999,
            "name": "V6.0",
            "downloadUrl": "https://civitai.red/api/download/models/999",
            "files": [{"name": "realisticVision_v60.safetensors", "primary": True}],
        },
        {
            "id": 130072,
            "name": "V5.1",
            "downloadUrl": "https://civitai.red/api/download/models/130072",
            "files": [{"name": "realisticVision_v51.safetensors", "primary": True}],
        },
    ],
}


class TestIdentifyUrlVariants:
    """URL formats users copy from the browser"""

    @pytest.mark.parametrize("url, expected_type, expected_data", [
        ("https://civitai.com/models/4201?modelVersionId=130072", "model_version_page",
         {"model_id": "4201", "model_version_id": "130072"}),
        ("https://civitai.com/models/4201/realistic-vision?modelVersionId=130072", "model_version_page",
         {"model_id": "4201", "model_version_id": "130072"}),
        ("https://civitai.com/models/4201/realistic-vision?foo=bar&modelVersionId=130072", "model_version_page",
         {"model_id": "4201", "model_version_id": "130072"}),
        ("https://www.civitai.com/models/4201/realistic-vision", "model_page", {"model_id": "4201"}),
        ("http://civitai.com/models/4201/", "model_page", {"model_id": "4201"}),
        ("https://civitai.green/models/4201", "model_page", {"model_id": "4201"}),
        ("https://civitai.red/models/4201/realistic-vision?modelVersionId=130072", "model_version_page",
         {"model_id": "4201", "model_version_id": "130072"}),
        ("https://civitai.red/api/download/models/130072", "download_url", {"model_version_id": "130072"}),
        ("https://civitai.com/api/download/models/130072?type=Model&format=SafeTensor", "download_url",
         {"model_version_id": "130072"}),
        ("  https://civitai.com/models/4201  ", "model_page", {"model_id": "4201"}),
    ])
    def test_identify(self, url, expected_type, expected_data):
        url_type, data = URLPreprocessor().identify_url_type(url)
        assert url_type == expected_type
        assert data == expected_data

    def test_other_domains_not_treated_as_civitai(self):
        url_type, _ = URLPreprocessor().identify_url_type("https://example.com/models/4201")
        assert url_type == "unknown"


class TestResolveDownloadTarget:
    """Resolving inputs to a downloadable file"""

    @pytest.mark.asyncio
    async def test_version_page_uses_requested_version(self):
        preprocessor = URLPreprocessor()
        preprocessor.get_model_version_info = AsyncMock(return_value=VERSION_DATA)
        preprocessor.get_model_info = AsyncMock()

        success, target = await preprocessor.resolve_download_target(
            MagicMock(), "https://civitai.com/models/4201?modelVersionId=130072"
        )

        assert success is True
        assert target["download_url"] == "https://civitai.red/api/download/models/130072"
        assert target["model_id"] == "4201"
        assert target["model_version_id"] == "130072"
        assert target["model_name"] == "Realistic Vision"
        assert target["model_type"] == "Checkpoint"
        assert target["file_name"] == "realisticVision_v51.safetensors"
        assert preprocessor.get_model_version_info.await_args.args[1] == "130072"
        preprocessor.get_model_info.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_model_page_uses_latest_version(self):
        preprocessor = URLPreprocessor()
        preprocessor.get_model_info = AsyncMock(return_value=MODEL_DATA)

        success, target = await preprocessor.resolve_download_target(
            MagicMock(), "https://civitai.com/models/4201/realistic-vision"
        )

        assert success is True
        assert target["download_url"] == "https://civitai.red/api/download/models/999"
        assert target["model_version_id"] == "999"
        assert target["model_name"] == "Realistic Vision"
        assert target["model_type"] == "Checkpoint"
        assert target["file_name"] == "realisticVision_v60.safetensors"

    @pytest.mark.asyncio
    async def test_version_lookup_falls_back_to_model(self):
        preprocessor = URLPreprocessor()
        preprocessor.get_model_version_info = AsyncMock(return_value=None)
        preprocessor.get_model_info = AsyncMock(return_value=MODEL_DATA)

        success, target = await preprocessor.resolve_download_target(
            MagicMock(), "https://civitai.com/models/4201?modelVersionId=130072"
        )

        assert success is True
        assert target["model_version_id"] == "130072"
        assert target["file_name"] == "realisticVision_v51.safetensors"

    @pytest.mark.asyncio
    async def test_download_url_keeps_query_string(self):
        preprocessor = URLPreprocessor()
        preprocessor.get_model_version_info = AsyncMock(return_value=VERSION_DATA)
        url = "https://civitai.com/api/download/models/130072?type=Model&format=SafeTensor"

        success, target = await preprocessor.resolve_download_target(MagicMock(), url)

        assert success is True
        assert target["download_url"] == "https://civitai.red/api/download/models/130072?type=Model&format=SafeTensor"
        assert target["model_type"] == "Checkpoint"

    @pytest.mark.asyncio
    async def test_download_url_without_metadata_still_downloads(self):
        preprocessor = URLPreprocessor()
        preprocessor.get_model_version_info = AsyncMock(return_value=None)
        url = "https://civitai.com/api/download/models/130072"

        success, target = await preprocessor.resolve_download_target(MagicMock(), url)

        assert success is True
        assert target["download_url"] == "https://civitai.red/api/download/models/130072"
        assert target["model_type"] is None
        assert target["file_name"] is None

    @pytest.mark.asyncio
    async def test_unresolvable_input_fails(self):
        preprocessor = URLPreprocessor()
        preprocessor.get_model_info = AsyncMock(return_value=None)

        success, message = await preprocessor.resolve_download_target(MagicMock(), "4201")

        assert success is False
        assert "Could not resolve" in message

    @pytest.mark.asyncio
    async def test_process_single_url_reports_version_metadata(self, monkeypatch):
        monkeypatch.setattr(URLPreprocessor, "get_model_version_info", AsyncMock(return_value=VERSION_DATA))

        success, result, metadata = await process_single_url("https://civitai.com/api/download/models/130072")

        assert success is True
        assert result == "https://civitai.red/api/download/models/130072"
        assert metadata["model_id"] == "4201"
        assert metadata["model_name"] == "Realistic Vision"
        assert metadata["version_name"] == "V5.1"


class TestModelTypeKey:
    """Mapping CivitAI model types to download folders"""

    @pytest.fixture
    def model_manager(self):
        config_manager = MagicMock()
        config_manager.get_model_paths.return_value = {
            "checkpoint": "models/Stable-diffusion",
            "lora": "models/Lora",
            "locon": "models/Lora",
            "textualinversion": "Embeddings",
            "other": "models/Other",
        }
        return ModelManager(config_manager)

    @pytest.mark.parametrize("api_type, expected", [
        ("Checkpoint", "checkpoint"),
        ("LORA", "lora"),
        ("LoCon", "locon"),
        ("DoRA", "lora"),
        ("TextualInversion", "textualinversion"),
        ("Workflows", "other"),
        (None, "other"),
    ])
    def test_model_type_key(self, model_manager, api_type, expected):
        assert model_manager.model_type_key(api_type) == expected


class TestCivitaiHost:
    """Requests go to civitai.red whatever host the link was copied from"""

    @pytest.mark.parametrize("url, expected", [
        ("https://civitai.com/api/download/models/1?type=Model", "https://civitai.red/api/download/models/1?type=Model"),
        ("http://www.civitai.com/api/download/models/1", "https://civitai.red/api/download/models/1"),
        ("https://civitai.green/models/1", "https://civitai.red/models/1"),
        ("https://civitai.red/api/download/models/1", "https://civitai.red/api/download/models/1"),
        ("https://civitai.community/models/1", "https://civitai.community/models/1"),
        ("https://example.com/civitai.com/x", "https://example.com/civitai.com/x"),
    ])
    def test_to_civitai_host(self, url, expected):
        assert to_civitai_host(url) == expected

    def test_download_url_for(self):
        assert download_url_for(42) == "https://civitai.red/api/download/models/42"
