"""
Tests for ConfigManager
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from src.config.manager import ConfigManager


class TestConfigManager:
    """Test cases for ConfigManager class"""
    
    def test_load_existing_config(self, temp_dir, sample_config_data):
        """Test loading an existing configuration file"""
        config_path = temp_dir / "config.json"
        with open(config_path, 'w') as f:
            json.dump(sample_config_data, f)
        
        manager = ConfigManager(config_path)
        
        assert manager.config["civitai_api_key"] == "test_api_key_123"
        assert manager.config["csvs_directory"] == "CSVs"
        assert manager.config["download_settings"]["max_concurrent_downloads"] == 4
    
    def test_create_default_config_when_missing(self, temp_dir):
        """Test creating default config when file doesn't exist"""
        config_path = temp_dir / "nonexistent_config.json"
        
        manager = ConfigManager(config_path)
        
        # Should create default config
        assert config_path.exists()
        assert manager.config["civitai_api_key"] == ""
        assert manager.config["csvs_directory"] == "CSVs"
        assert "model_paths" in manager.config
        assert "download_settings" in manager.config
    
    def test_get_default_config(self):
        """Test getting default configuration"""
        manager = ConfigManager()
        default_config = manager.get_default_config()
        
        assert "civitai_api_key" in default_config
        assert "csvs_directory" in default_config
        assert "model_paths" in default_config
        assert "download_settings" in default_config
        assert default_config["model_paths"]["checkpoint"] == "models/Stable-diffusion"
        assert default_config["model_paths"]["lora"] == "models/Lora"
    
    def test_save_config(self, temp_dir, sample_config_data):
        """Test saving configuration"""
        config_path = temp_dir / "config.json"
        manager = ConfigManager(config_path)
        
        # Modify config
        manager.config["civitai_api_key"] = "new_api_key"
        manager.save_config()
        
        # Reload and verify
        with open(config_path, 'r') as f:
            saved_config = json.load(f)
        
        assert saved_config["civitai_api_key"] == "new_api_key"
    
    def test_get_api_key(self, config_manager):
        """Test getting API key"""
        assert config_manager.get_api_key() == "test_api_key_123"
    
    def test_set_api_key(self, config_manager):
        """Test setting API key"""
        new_key = "new_test_key"
        config_manager.set_api_key(new_key)
        
        assert config_manager.get_api_key() == new_key
        assert config_manager.config["civitai_api_key"] == new_key
    
    def test_get_csvs_directory(self, config_manager):
        """Test getting CSV directory"""
        assert config_manager.get_csvs_directory() == "CSVs"
    
    def test_set_csvs_directory(self, config_manager):
        """Test setting CSV directory"""
        new_dir = "MyCSVs"
        config_manager.set_csvs_directory(new_dir)
        
        assert config_manager.get_csvs_directory() == new_dir
    
    def test_get_model_paths(self, config_manager):
        """Test getting model paths"""
        model_paths = config_manager.get_model_paths()
        
        assert model_paths["checkpoint"] == "models/Stable-diffusion"
        assert model_paths["lora"] == "models/Lora"
        assert model_paths["vae"] == "models/VAE"
    
    def test_get_download_settings(self, config_manager):
        """Test getting download settings"""
        settings = config_manager.get_download_settings()
        
        assert settings["max_concurrent_downloads"] == 4
        assert settings["timeout"] == 30
        assert settings["retry_attempts"] == 3
    
    def test_update_config(self, config_manager):
        """Test updating configuration"""
        updates = {"new_setting": "new_value"}
        config_manager.update_config(updates)
        
        assert config_manager.config["new_setting"] == "new_value"
    
    def test_handle_corrupted_config(self, temp_dir):
        """Test handling corrupted config file"""
        config_path = temp_dir / "corrupted_config.json"
        with open(config_path, 'w') as f:
            f.write("invalid json content {")
        
        manager = ConfigManager(config_path)
        
        # Should fall back to default config
        assert manager.config == manager.get_default_config()
    
    def test_config_with_missing_keys(self, temp_dir):
        """Test handling config with missing keys"""
        incomplete_config = {"civitai_api_key": "test_key"}
        config_path = temp_dir / "incomplete_config.json"
        
        with open(config_path, 'w') as f:
            json.dump(incomplete_config, f)
        
        manager = ConfigManager(config_path)
        
        # The config will be the incomplete one since we don't merge with defaults
        assert manager.config["civitai_api_key"] == "test_key"
        # Missing keys will return defaults from getter methods
        assert manager.get_csvs_directory() == "CSVs"  # Default from getter
        assert isinstance(manager.get_model_paths(), dict)  # Will be empty dict
