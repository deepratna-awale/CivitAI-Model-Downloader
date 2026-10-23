"""
Tests for downloading models directly from CivitAI URLs
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from civitai_downloader.preprocess.preprocessor import URLPreprocessor, process_single_url
from civitai_downloader.utils.model_manager import ModelManager
from civitai_downloader.config.urls import to_civitai_host, download_url_for, hosts_to_try


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
        assert target["download_url"] == "https://civitai.com/api/download/models/130072"
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
    """Links stay on their own CivitAI site, with the others as fallbacks"""

    @pytest.mark.parametrize("url, expected", [
        ("https://civitai.com/api/download/models/1?type=Model", "https://civitai.com/api/download/models/1?type=Model"),
        ("http://www.civitai.com/api/download/models/1", "https://civitai.com/api/download/models/1"),
        ("https://civitai.green/models/1", "https://civitai.com/models/1"),
        ("https://civitai.red/api/download/models/1", "https://civitai.red/api/download/models/1"),
        ("https://civitai.community/models/1", "https://civitai.community/models/1"),
        ("https://example.com/civitai.com/x", "https://example.com/civitai.com/x"),
    ])
    def test_to_civitai_host(self, url, expected):
        assert to_civitai_host(url) == expected

    def test_to_civitai_host_moves_link(self):
        assert to_civitai_host("https://www.civitai.com/api/download/models/1?fileId=2", "https://civitai.red") == \
            "https://civitai.red/api/download/models/1?fileId=2"
        assert to_civitai_host("https://example.com/x", "https://civitai.red") == "https://example.com/x"

    @pytest.mark.parametrize("url, expected", [
        ("https://civitai.com/models/1", ["https://civitai.com", "https://civitai.red"]),
        ("http://www.civitai.green/models/1", ["https://civitai.com", "https://civitai.red"]),
        ("https://civitai.red/models/1", ["https://civitai.red", "https://civitai.com"]),
        ("4201", ["https://civitai.red", "https://civitai.com"]),
        (None, ["https://civitai.red", "https://civitai.com"]),
    ])
    def test_hosts_to_try(self, url, expected):
        assert hosts_to_try(url) == expected

    def test_download_url_for(self):
        assert download_url_for(42) == "https://civitai.red/api/download/models/42"
        assert download_url_for(42, "https://civitai.com") == "https://civitai.com/api/download/models/42"


def _session_with(statuses):
    """A mock aiohttp session answering each requested host with the given status"""
    session = MagicMock()
    requested = []

    def get(url, **kwargs):
        requested.append(url)
        host = next(h for h in statuses if url.startswith(h))
        response = MagicMock(status=statuses[host])
        response.json = AsyncMock(return_value=dict(VERSION_DATA, downloadUrl=f"{host}/api/download/models/130072"))
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=response)
        context.__aexit__ = AsyncMock(return_value=None)
        return context

    session.get.side_effect = get
    return session, requested


class TestHostFallback:
    """A model missing on the link's own site is looked up on the others"""

    @pytest.mark.asyncio
    async def test_own_host_is_used_when_it_has_the_model(self):
        session, requested = _session_with({"https://civitai.com": 200, "https://civitai.red": 200})

        success, target = await URLPreprocessor().resolve_download_target(
            session, "https://civitai.com/models/4201?modelVersionId=130072")

        assert success is True
        assert requested == ["https://civitai.com/api/v1/model-versions/130072"]
        assert target["download_url"] == "https://civitai.com/api/download/models/130072"

    @pytest.mark.asyncio
    async def test_falls_back_to_another_host(self):
        session, requested = _session_with({"https://civitai.com": 404, "https://civitai.red": 200})

        success, target = await URLPreprocessor().resolve_download_target(
            session, "https://civitai.com/api/download/models/130072?type=Model")

        assert success is True
        assert requested == ["https://civitai.com/api/v1/model-versions/130072",
                             "https://civitai.red/api/v1/model-versions/130072"]
        assert target["download_url"] == "https://civitai.red/api/download/models/130072?type=Model"

    @pytest.mark.asyncio
    async def test_download_stays_on_serving_host(self):
        """civitai.red's model endpoint lists civitai.com download links"""
        session = MagicMock()
        response = MagicMock(status=200)
        session.get.return_value.__aenter__ = AsyncMock(return_value=response)
        session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        model = dict(MODEL_DATA, modelVersions=[dict(MODEL_DATA["modelVersions"][0],
                                                     downloadUrl="https://civitai.com/api/download/models/999")])
        response.json = AsyncMock(return_value=model)

        success, target = await URLPreprocessor().resolve_download_target(session, "https://civitai.red/models/4201")

        assert success is True
        assert target["download_url"] == "https://civitai.red/api/download/models/999"

    @pytest.mark.asyncio
    async def test_missing_everywhere(self):
        session, requested = _session_with({"https://civitai.com": 404, "https://civitai.red": 404})

        success, message = await URLPreprocessor().resolve_download_target(session, "https://civitai.green/models/4201")

        assert success is False
        assert requested == ["https://civitai.com/api/v1/models/4201", "https://civitai.red/api/v1/models/4201"]


