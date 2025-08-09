# Testing Documentation for CivitAI Model Downloader

This directory contains comprehensive test suites for the CivitAI Model Downloader project.

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Shared fixtures and utilities
├── test_config_manager.py      # Tests for configuration management
├── test_api_client.py          # Tests for CivitAI API client
├── test_url_preprocessor.py    # Tests for URL preprocessing
├── test_csv_processor.py       # Tests for CSV processing and model management
├── test_file_downloader.py     # Tests for file downloading functionality
└── test_integration.py         # Integration tests for complete workflows
```

## Test Categories

### Unit Tests
- **Config Manager**: Configuration loading, saving, validation
- **API Client**: CivitAI API interactions, authentication, error handling
- **URL Preprocessor**: URL parsing, conversion, preprocessing logic
- **CSV Processor**: CSV file reading, model data extraction
- **File Downloader**: File download logic, progress tracking, retry mechanisms

### Integration Tests
- **Complete Workflow**: End-to-end download process
- **Component Integration**: How different modules work together
- **Error Handling**: Cross-component error scenarios
- **Concurrent Operations**: Multi-file download scenarios

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r requirements-test.txt
```

Or using the test runner:
```bash
python run_tests.py --install
```

### Running All Tests
```bash
# Using pytest directly
pytest tests/

# Using the test runner
python run_tests.py
```

### Running Specific Test Categories
```bash
# Unit tests only
python run_tests.py --type unit

# Integration tests only
python run_tests.py --type integration

# Fast tests (excluding slow ones)
python run_tests.py --type fast
```

### Running with Coverage
```bash
# With coverage report
python run_tests.py --verbose

# Without coverage
python run_tests.py --no-coverage
```

### Running Individual Test Files
```bash
# Test specific module
pytest tests/test_config_manager.py -v

# Test specific function
pytest tests/test_api_client.py::TestCivitAIApiClient::test_client_initialization -v
```

## Test Features

### Async Testing
- Uses `pytest-asyncio` for testing async functions
- Proper event loop management
- Async context manager testing

### Mocking
- Extensive use of `unittest.mock` for isolation
- HTTP request mocking with `aiohttp`
- File system operation mocking
- API response simulation

### Fixtures
- **temp_dir**: Temporary directory for file operations
- **config_manager**: Pre-configured configuration manager
- **sample_config_data**: Test configuration data
- **csv_file**: Sample CSV file for testing
- **api_client**: CivitAI API client instance
- **mock_aiohttp_session**: Mocked HTTP session

### Test Data
- Sample configuration files
- Mock CSV data with various URL types
- Simulated API responses
- Edge case scenarios

## Writing New Tests

### Test Naming Convention
- Test files: `test_<module_name>.py`
- Test classes: `TestClassName`
- Test methods: `test_specific_functionality`

### Example Test Structure
```python
import pytest
from unittest.mock import patch, AsyncMock

class TestNewFeature:
    """Test cases for new feature"""
    
    def test_basic_functionality(self):
        """Test basic functionality"""
        # Arrange
        # Act
        # Assert
        pass
    
    @pytest.mark.asyncio
    async def test_async_functionality(self):
        """Test async functionality"""
        # Arrange
        # Act
        # Assert
        pass
    
    def test_error_handling(self):
        """Test error handling"""
        with pytest.raises(ExpectedError):
            # Code that should raise ExpectedError
            pass
```

### Best Practices
1. **Isolation**: Each test should be independent
2. **Mocking**: Mock external dependencies (HTTP, file system)
3. **Coverage**: Aim for high test coverage
4. **Documentation**: Clear test descriptions
5. **Edge Cases**: Test boundary conditions and error scenarios

## Common Test Patterns

### Testing Async Functions
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result == expected_value
```

### Mocking HTTP Requests
```python
with patch('aiohttp.ClientSession') as mock_session:
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"key": "value"}
    mock_session.return_value.get.return_value.__aenter__.return_value = mock_response
    
    # Test code here
```

### Testing File Operations
```python
def test_file_operation(temp_dir):
    file_path = temp_dir / "test_file.txt"
    # Test file operations using temp_dir
```

### Testing Configuration
```python
def test_config_loading(config_manager):
    api_key = config_manager.get_api_key()
    assert api_key == "expected_key"
```

## Test Maintenance

### Regular Tasks
1. **Update test data** when API responses change
2. **Add tests** for new features
3. **Refactor tests** when code structure changes
4. **Update mocks** when external dependencies change

### Performance Considerations
- Use appropriate fixtures to avoid test setup overhead
- Mock expensive operations (network calls, file I/O)
- Mark slow tests appropriately
- Use parametrized tests for multiple similar scenarios

## Debugging Tests

### Common Issues
1. **Import Errors**: Ensure test requirements are installed
2. **Async Issues**: Use proper pytest-asyncio markers
3. **Mock Issues**: Verify mock setup matches actual usage
4. **File Path Issues**: Use temp_dir fixture for file operations

### Debugging Commands
```bash
# Run with verbose output
pytest tests/ -v -s

# Run specific test with pdb
pytest tests/test_config_manager.py::test_specific -v -s --pdb

# Show test coverage
pytest tests/ --cov=src --cov-report=html
```

## Continuous Integration

The test suite is designed to run in CI environments:
- All external dependencies are mocked
- No real network calls are made
- Temporary directories are used for file operations
- Tests are isolated and can run in parallel

Example CI configuration:
```yaml
- name: Install dependencies
  run: pip install -r requirements-test.txt
  
- name: Run tests
  run: python run_tests.py --verbose
```
