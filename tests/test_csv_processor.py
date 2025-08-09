"""
Tests for CSV Processor and Model Manager
"""

import pytest
import csv
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.utils.model_manager import CSVProcessor, ModelManager


class TestCSVProcessor:
    """Test cases for CSVProcessor class"""
    
    def test_read_model_csv_valid_file(self, temp_dir):
        """Test reading a valid CSV file"""
        csv_content = """SrNo,Model_ID,Model_Name,Model_URL
1,12345,Test Model 1,https://civitai.com/api/download/models/12345
2,67890,Test Model 2,https://civitai.com/models/67890
3,11111,Test Model 3,"""
        
        csv_path = temp_dir / "test.csv"
        with open(csv_path, 'w') as f:
            f.write(csv_content)
        
        models = CSVProcessor.read_model_csv(csv_path)
        
        assert len(models) == 3
        assert models[0] == ("1", "12345", "Test Model 1", "https://civitai.com/api/download/models/12345")
        assert models[1] == ("2", "67890", "Test Model 2", "https://civitai.com/models/67890")
        assert models[2] == ("3", "11111", "Test Model 3", "")
    
    def test_read_model_csv_empty_file(self, temp_dir):
        """Test reading an empty CSV file"""
        csv_path = temp_dir / "empty.csv"
        csv_path.touch()
        
        models = CSVProcessor.read_model_csv(csv_path)
        
        assert models == []
    
    def test_read_model_csv_nonexistent_file(self, temp_dir):
        """Test reading a non-existent CSV file"""
        csv_path = temp_dir / "nonexistent.csv"
        
        models = CSVProcessor.read_model_csv(csv_path)
        
        assert models == []
    
    def test_read_model_csv_with_header_variations(self, temp_dir):
        """Test reading CSV with different header variations"""
        csv_content = """Sr No,Model_ID,Model_Name,Model_URL
1,12345,Test Model 1,https://civitai.com/api/download/models/12345"""
        
        csv_path = temp_dir / "test_header.csv"
        with open(csv_path, 'w') as f:
            f.write(csv_content)
        
        models = CSVProcessor.read_model_csv(csv_path)
        
        assert len(models) == 1
        assert models[0] == ("1", "12345", "Test Model 1", "https://civitai.com/api/download/models/12345")
    
    def test_read_model_csv_skip_invalid_rows(self, temp_dir):
        """Test skipping invalid rows in CSV"""
        csv_content = """SrNo,Model_ID,Model_Name,Model_URL
1,12345,Test Model 1,https://civitai.com/api/download/models/12345
incomplete_row
3,67890,Test Model 2,https://civitai.com/models/67890"""
        
        csv_path = temp_dir / "test_invalid.csv"
        with open(csv_path, 'w') as f:
            f.write(csv_content)
        
        models = CSVProcessor.read_model_csv(csv_path)
        
        assert len(models) == 2
        assert models[0][2] == "Test Model 1"
        assert models[1][2] == "Test Model 2"
    
    def test_get_model_types(self, temp_dir):
        """Test getting model types from CSV files"""
        # Create test CSV files
        (temp_dir / "checkpoint.csv").touch()
        (temp_dir / "lora.csv").touch()
        (temp_dir / "template.csv").touch()
        (temp_dir / "vae.csv").touch()
        (temp_dir / "not_a_csv.txt").touch()
        
        model_types = CSVProcessor.get_model_types(temp_dir)
        
        expected_types = {"checkpoint", "lora", "vae"}  # template should be excluded
        assert set(model_types) == expected_types
    
    def test_get_model_types_nonexistent_directory(self, temp_dir):
        """Test getting model types from non-existent directory"""
        nonexistent_dir = temp_dir / "nonexistent"
        
        model_types = CSVProcessor.get_model_types(nonexistent_dir)
        
        assert model_types == []