class TestMangledInput:
    """Links and stray words from a mistyped command line"""

    @pytest.mark.parametrize("url, expected", [
        ("https://civitai.red/api/download/models/2835136?fileId=2721540python",
         "https://civitai.red/api/download/models/2835136?fileId=2721540"),
        ("https://civitai.red/api/download/models/1?type=Model&fileId=abc",
         "https://civitai.red/api/download/models/1?type=Model"),
        ("https://civitai.red/models/4201?modelVersionId=130072x",
         "https://civitai.red/models/4201?modelVersionId=130072"),
        ("https://civitai.red/api/download/models/1?fileId=2&format=SafeTensor",
         "https://civitai.red/api/download/models/1?fileId=2&format=SafeTensor"),
        ("https://example.com/x?fileId=1abc", "https://example.com/x?fileId=1abc"),
        ("download.py", "download.py"),
    ])
    def test_sanitize_url(self, url, expected):
        assert URLPreprocessor().sanitize_url(url) == expected

    @pytest.mark.asyncio
    async def test_mangled_and_clean_links_resolve_to_same_download(self):
        preprocessor = URLPreprocessor()
        preprocessor.get_model_version_info = AsyncMock(return_value=VERSION_DATA)

        _, mangled = await preprocessor.resolve_download_target(
            MagicMock(), "https://civitai.red/api/download/models/130072?fileId=2721540python"
        )
        _, clean = await preprocessor.resolve_download_target(
            MagicMock(), "https://civitai.red/api/download/models/130072?fileId=2721540"
        )

        assert mangled["download_url"] == clean["download_url"] == \
            "https://civitai.red/api/download/models/130072?fileId=2721540"

    @pytest.mark.asyncio
    async def test_name_search_needs_exact_match(self):
        preprocessor = URLPreprocessor()
        preprocessor.search_models = AsyncMock(return_value=[{"id": 1, "name": "Some Other Model", "modelVersions": []}])

        success, message = await preprocessor.resolve_download_target(MagicMock(), "download.py")

        assert success is False
        assert "No model named 'download.py'" in message
        assert "'Some Other Model' (1)" in message

    @pytest.mark.asyncio
    async def test_name_search_exact_match_downloads(self):
        preprocessor = URLPreprocessor()
        preprocessor.search_models = AsyncMock(return_value=[
            {"id": 2, "name": "Realistic Vision Extra", "modelVersions": []},
            MODEL_DATA,
        ])

        success, target = await preprocessor.resolve_download_target(MagicMock(), "realistic vision")

        assert success is True
        assert target["model_id"] == "4201"
        assert target["download_url"] == "https://civitai.red/api/download/models/999"

    @pytest.mark.asyncio
    async def test_search_params_are_valid_query_values(self):
        session = MagicMock()
        response = MagicMock(status=200)
        response.json = AsyncMock(return_value={"items": []})
        session.get.return_value.__aenter__ = AsyncMock(return_value=response)
        session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        await URLPreprocessor().search_models(session, "anything")

        params = session.get.call_args.kwargs["params"]
        assert all(isinstance(value, (str, int, float)) and not isinstance(value, bool)
                   for value in params.values())


class TestRequestedFile:
    """Expected size and hash come from the file the link actually serves"""

    VERSION = {
        "id": 1, "modelId": 2, "downloadUrl": "https://civitai.red/api/download/models/1",
        "model": {"name": "M", "type": "Checkpoint"},
        "files": [
            {"id": 10, "name": "m_fp16.safetensors", "primary": True, "sizeKB": 2.0, "type": "Model",
             "metadata": {"format": "SafeTensor", "fp": "fp16"}, "hashes": {"SHA256": "AAA"}},
            {"id": 11, "name": "m.ckpt", "primary": False, "sizeKB": 3.5, "type": "Model",
             "metadata": {"format": "PickleTensor"}, "hashes": {"SHA256": "BBB"}},
        ],
    }

    @pytest.mark.parametrize("url, name, size, sha", [
        ("https://civitai.red/models/2", "m_fp16.safetensors", 2048, "AAA"),
        ("https://civitai.red/api/download/models/1?fileId=11", "m.ckpt", 3584, "BBB"),
        ("https://civitai.red/api/download/models/1?type=Model&format=PickleTensor", "m.ckpt", 3584, "BBB"),
        ("https://civitai.red/api/download/models/1?type=Model", None, None, None),
    ])
    @pytest.mark.asyncio
    async def test_requested_file(self, url, name, size, sha):
        preprocessor = URLPreprocessor()
        preprocessor.get_model_version_info = AsyncMock(return_value=self.VERSION)
        preprocessor.get_model_info = AsyncMock(return_value={"id": 2, "modelVersions": [self.VERSION]})

        success, target = await preprocessor.resolve_download_target(MagicMock(), url)

        assert success
        assert target["file_name"] == name
        assert target["file_size"] == size
        assert target["file_sha256"] == sha
