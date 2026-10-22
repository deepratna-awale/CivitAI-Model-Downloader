# CivitAI Model Downloader

A professional, async multi-threaded downloader for CivitAI models with intelligent URL preprocessing, comprehensive testing, and CLI automation support.

## ✨ Features

- **🔐 API Authentication**: Full CivitAI API integration with bearer token support
- **⚡ High Performance**: Async multi-threaded downloads with configurable concurrency
- **🔄 Smart URL Processing**: Automatically converts any CivitAI URL format to proper download URLs
- **📁 Organized Downloads**: Automatic model type detection and organized folder structure
- **🎯 Progress Tracking**: Real-time progress bars with detailed download statistics
- **🛡️ Robust Error Handling**: Comprehensive retry logic and error recovery
- **🤖 CLI Automation**: Full command-line interface for scripted deployments
- **🧪 Thoroughly Tested**: 77+ tests with 96% success rate and comprehensive coverage
- **📊 CSV Management**: Batch processing with intelligent CSV file handling

## 🚀 Quick Start

### 1. Installation
```bash
git clone https://github.com/deepratnaawale/CivitAI-Model-Downloader.git
cd CivitAI-Model-Downloader
pip install -r requirements.txt
```

### 2. Get Your API Key
Visit [CivitAI Account Settings](https://civitai.com/user/account) and create an API token.

### 3. Basic Usage
```bash
# Interactive mode (recommended for first-time users)
python download.py

# Automated mode
python download.py --sd /path/to/stable-diffusion --api-key your-api-key

# Preprocess URLs then download
python download.py --preprocess --api-key your-api-key

# Download straight from a CivitAI URL (no CSV needed)
python download.py --url "https://civitai.red/models/4201?modelVersionId=130072" --sd ~/stable-diffusion-webui
```

## 📋 Requirements

- **Python**: 3.8+ (3.11+ recommended)
- **CivitAI API Key**: Required for authentication
- **Dependencies**: Auto-installed or via `pip install -r requirements.txt`
  - `aiohttp` - Async HTTP client
  - `aiofiles` - Async file operations  
  - `tqdm` - Progress bars
  - `loguru` - Advanced logging

## 🎯 Usage

### Interactive Mode
```bash
python download.py
```
The script will guide you through setup with prompts for:
- Stable Diffusion installation path
- CivitAI API key
- CSV directory location

### Command Line Interface
```bash
# Complete automation
python download.py \
  --sd ~/stable-diffusion-webui \
  --csv ./my-models \
  --api-key your-civitai-api-key

# Available options
python download.py --help
```

#### CLI Arguments
| Argument | Description | Default |
|----------|-------------|---------|
| `--sd`, `--stable-diffusion` | Stable Diffusion installation path | Interactive prompt |
| `--csv`, `--csvs-dir` | Directory containing CSV files | `CSVs` |
| `--api-key` | CivitAI API key, or the name of an env var holding it (e.g. `CAI_API_KEY`) | `CAI_API_KEY` / `CIVITAI_API_KEY` env var, then `config.json`, then prompt |
| `--preprocess` | Preprocess URLs before downloading | `False` |
| `--url`, `--urls` | Download one or more models from CivitAI URLs, model IDs or names | None |
| `--url-file` | Text file with one URL/ID/name per line (`#` comments allowed) | None |
| `--type` | Force every `--url` download into one model type folder (e.g. `lora`) | Detected from CivitAI |
| `-o`, `--output` | Folder to save `--url` downloads into, with a subfolder per type (no `--sd` needed) | None |
| `--flat` | With `--output`, skip the per-type subfolders | `False` |
| `--resolve-only` | With `--url`, show the download URL and model info without downloading | `False` |

### Download by URL
Paste any CivitAI link straight into the CLI. All API calls and downloads go through `https://civitai.red`; links copied from `civitai.com` or `civitai.green` are rewritten automatically. The model type (checkpoint, LoRA, embedding, ...) is looked up on CivitAI and the file is saved into the matching folder from `model_paths`, using the file's real name.

```bash
# Model page (latest version)
python download.py --url "https://civitai.red/models/4201/realistic-vision" --sd ~/stable-diffusion-webui

# A list of models of different types: each lands in its own folder
# (checkpoints in models/Stable-diffusion, LoRAs in models/Lora, embeddings in Embeddings, ...)
python download.py --sd ~/stable-diffusion-webui --url \
  "https://civitai.red/models/4201?modelVersionId=130072" \
  "https://civitai.red/api/download/models/9208" \
  7808

# Or keep the list in a file, one per line
python download.py --sd ~/stable-diffusion-webui --url-file my-models.txt

# Force the destination folder
python download.py --url "https://civitai.red/api/download/models/130072" --type lora --sd ~/stable-diffusion-webui

# Save into any folder instead of the Stable Diffusion tree
# (creates ~/Downloads/models/checkpoint, ~/Downloads/models/lora, ...; add --flat to skip subfolders)
python download.py --url "https://civitai.red/models/4201/realistic-vision" --output ~/Downloads/models

# Use an API key from an exported environment variable
export CAI_API_KEY=your-civitai-api-key
python download.py --url "https://civitai.red/api/download/models/130072" -o ./models
python download.py --api-key CAI_API_KEY --url "https://civitai.red/models/4201" -o ./models

# Just show what would be downloaded
python download.py --url "https://civitai.red/models/4201/realistic-vision" --resolve-only
```

API key lookup order: `--api-key` (a literal key, or the name of an exported variable), then the `CAI_API_KEY` or `CIVITAI_API_KEY` environment variable, then `config.json`. Keys read from the environment are never written to `config.json`.

Accepted inputs: model pages (with or without the name slug), `?modelVersionId=` version links, `/api/download/models/` links (query options like `?type=Model&format=SafeTensor` are kept), `civitai.com`, `civitai.red`, `civitai.green` and `www.` links, bare model IDs, and model names. Inputs that point to the same file are only downloaded once. The command exits with a non-zero status if any URL fails, so it can be used in scripts.

### URL Preprocessing
Convert any CivitAI URL format to proper download URLs:

```bash
# Standalone preprocessing
python preprocess.py --api-key your-api-key

# Preprocess specific file
python preprocess.py --file CSVs/checkpoint.csv --api-key your-api-key

# Preprocess then download
python download.py --preprocess --api-key your-api-key
```

**Supported URL Formats:**
- ✅ `https://civitai.com/api/download/models/123456` (already correct)
- ✅ `https://civitai.com/models/123456/model-name` (model page)
- ✅ `https://civitai.com/models/123456?modelVersionId=789` (version page, with or without the name slug)
- ✅ `www.civitai.com` and `civitai.green` links
- ✅ `123456` (model ID only)
- ✅ Automatic search by model name for unrecognized URLs

## 📂 Project Structure

```
CivitAI-Model-Downloader/
├── 📁 src/                    # Source code
│   ├── 📁 api/               # CivitAI API client
│   ├── 📁 config/            # Configuration management
│   ├── 📁 downloader/        # Download engine
│   ├── 📁 preprocess/        # URL preprocessing
│   └── 📁 utils/             # Model management utilities
├── 📁 tests/                 # Comprehensive test suite
├── 📁 CSVs/                  # CSV files for batch downloads
├── 🐍 download.py            # Main CLI interface
├── 🐍 preprocess.py          # Standalone URL preprocessor
├── 🐍 run_tests.py           # Test runner with coverage
├── ⚙️ config.json           # User configuration
├── 📄 requirements.txt       # Dependencies
└── 📄 requirements-test.txt  # Test dependencies
```

## 📊 CSV Format

Create CSV files in the `CSVs/` directory with this structure:

```csv
SrNo,Model_ID,Model_Name,Model_URL
1,4201,Realistic Vision V4.0,https://civitai.com/api/download/models/114367
2,12345,Another Model,https://civitai.com/models/12345/model-name
3,67890,Model with ID Only,67890
```

**Automatic CSV Generation**: Use the [CivitAI DownloadLink Extractor](https://github.com/deepratnaawale/CivitAI-DownloadLink-Extractor) to automatically generate CSV files.

## ⚙️ Configuration

The downloader creates a `config.json` file with customizable settings:

```json
{
  "api_key": "your-civitai-api-key",
  "csvs_directory": "CSVs",
  "model_paths": {
    "checkpoint": "models/Stable-diffusion",
    "lora": "models/Lora",
    "controlnet": "models/ControlNet",
    "vae": "models/VAE",
    "textualinversion": "embeddings",
    "upscaler": "models/ESRGAN"
  },
  "download_settings": {
    "max_concurrent_downloads": 4,
    "timeout_seconds": 300,
    "retry_attempts": 3,
    "chunk_size": 8192
  }
}
```

### Supported Model Types
- **checkpoint** → `models/Stable-diffusion/`
- **lora** → `models/Lora/`
- **locon** → `models/Lora/`
- **lycoris** → `models/Lora/`
- **controlnet** → `models/ControlNet/`
- **hypernetwork** → `models/hypernetworks/`
- **vae** → `models/VAE/`
- **textualinversion** → `embeddings/`
- **upscaler** → `models/ESRGAN/`
- **poses** → `models/Poses/`
- **other** → `models/Other/`

## 🧪 Testing

The project includes a comprehensive test suite with 77+ tests:

```bash
# Run all tests with coverage
python run_tests.py

# Install test dependencies and run tests
python run_tests.py --install

# Verbose output
python run_tests.py --verbose

# Direct pytest execution
python -m pytest tests/ -v --cov=src
```

**Test Coverage:**
- ✅ 96% test success rate (74/77 tests passing)
- ✅ 56% code coverage with detailed reporting
- ✅ Comprehensive mocking for external dependencies
- ✅ Async testing for HTTP operations
- ✅ Integration tests for end-to-end workflows

## 🔧 Development

### Prerequisites
- Python 3.8+
- pip or conda
- Git

### Setup Development Environment
```bash
# Clone repository
git clone https://github.com/deepratnaawale/CivitAI-Model-Downloader.git
cd CivitAI-Model-Downloader

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# Run tests
python run_tests.py
```

### Architecture Overview
- **Async Design**: Built on asyncio for maximum performance
- **Modular Structure**: Clean separation of concerns across modules  
- **Type Hints**: Full type annotation for better IDE support
- **Error Handling**: Comprehensive exception handling with detailed logging
- **Testing**: Extensive test coverage with mocking for external services

## 🚢 Deployment

### Local Installation
```bash
git clone https://github.com/deepratnaawale/CivitAI-Model-Downloader.git
cd CivitAI-Model-Downloader
pip install -r requirements.txt
python download.py --sd /path/to/stable-diffusion --api-key your-api-key
```

### RunPod/Cloud Deployment
```bash
# In Jupyter Lab terminal
git clone https://github.com/deepratnaawale/CivitAI-Model-Downloader.git
cd CivitAI-Model-Downloader
python download.py --sd /workspace/stable-diffusion-webui --api-key your-api-key
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "download.py", "--help"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes and add tests
4. Run test suite (`python run_tests.py`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [CivitAI](https://civitai.com) for the excellent model platform and API
- [Stable Diffusion](https://github.com/AUTOMATIC1111/stable-diffusion-webui) community
- Contributors and users who provide feedback and improvements

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/deepratnaawale/CivitAI-Model-Downloader/issues)
---

⭐ **Star this repository if you find it useful!**