class TestModelManager:
    """Test cases for ModelManager class"""
    
    def test_initialization(self, config_manager):
        """Test ModelManager initialization"""
        manager = ModelManager(config_manager)
        
        assert manager.config_manager == config_manager
        assert isinstance(manager.csv_processor, CSVProcessor)
    
    def test_get_download_path_known_type(self, config_manager, temp_dir):
        """Test getting download path for known model type"""
        manager = ModelManager(config_manager)
        
        download_path = manager.get_download_path("checkpoint", temp_dir)
        
        expected_path = temp_dir / "models/Stable-diffusion"
        assert download_path == expected_path
        assert download_path.exists()  # Should be created
    
    def test_get_download_path_unknown_type(self, config_manager, temp_dir):
        """Test getting download path for unknown model type"""
        manager = ModelManager(config_manager)
        
        download_path = manager.get_download_path("unknown_type", temp_dir)
        
        expected_path = temp_dir / "models/Other"
        assert download_path == expected_path
        assert download_path.exists()  # Should be created
    
    def test_prepare_download_tasks_with_urls(self, config_manager, temp_dir):
        """Test preparing download tasks with existing URLs"""
        # Setup CSV file
        csv_dir = temp_dir / "CSVs"
        csv_dir.mkdir()
        csv_content = """SrNo,Model_ID,Model_Name,Model_URL
1,12345,Test Model 1,https://civitai.com/api/download/models/12345
2,67890,Test Model 2,https://civitai.com/models/67890"""
        
        csv_path = csv_dir / "checkpoint.csv"
        with open(csv_path, 'w') as f:
            f.write(csv_content)
        
        # Mock config to use temp directory
        config_manager.config["csvs_directory"] = "CSVs"
        
        with patch.object(Path, 'cwd', return_value=temp_dir):
            manager = ModelManager(config_manager)
            tasks = manager.prepare_download_tasks("checkpoint", temp_dir)
        
        assert len(tasks) == 2
        assert tasks[0][0] == "https://civitai.com/api/download/models/12345"
        assert tasks[1][0] == "https://civitai.com/models/67890"
        
        # Check file paths
        expected_dir = temp_dir / "models/Stable-diffusion"
        assert tasks[0][1] == expected_dir / "Test Model 1.safetensors"
        assert tasks[1][1] == expected_dir / "Test Model 2.safetensors"
    
    def test_prepare_download_tasks_with_missing_urls(self, config_manager, temp_dir):
        """Test preparing download tasks with missing URLs and handler"""
        # Setup CSV file with missing URLs
        csv_dir = temp_dir / "CSVs"
        csv_dir.mkdir()
        csv_content = """SrNo,Model_ID,Model_Name,Model_URL
1,12345,Test Model 1,
2,67890,Test Model 2,https://civitai.com/api/download/models/67890"""
        
        csv_path = csv_dir / "lora.csv"
        with open(csv_path, 'w') as f:
            f.write(csv_content)
        
        # Mock config
        config_manager.config["csvs_directory"] = "CSVs"
        
        # Mock missing URL handler that resolves the first task
        def mock_handler(missing_tasks, model_type):
            # missing_tasks is a list of (model_id, model_name, file_path) tuples
            resolved_tasks = []
            for model_id, model_name, file_path in missing_tasks:
                resolved_url = f"https://civitai.com/api/download/models/{model_id}"
                resolved_tasks.append((resolved_url, file_path))
            return resolved_tasks
        
        with patch.object(Path, 'cwd', return_value=temp_dir):
            manager = ModelManager(config_manager)
            tasks = manager.prepare_download_tasks("lora", temp_dir, mock_handler)
        
        assert len(tasks) == 2
        # Both tasks should be present (order may vary based on processing)
        urls = [task[0] for task in tasks]
        assert "https://civitai.com/api/download/models/12345" in urls
        assert "https://civitai.com/api/download/models/67890" in urls
    
    def test_prepare_download_tasks_no_csv(self, config_manager, temp_dir):
        """Test preparing download tasks when CSV doesn't exist"""
        config_manager.config["csvs_directory"] = "CSVs"
        
        with patch.object(Path, 'cwd', return_value=temp_dir):
            manager = ModelManager(config_manager)
            tasks = manager.prepare_download_tasks("nonexistent", temp_dir)
        
        assert tasks == []
    
    def test_get_available_model_types(self, config_manager, temp_dir):
        """Test getting available model types"""
        # Setup CSV directory with files
        csv_dir = temp_dir / "CSVs"
        csv_dir.mkdir()
        (csv_dir / "checkpoint.csv").touch()
        (csv_dir / "lora.csv").touch()
        (csv_dir / "template.csv").touch()
        
        config_manager.config["csvs_directory"] = "CSVs"
        
        with patch.object(Path, 'cwd', return_value=temp_dir):
            manager = ModelManager(config_manager)
            model_types = manager.get_available_model_types()
        
        expected_types = {"checkpoint", "lora"}  # template should be excluded
        assert set(model_types) == expected_types
    
    def test_prepare_download_tasks_empty_csv(self, config_manager, temp_dir):
        """Test preparing download tasks with empty CSV"""
        # Setup empty CSV file
        csv_dir = temp_dir / "CSVs"
        csv_dir.mkdir()
        csv_path = csv_dir / "empty.csv"
        csv_path.touch()
        
        config_manager.config["csvs_directory"] = "CSVs"
        
        with patch.object(Path, 'cwd', return_value=temp_dir):
            manager = ModelManager(config_manager)
            tasks = manager.prepare_download_tasks("empty", temp_dir)
        
        assert tasks == []
