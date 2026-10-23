"""
Tests for the bundled AutoExpress expression LoRA list and --ae-expression-loras
"""

import argparse
import sys
import pytest
from unittest.mock import AsyncMock, patch

from civitai_downloader import cli
from civitai_downloader.cli import CivitAIDownloaderCLI
from civitai_downloader.expression_loras import (
    EXPRESSION_MODEL_TYPES,
    expression_loras_for,
    load_expression_loras,
    normalize_expression_type,
)


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in cli.API_KEY_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return tmp_path


def make_cli(**kwargs):
    defaults = {"api_key": None, "csvs_dir": None, "ui": None, "model_type": None, "flat": False,
                "expression_loras": None}
    defaults.update(kwargs)
    return CivitAIDownloaderCLI(argparse.Namespace(**defaults))


def parse(*argv):
    with patch.object(sys, "argv", ["civitai-download", *argv]):
        return cli.parse_arguments()


class TestBundledList:
    def test_every_model_type_has_a_lora(self):
        loras = load_expression_loras()
        assert {lora["model_type"] for lora in loras} == set(EXPRESSION_MODEL_TYPES)
        assert len(loras) == 6
        for lora in loras:
            assert lora["url"].startswith("https://civitai.red/models/")
            assert "modelVersionId=" in lora["url"]

    def test_filter_by_model_type(self):
        names = [lora["name"] for lora in expression_loras_for(["illustrious"])]
        assert names == ["AutoExpress-expressions-illustrious", "AutoExpress-face-enhancer-illustrious"]
        assert expression_loras_for(["illustrious"])[1]["url"] == \
            "https://civitai.red/models/1625070?modelVersionId=1839268"

    def test_no_filter_returns_everything(self):
        assert expression_loras_for([]) == load_expression_loras()

    @pytest.mark.parametrize("value,expected", [
        ("Pony", "pony"), ("NoobAI", "illustrious"), ("illu", "illustrious"),
        ("xl", "sdxl"), ("SD1.5", "sd15"), ("flux", "flux"), ("sd3", None),
    ])
    def test_aliases(self, value, expected):
        assert normalize_expression_type(value) == expected


class TestArguments:
    def test_flag_absent(self):
        assert parse().expression_loras is None

    def test_flag_without_types_means_all(self):
        assert parse("--sd", "ComfyUI", "--ae-expression-loras").expression_loras == []

    def test_flag_with_types(self):
        assert parse("--ae-expression-loras", "pony", "noobai").expression_loras == ["pony", "illustrious"]

    def test_short_alias(self):
        assert parse("--expression-loras", "flux").expression_loras == ["flux"]

    def test_unknown_type_is_rejected(self):
        with pytest.raises(SystemExit):
            parse("--ae-expression-loras", "sd3")


class TestDownload:
    @pytest.mark.asyncio
    async def test_expression_loras_go_into_lora_folder(self, tmp_path):
        downloader = make_cli(expression_loras=["sdxl"], model_type="checkpoint")
        target = {
            "download_url": "https://civitai.red/api/download/models/761462",
            "file_name": "expressions_xl.safetensors", "file_size": None, "file_sha256": None,
            "model_name": "Facial Expressions", "version_name": "XL v3",
            "model_version_id": 761462, "model_type": "Checkpoint",
        }
        resolve = AsyncMock(return_value=(True, target))
        download = AsyncMock(return_value=[(True, "Downloaded")])
        urls = [lora["url"] for lora in downloader.collect_expression_loras()]
        forced = {url: "lora" for url in urls}
        with patch.object(cli.URLPreprocessor, "resolve_download_target", resolve), \
             patch.object(cli.FileDownloader, "download_files", download):
            downloaded, failed = await downloader.download_urls(urls, output_dir=tmp_path, forced_types=forced)
        assert (downloaded, failed) == (1, 0)
        file_path = download.await_args.args[0][0][1]
        assert file_path == tmp_path / "lora" / "expressions_xl.safetensors"
