"""
Basic setup and smoke tests
"""

import sys
from pathlib import Path


def test_imports():
    """Test that all modules can be imported"""
    try:
        from src.config.manager import ConfigManager
        from src.api.client import CivitAIApiClient
        from src.preprocess.preprocessor import URLPreprocessor
        from src.utils.model_manager import ModelManager, CSVProcessor
        from src.downloader.file_downloader import FileDownloader, ProgressManager
        assert True, "All imports successful"
    except ImportError as e:
        assert False, f"Import failed: {e}"


def test_basic_functionality():
    """Test basic functionality without external dependencies"""
    from src.config.manager import ConfigManager
    
    # Test config manager can be created
    config_manager = ConfigManager()
    assert config_manager is not None
    
    # Test default config has required keys
    default_config = config_manager.get_default_config()
    required_keys = ["civitai_api_key", "csvs_directory", "model_paths", "download_settings"]
    
    for key in required_keys:
        assert key in default_config, f"Missing required config key: {key}"


def test_url_patterns():
    """Test URL pattern matching"""
    from src.preprocess.preprocessor import URLPreprocessor
    
    preprocessor = URLPreprocessor()
    
    # Test download URL pattern
    url_type, data = preprocessor.identify_url_type("https://civitai.com/api/download/models/12345")
    assert url_type == "download_url"
    assert data.get("model_version_id") == "12345"
    
    # Test model page pattern
    url_type, data = preprocessor.identify_url_type("https://civitai.com/models/67890")
    assert url_type in ["model_page", "short_url"]
    assert data.get("model_id") == "67890"


def test_csv_processor_basic():
    """Test CSV processor with basic functionality"""
    from src.utils.model_manager import CSVProcessor
    import tempfile
    from pathlib import Path
    
    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("SrNo,Model_ID,Model_Name,Model_URL\n")
        f.write("1,12345,Test Model,https://example.com/model.safetensors\n")
        csv_path = Path(f.name)
    
    try:
        models = CSVProcessor.read_model_csv(csv_path)
        assert len(models) == 1
        assert models[0][2] == "Test Model"
        assert models[0][3] == "https://example.com/model.safetensors"
    finally:
        csv_path.unlink()  # Clean up


def test_project_structure():
    """Test that project structure is correct"""
    project_root = Path(__file__).parent.parent
    
    # Check main directories exist
    assert (project_root / "src").exists(), "src directory missing"
    assert (project_root / "tests").exists(), "tests directory missing"
    
    # Check main modules exist
    src_modules = ["config", "api", "preprocess", "utils", "downloader"]
    for module in src_modules:
        module_path = project_root / "src" / module
        assert module_path.exists(), f"Module {module} missing"
        assert (module_path / "__init__.py").exists(), f"Module {module} missing __init__.py"


if __name__ == "__main__":
    # Run basic tests
    print("Running basic setup tests...")
    
    try:
        test_imports()
        print("✓ Import test passed")
        
        test_basic_functionality()
        print("✓ Basic functionality test passed")
        
        test_url_patterns()
        print("✓ URL patterns test passed")
        
        test_csv_processor_basic()
        print("✓ CSV processor test passed")
        
        test_project_structure()
        print("✓ Project structure test passed")
        
        print("\nAll basic tests passed! ✅")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
