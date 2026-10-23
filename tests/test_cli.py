"""
Tests for the packaged command line interface
"""

import argparse
import pytest
from unittest.mock import AsyncMock, patch

from civitai_downloader import cli
from civitai_downloader.cli import CivitAIDownloaderCLI


def make_cli(**kwargs):
    defaults = {"api_key": None, "csvs_dir": None, "ui": None, "model_type": None, "flat": False}
    defaults.update(kwargs)
    return CivitAIDownloaderCLI(argparse.Namespace(**defaults))


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    """The CLI reads and writes config.json in the working directory"""
    monkeypatch.chdir(tmp_path)
    for name in cli.API_KEY_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return tmp_path


class TestDownloadUrls:
    @pytest.mark.asyncio
    async def test_unresolvable_url_is_reported_as_failed(self, tmp_path):
        """download_urls opens a real HTTP session, so its imports must be in place"""
        downloader = make_cli()
        resolve = AsyncMock(return_value=(False, "No model found"))
        with patch.object(cli.URLPreprocessor, "resolve_download_target", resolve):
            downloaded, failed = await downloader.download_urls(["not-a-model"], output_dir=tmp_path)
        assert (downloaded, failed) == (0, 1)
        resolve.assert_awaited_once()


class TestApiKey:
    def test_env_var_is_used(self, monkeypatch):
        monkeypatch.setenv("CAI_API_KEY", "env-key")
        downloader = make_cli()
        assert downloader.api_key_source == "env"
        assert downloader.config_manager.get_api_key() == "env-key"

    def test_env_var_beats_config_file(self, isolated_cwd, monkeypatch):
        (isolated_cwd / "config.json").write_text('{"civitai_api_key": "file-key"}')
        monkeypatch.setenv("CAI_API_KEY", "env-key")
        assert make_cli().config_manager.get_api_key() == "env-key"

    def test_api_key_flag_can_name_env_var(self, monkeypatch):
        monkeypatch.setenv("MY_KEY", "named-env-key")
        downloader = make_cli(api_key="MY_KEY")
        assert downloader.api_key_source == "env"
        assert downloader.config_manager.get_api_key() == "named-env-key"

    def test_config_file_key_is_used_without_prompting(self, isolated_cwd, monkeypatch):
        (isolated_cwd / "config.json").write_text('{"civitai_api_key": "file-key"}')
        monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("should not prompt"))
        downloader = make_cli()
        assert downloader.api_key_source is None
        downloader.setup_api_key()
        assert downloader.config_manager.get_api_key() == "file-key"

