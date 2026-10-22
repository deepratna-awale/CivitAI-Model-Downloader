"""
Tests for per-UI model folder layouts
"""

import json
import pytest

from src.config.manager import ConfigManager
from src.config.ui_presets import UI_PRESETS, detect_ui, normalize_ui
from src.utils.model_manager import ModelManager


class TestNormalizeUi:

    @pytest.mark.parametrize("name, expected", [
        ("ComfyUI", "comfyui"),
        ("comfy", "comfyui"),
        ("SD.Next", "sdnext"),
        ("next", "sdnext"),
        ("automatic1111", "a1111"),
        ("reForge", "reforge"),
        ("swarm", "swarmui"),
        ("invokeai", None),
        (None, None),
    ])
    def test_normalize(self, name, expected):
        assert normalize_ui(name) == expected


class TestDetectUi:

    @pytest.mark.parametrize("files, expected", [
        (["comfy/", "custom_nodes/", "main.py"], "comfyui"),
        (["fooocus_version.py", "models/"], "fooocus"),
        (["launchtools/", "Models/"], "swarmui"),
        (["installer.py", "modules/", "webui.py"], "sdnext"),
        (["modules_forge/", "modules/", "webui.py"], "forge"),
        (["webui.py", "modules/"], "a1111"),
        (["random.txt"], None),
    ])
    def test_detect(self, tmp_path, files, expected):
        for name in files:
            path = tmp_path / name
            if name.endswith("/"):
                path.mkdir(parents=True)
            else:
                path.touch()
        assert detect_ui(tmp_path) == expected


class TestUiModelPaths:

    @pytest.fixture
    def config_manager(self, tmp_path):
        config_path = tmp_path / "config.json"
        manager = ConfigManager(config_path)
        manager.config["model_paths"]["lora"] = "custom/Lora"
        return manager

    def test_default_uses_config_paths(self, config_manager):
        assert config_manager.get_model_paths()["lora"] == "custom/Lora"

    @pytest.mark.parametrize("ui", ["a1111", "forge", "reforge"])
    def test_a1111_family_keeps_config_paths(self, config_manager, ui):
        config_manager.set_ui(ui)
        assert config_manager.get_model_paths()["lora"] == "custom/Lora"

    def test_comfyui_layout(self, config_manager, tmp_path):
        config_manager.set_ui("comfyui")
        model_manager = ModelManager(config_manager)

        assert model_manager.model_type_key("LORA") == "lora"
        assert model_manager.get_download_path("lora", tmp_path) == tmp_path / "models/loras"
        assert model_manager.get_download_path("checkpoint", tmp_path) == tmp_path / "models/checkpoints"
        assert model_manager.get_download_path("textualinversion", tmp_path) == tmp_path / "models/embeddings"

    def test_unsupported_type_falls_back_to_other(self, config_manager):
        config_manager.set_ui("fooocus")
        assert ModelManager(config_manager).model_type_key("Hypernetwork") == "other"

    def test_ui_from_config_file(self, tmp_path):
        config_path = tmp_path / "config.json"
        ConfigManager(config_path)
        data = json.loads(config_path.read_text())
        data["ui"] = "ComfyUI"
        config_path.write_text(json.dumps(data))

        manager = ConfigManager(config_path)
        assert manager.get_ui() == "comfyui"
        assert manager.get_model_paths() == UI_PRESETS["comfyui"]

    def test_set_ui_is_not_saved(self, config_manager):
        config_manager.set_ui("comfyui")
        config_manager.save_config()
        assert "ui" not in json.loads(config_manager.config_path.read_text())

    def test_every_preset_has_core_folders(self):
        for ui, paths in UI_PRESETS.items():
            for key in ("checkpoint", "lora", "vae", "textualinversion", "other"):
                assert key in paths, f"{ui} is missing {key}"
