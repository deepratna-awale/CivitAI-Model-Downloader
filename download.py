#!/usr/bin/env python3
"""
CivitAI Model Downloader - CLI Interface
"""

import asyncio
import subprocess
import sys
import argparse
from pathlib import Path

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="CivitAI Model Downloader - Download models for Stable Diffusion",
        epilog="""
Examples:
  %(prog)s --sd /path/to/stable-diffusion --csv ./my-csvs --api-key your-api-key
  %(prog)s --sd ~/stable-diffusion-webui
  %(prog)s --api-key your-civitai-api-key
  %(prog)s --preprocess --api-key your-api-key
  %(prog)s --preprocess --csv ./my-csvs --text-files
  %(prog)s --url "https://civitai.com/models/4201/realistic-vision" --api-key your-api-key
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--sd", "--stable-diffusion",
        dest="sd_path",
        type=str,
        help="Path to Stable Diffusion installation directory"
    )
    
    parser.add_argument(
        "--csv", "--csvs-dir",
        dest="csvs_dir",
        type=str,
        help="Path to CSV files directory (default: CSVs)"
    )
    
    parser.add_argument(
        "--api-key",
        dest="api_key",
        type=str,
        help="CivitAI API key for authentication"
    )
    
    parser.add_argument(
        "--preprocess",
        action="store_true",
        help="Preprocess CSV files to convert non-download URLs to proper download URLs before downloading"
    )
    
    parser.add_argument(
        "--url",
        dest="single_url",
        type=str,
        help="Process a single URL/ID/name and display the download URL (preprocessing only)"
    )
    
    parser.add_argument(
        "--text-files",
        action="store_true",
        help="Include .txt files when preprocessing (creates CSV output)"
    )
    
    return parser.parse_args()

# Parse arguments early so we can show help even if imports fail
try:
    args = parse_arguments()
except SystemExit:
    # argparse calls sys.exit() for --help, let it through
    raise

# Now try to import required dependencies
try:
    import aiohttp
    import aiofiles
    import tqdm
    from loguru import logger
except ImportError as e:
    print(f"Error: Missing required dependency: {e}")
    print("Please install the required packages:")
    print("pip install aiohttp aiofiles tqdm loguru")
    sys.exit(1)

# Configure logging
def setup_logging():
    """Setup loguru logging to both file and stdout"""
    # Remove default handler
    logger.remove()
    
    # Add stdout handler with INFO level
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        colorize=True
    )
    
    # Add file handler with DEBUG level
    logger.add(
        "downloads.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="7 days",
        compression="zip"
    )
    
    logger.info("Logging initialized - writing to downloads.log")

# Setup logging
setup_logging()


# Import our modules
from src import ConfigManager, CivitAIApiClient, FileDownloader, ModelManager, URLPreprocessor, preprocess_urls, process_single_url


class CivitAIDownloaderCLI:
    """Command Line Interface for CivitAI Model Downloader"""
    
    def __init__(self, args=None):
        self.args = args or argparse.Namespace()
        self.config_manager = ConfigManager()
        
        # Apply CLI overrides for configuration
        if hasattr(self.args, 'csvs_dir') and self.args.csvs_dir:
            # Update the CSV directory path in config
            logger.info(f"Using CSV directory from CLI: {self.args.csvs_dir}")
            self.config_manager.set_csvs_directory(self.args.csvs_dir)
        
        # Apply API key from CLI if provided
        if hasattr(self.args, 'api_key') and self.args.api_key:
            logger.info("Using API key from CLI")
            self.config_manager.set_api_key(self.args.api_key)
        
        self.model_manager = ModelManager(self.config_manager)
    
    def setup_api_key(self):
        """Setup CivitAI API key if not configured"""
        api_key = self.config_manager.get_api_key()
        
        # If API key was provided via CLI, we're done
        if hasattr(self.args, 'api_key') and self.args.api_key:
            logger.info("API key configured via CLI")
            return
        
        if not api_key:
            logger.info("CivitAI API Key Setup")
            print("\nCivitAI API Key Setup")
            print("To download models from CivitAI, you need an API key.")
            print("1. Go to https://civitai.com/user/account")
            print("2. Create an API token")
            print("3. Copy the token and paste it below")
            
            while True:
                api_key = input("Enter your CivitAI API key (or press Enter to skip): ").strip()
                if api_key:
                    self.config_manager.set_api_key(api_key)
                    logger.success("API key saved successfully!")
                    print("API key saved successfully!")
                    break
                else:
                    logger.warning("User chose to continue without API key")
                    print("Warning: Without an API key, you may not be able to download some models.")
                    confirm = input("Continue without API key? (y/n): ").lower()
                    if confirm == 'y':
                        break
    
    def get_stable_diffusion_path(self) -> Path | None:
        """Get and validate Stable Diffusion installation path"""
        logger.info("Starting Stable Diffusion path validation")
        
        # Check if path was provided via CLI argument
        if hasattr(self.args, 'sd_path') and self.args.sd_path:
            logger.info(f"Using Stable Diffusion path from CLI: {self.args.sd_path}")
            main_path = Path(self.args.sd_path)
            
            if not main_path.exists():
                logger.error(f"CLI provided path does not exist: {main_path}")
                print(f"Error: CLI provided path does not exist: {main_path}")
                return None
            
            # Check if models folder exists (simplified validation)
            if (main_path / "models").exists():
                logger.success(f"Valid Stable Diffusion path found: {main_path}")
                print(f"Using Stable Diffusion path: {main_path}")
                return main_path
            else:
                logger.error(f"Invalid CLI path - no models folder found: {main_path}")
                print(f"Error: Invalid CLI path. The Stable Diffusion directory must contain a 'models' folder.")
                return None
        
        # Interactive path selection if no CLI argument provided
        while True:
            path_input = input("\nEnter your Stable Diffusion installation path: ").strip()
            
            if not path_input:
                logger.warning("Empty path provided by user")
                print("Please enter a valid path.")
                continue
                
            main_path = Path(path_input)
            logger.debug(f"Checking path: {main_path}")
            
            if not main_path.exists():
                logger.warning(f"Path does not exist: {main_path}")
                print("Path does not exist. Please enter a valid path.")
                continue
            
            # Check if models folder exists (simplified validation)
            if (main_path / "models").exists():
                logger.success(f"Valid Stable Diffusion path found: {main_path}")
                print("Valid Stable Diffusion path found.")
                return main_path
            else:
                logger.warning(f"Invalid path - no models folder found: {main_path}")
                print("Invalid path. The Stable Diffusion directory must contain a 'models' folder.")
                retry = input("Try again? (y/n): ").lower()
                if retry != 'y':
                    logger.info("User chose to exit path validation")
                    return None
    
    async def preprocess_csv_files(self):
        """Preprocess CSV files to resolve URLs to download URLs"""
        logger.info("Starting CSV URL preprocessing...")
        print("\n🔄 Preprocessing CSV files...")
        print("Converting non-download URLs to proper download URLs using CivitAI API")
        
        api_key = self.config_manager.get_api_key()
        csvs_dir = Path(self.config_manager.get_csvs_directory())
        
        if not api_key:
            logger.warning("No API key available for preprocessing")
            print("⚠️  Warning: No API key configured. Some protected models may not be accessible.")
            print("Consider setting an API key for better results.")
        
        try:
            results = await preprocess_urls(api_key, csvs_dir, getattr(self.args, 'text_files', False))
            
            if not results:
                logger.info("No files found to preprocess")
                print("No files found to preprocess")
                return
            
            # Display results
            total_all = 0
            success_all = 0
            failed_all = 0
            
            print(f"\n📊 Preprocessing Results:")
            for filename, (total, success, failed) in results.items():
                print(f"  {filename}:")
                print(f"    Total processed: {total}")
                print(f"    Successfully resolved: {success}")
                if failed > 0:
                    print(f"    Failed to resolve: {failed}")
                
                total_all += total
                success_all += success
                failed_all += failed
            
            print(f"\n📈 Overall Summary:")
            print(f"  Total URLs processed: {total_all}")
            print(f"  Successfully resolved: {success_all}")
            print(f"  Failed to resolve: {failed_all}")
            
            if total_all > 0:
                success_rate = (success_all / total_all) * 100
                print(f"  Success rate: {success_rate:.1f}%")
                
            logger.info(f"Preprocessing completed: {success_all}/{total_all} URLs resolved")
            
        except Exception as e:
            logger.error(f"Error during preprocessing: {e}")
            print(f"❌ Error during preprocessing: {e}")
            raise
    
    async def process_single_url(self):
        """Process a single URL and display the result"""
        logger.info("Processing single URL...")
        print("\n🔗 Processing single URL...")
        
        url = self.args.single_url
        api_key = self.config_manager.get_api_key()
        
        print(f"Input: {url}")
        
        try:
            success, result, metadata = await process_single_url(url, api_key)
            
            if success:
                print(f"\n✅ Successfully resolved!")
                print(f"📥 Download URL: {result}")
                
                if metadata:
                    print(f"\n📋 Model Information:")
                    for key, value in metadata.items():
                        if key != 'download_url':  # Already shown above
                            print(f"   {key.replace('_', ' ').title()}: {value}")
                
                logger.success(f"Successfully processed URL: {url}")
            else:
                print(f"\n❌ Failed to resolve: {result}")
                logger.error(f"Failed to process URL: {url} - {result}")
                
        except Exception as e:
            logger.error(f"Error processing single URL: {e}")
            print(f"❌ Error processing URL: {e}")
            raise
    
    async def resolve_missing_urls(self, missing_url_tasks, model_type):
        """Resolve missing URLs using CivitAI API"""
        api_key = self.config_manager.get_api_key()
        resolved_tasks = []
        
        if not api_key:
            logger.warning("API key required to resolve missing URLs")
            print("API key required to resolve missing URLs")
            return resolved_tasks
        
        logger.info(f"Resolving {len(missing_url_tasks)} missing URLs for {model_type}")
        async with CivitAIApiClient(api_key) as api_client:
            for model_id, model_name, file_path in missing_url_tasks:
                try:
                    logger.debug(f"Searching for model: {model_name} (ID: {model_id})")
                    print(f"  Searching for: {model_name}")
                    download_url = await api_client.find_download_url(
                        model_name, model_id, model_type
                    )
                    
                    if download_url:
                        resolved_tasks.append((download_url, file_path))
                        logger.success(f"Found download URL for {model_name}")
                        print(f"    ✓ Found download URL")
                    else:
                        logger.warning(f"Could not find download URL for {model_name}")
                        print(f"    ✗ Could not find download URL")
                
                except Exception as e:
                    logger.error(f"Error resolving URL for {model_name}: {e}")
                    print(f"    ✗ Error: {e}")
        
        logger.info(f"Resolved {len(resolved_tasks)} out of {len(missing_url_tasks)} URLs")
        return resolved_tasks
    
    async def download_model_type(self, model_type: str, main_path: Path) -> tuple:
        """Download models of a specific type"""
        logger.info(f"Processing {model_type.capitalize()} files...")
        print(f"\nProcessing {model_type.capitalize()} files...")
        
        # Prepare download tasks (with URL resolution for missing URLs)
        download_tasks = self.model_manager.prepare_download_tasks(
            model_type, 
            main_path, 
            self.resolve_missing_urls
        )
        
        if not download_tasks:
            logger.info(f"No files to download for {model_type}")
            print(f"No files to download for {model_type}")
            return 0, 0
        
        logger.info(f"Prepared {len(download_tasks)} download tasks for {model_type}")
        
        # Download files with progress tracking
        api_key = self.config_manager.get_api_key()
        download_settings = self.config_manager.get_download_settings()
        max_concurrent = download_settings.get("max_concurrent_downloads", 4)
        
        print(f"📊 Downloading {len(download_tasks)} {model_type} files (max {max_concurrent} concurrent)")
        
        async with FileDownloader(api_key, download_settings) as downloader:
            results = await downloader.download_files(
                download_tasks, 
                f"{model_type.title()} Models"
            )
        
        # Count results with better categorization
        downloaded = sum(1 for success, message in results if success and "Skipped" not in message)
        skipped = sum(1 for success, message in results if success and "Skipped" in message)
        failed = sum(1 for success, _ in results if not success)
        
        logger.info(f"{model_type} download completed: {downloaded} downloaded, {skipped} skipped, {failed} failed")
        print(f"{model_type.capitalize()} Summary:")
        print(f"  Downloaded: {downloaded}")
        print(f"  Skipped (already exist): {skipped}")
        print(f"  Failed: {failed}")
        
        # Show failed downloads
        if failed > 0:
            logger.warning(f"Failed downloads for {model_type}:")
            print("Failed downloads:")
            for success, message in results:
                if not success:
                    logger.error(f"Failed download: {message}")
                    print(f"  - {message}")
        
        return downloaded, failed
    
    async def run(self):
        """Main CLI execution"""
        logger.info("Starting CivitAI Model Downloader")
        print("CivitAI Model Downloader")
        print("=" * 40)
        
        # Setup API key
        self.setup_api_key()
        
        # Handle single URL processing
        if hasattr(self.args, 'single_url') and self.args.single_url:
            await self.process_single_url()
            return
        
        # Handle preprocessing if requested
        if hasattr(self.args, 'preprocess') and self.args.preprocess:
            await self.preprocess_csv_files()
            print("\n✅ Preprocessing completed! You can now run the downloader normally.")
            input("Press Enter to continue with downloads or Ctrl+C to exit...")
        
        # Get available model types
        models = self.model_manager.get_available_model_types()
        logger.info(f"Found model types: {models}")
        
        if not models:
            csvs_dir = self.config_manager.get_csvs_directory()
            logger.error(f"No model CSV files found in {csvs_dir} directory!")
            print(f"No model CSV files found in {csvs_dir} directory!")
            input("Press Enter to exit...")
            return
        
        # Get Stable Diffusion path
        main_path = self.get_stable_diffusion_path()
        if not main_path:
            logger.error("Failed to get valid Stable Diffusion path")
            input("Please rerun the script.\nPress Return to exit.")
            return
        
        logger.info(f"Using Stable Diffusion path: {main_path}")
        
        # Download models
        total_downloaded = 0
        total_failed = 0
        
        logger.info(f"Starting downloads for {len(models)} model types")
        for model_type in models:
            try:
                downloaded, failed = await self.download_model_type(model_type, main_path)
                total_downloaded += downloaded
                total_failed += failed
                
            except Exception as e:
                logger.error(f"Error downloading {model_type}: {e}")
                print(f"Error downloading {model_type}: {e}")
                total_failed += 1
        
        # Final summary
        logger.info(f"Download session completed: {total_downloaded} downloaded, {total_failed} failed")
        print(f"\nDownload Summary")
        print(f"Total Downloaded: {total_downloaded}")
        print(f"Total Failed: {total_failed}")
        
        if self.config_manager.get_download_settings().get("skip_existing_files", True):
            print("Note: Files that already existed were automatically skipped")
        
        input("\nPress Enter to exit...")


async def main():
    """Main entry point"""
    cli = CivitAIDownloaderCLI(args)
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())
