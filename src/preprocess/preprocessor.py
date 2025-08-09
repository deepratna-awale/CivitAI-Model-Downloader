"""
Preprocessing module for CivitAI Model Downloader
Converts non-download URLs to proper download URLs using CivitAI API
"""

import re
import csv
import asyncio
import aiohttp
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Any
from urllib.parse import urlparse, parse_qs
from loguru import logger


class URLPreprocessor:
    """Preprocesses URLs in CSV files to ensure they are valid download URLs"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://civitai.com/api/v1"
        
        # URL patterns for different CivitAI URL types
        self.url_patterns = {
            'download_url': re.compile(r'https://civitai\.com/api/download/models/(\d+)'),
            'model_page': re.compile(r'https://civitai\.com/models/(\d+)'),
            'model_version_page': re.compile(r'https://civitai\.com/models/(\d+)/.*\?modelVersionId=(\d+)'),
            'model_id_only': re.compile(r'^(\d+)$'),
            'short_url': re.compile(r'https://civitai\.com/models/(\d+)/?$'),
        }
    
    def identify_url_type(self, url: str) -> Tuple[str, Dict[str, str]]:
        """
        Identify the type of URL and extract relevant IDs
        
        Returns:
            Tuple of (url_type, extracted_data)
        """
        url = url.strip()
        
        # Check for download URL (already correct format)
        match = self.url_patterns['download_url'].match(url)
        if match:
            return 'download_url', {'model_version_id': match.group(1)}
        
        # Check for model version page with modelVersionId parameter
        match = self.url_patterns['model_version_page'].match(url)
        if match:
            return 'model_version_page', {
                'model_id': match.group(1),
                'model_version_id': match.group(2)
            }
        
        # Check for general model page
        match = self.url_patterns['model_page'].match(url)
        if match:
            return 'model_page', {'model_id': match.group(1)}
        
        # Check for short URL format
        match = self.url_patterns['short_url'].match(url)
        if match:
            return 'model_page', {'model_id': match.group(1)}
        
        # Check for just a model ID
        match = self.url_patterns['model_id_only'].match(url)
        if match:
            return 'model_id_only', {'model_id': match.group(1)}
        
        # Try to extract from query parameters
        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            
            if 'modelVersionId' in query_params:
                return 'query_version_id', {'model_version_id': query_params['modelVersionId'][0]}
            elif 'modelId' in query_params:
                return 'query_model_id', {'model_id': query_params['modelId'][0]}
        except Exception:
            pass
        
        return 'unknown', {'original_url': url}
    
    async def get_model_info(self, session: aiohttp.ClientSession, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model information from CivitAI API"""
        url = f"{self.base_url}/models/{model_id}"
        headers = {}
        
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Retrieved model info for ID {model_id}")
                    return data
                else:
                    logger.warning(f"Failed to get model info for ID {model_id}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting model info for ID {model_id}: {e}")
            return None
    
    async def get_model_version_info(self, session: aiohttp.ClientSession, version_id: str) -> Optional[Dict[str, Any]]:
        """Get model version information from CivitAI API"""
        url = f"{self.base_url}/model-versions/{version_id}"
        headers = {}
        
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Retrieved model version info for ID {version_id}")
                    return data
                else:
                    logger.warning(f"Failed to get model version info for ID {version_id}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting model version info for ID {version_id}: {e}")
            return None
    
    async def search_models(self, session: aiohttp.ClientSession, query: str) -> Optional[List[Dict[str, Any]]]:
        """Search for models by name"""
        url = f"{self.base_url}/models"
        params = {
            'query': query,
            'limit': 10,
            'primaryFileOnly': True
        }
        headers = {}
        
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        try:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Search found {len(data.get('items', []))} models for query: {query}")
                    return data.get('items', [])
                else:
                    logger.warning(f"Failed to search models for query '{query}': {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error searching models for query '{query}': {e}")
            return None
    
    def get_best_download_url(self, model_data: Dict[str, Any], preferred_version_id: Optional[str] = None) -> Optional[str]:
        """Extract the best download URL from model data"""
        model_versions = model_data.get('modelVersions', [])
        
        if not model_versions:
            logger.warning("No model versions found in model data")
            return None
        
        # If a specific version is requested, try to find it
        if preferred_version_id:
            for version in model_versions:
                if str(version.get('id')) == str(preferred_version_id):
                    download_url = version.get('downloadUrl')
                    if download_url:
                        logger.debug(f"Found download URL for specific version {preferred_version_id}")
                        return download_url
        
        # Otherwise, use the first version (usually the latest)
        first_version = model_versions[0]
        download_url = first_version.get('downloadUrl')
        
        if download_url:
            logger.debug(f"Using download URL from first version: {first_version.get('id')}")
            return download_url
        
        logger.warning("No download URL found in model versions")
        return None
    
    async def resolve_url(self, session: aiohttp.ClientSession, url: str, model_name: str = "") -> Tuple[bool, str]:
        """
        Resolve a URL to a proper download URL
        
        Returns:
            Tuple of (success, download_url_or_error_message)
        """
        url_type, data = self.identify_url_type(url)
        
        logger.debug(f"Processing URL type '{url_type}' for: {url}")
        
        # If it's already a download URL, return as-is
        if url_type == 'download_url':
            logger.debug(f"URL is already a download URL: {url}")
            return True, url
        
        # Handle model version ID directly
        if url_type in ['model_version_page', 'query_version_id'] and 'model_version_id' in data:
            version_id = data['model_version_id']
            version_info = await self.get_model_version_info(session, version_id)
            
            if version_info:
                download_url = version_info.get('downloadUrl')
                if download_url:
                    logger.success(f"Resolved version ID {version_id} to download URL")
                    return True, download_url
                else:
                    logger.warning(f"No download URL found for version ID {version_id}")
            else:
                logger.error(f"Could not fetch version info for ID {version_id}")
        
        # Handle model ID
        if url_type in ['model_page', 'model_id_only', 'query_model_id'] and 'model_id' in data:
            model_id = data['model_id']
            model_info = await self.get_model_info(session, model_id)
            
            if model_info:
                # Extract preferred version if available
                preferred_version = data.get('model_version_id')
                download_url = self.get_best_download_url(model_info, preferred_version)
                
                if download_url:
                    logger.success(f"Resolved model ID {model_id} to download URL")
                    return True, download_url
                else:
                    logger.warning(f"No download URL found for model ID {model_id}")
            else:
                logger.error(f"Could not fetch model info for ID {model_id}")
        
        # If we have a model name, try searching
        if model_name and url_type == 'unknown':
            logger.info(f"Attempting to search for model by name: {model_name}")
            search_results = await self.search_models(session, model_name)
            
            if search_results and len(search_results) > 0:
                # Use the first (most relevant) result
                first_result = search_results[0]
                download_url = self.get_best_download_url(first_result)
                
                if download_url:
                    logger.success(f"Found download URL via search for '{model_name}'")
                    return True, download_url
        
        # If all else fails
        error_msg = f"Could not resolve URL to download link: {url}"
        logger.error(error_msg)
        return False, error_msg
    
    async def process_csv_file(self, csv_path: Path, output_path: Optional[Path] = None) -> Tuple[int, int, int]:
        """
        Process a CSV file and resolve all URLs to download URLs
        
        Returns:
            Tuple of (total_processed, successfully_resolved, failed_to_resolve)
        """
        if not csv_path.exists():
            logger.error(f"CSV file not found: {csv_path}")
            return 0, 0, 0
        
        if output_path is None:
            output_path = csv_path
        
        logger.info(f"Processing CSV file: {csv_path}")
        
        # Read the CSV file
        rows = []
        headers = None
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                rows = list(reader)
        except Exception as e:
            logger.error(f"Error reading CSV file {csv_path}: {e}")
            return 0, 0, 0
        
        if not headers or not rows:
            logger.warning(f"CSV file is empty or has no data: {csv_path}")
            return 0, 0, 0
        
        logger.info(f"Found {len(rows)} rows to process")
        
        total_processed = 0
        successfully_resolved = 0
        failed_to_resolve = 0
        
        # Process URLs asynchronously
        async with aiohttp.ClientSession() as session:
            for i, row in enumerate(rows):
                if len(row) < 4:  # Need at least: SrNo, Model_ID, Model_Name, Model_URL
                    logger.warning(f"Row {i+1} has insufficient columns, skipping")
                    continue
                
                total_processed += 1
                sr_no, model_id, model_name, model_url = row[:4]
                
                logger.debug(f"Processing row {i+1}: {model_name} - {model_url}")
                
                success, result = await self.resolve_url(session, model_url, model_name)
                
                if success:
                    # Update the URL in the row
                    row[3] = result  # Update Model_URL column
                    successfully_resolved += 1
                    logger.info(f"✓ Resolved: {model_name}")
                else:
                    failed_to_resolve += 1
                    logger.warning(f"✗ Failed: {model_name} - {result}")
        
        # Write the updated CSV
        try:
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)
            
            logger.success(f"Updated CSV saved to: {output_path}")
        except Exception as e:
            logger.error(f"Error writing updated CSV to {output_path}: {e}")
        
        return total_processed, successfully_resolved, failed_to_resolve
        
    async def process_text_file(self, text_path: Path, output_path: Optional[Path] = None) -> Tuple[int, int, int]:
        """
        Process a text file containing mixed URLs/IDs/names and convert to CSV format
        
        Args:
            text_path: Path to text file containing URLs/IDs/names (one per line)
            output_path: Optional output path for CSV file
        
        Returns:
            Tuple of (total_processed, successfully_resolved, failed_to_resolve)
        """
        if not text_path.exists():
            logger.error(f"Text file not found: {text_path}")
            return 0, 0, 0
        
        if output_path is None:
            # Generate CSV filename from text file name
            output_path = text_path.with_suffix('.csv')
        
        logger.info(f"Processing text file: {text_path}")
        
        # Read the text file
        lines = []
        try:
            with open(text_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
        except Exception as e:
            logger.error(f"Error reading text file {text_path}: {e}")
            return 0, 0, 0
        
        if not lines:
            logger.warning(f"Text file is empty: {text_path}")
            return 0, 0, 0
        
        logger.info(f"Found {len(lines)} entries to process")
        
        total_processed = 0
        successfully_resolved = 0
        failed_to_resolve = 0
        
        # Prepare CSV data
        csv_rows = []
        
        # Process each line asynchronously
        async with aiohttp.ClientSession() as session:
            for i, line in enumerate(lines):
                if not line:
                    continue
                
                total_processed += 1
                
                logger.debug(f"Processing line {i+1}: {line}")
                
                # Try to resolve the URL/ID/name
                success, result = await self.resolve_url(session, line, line)
                
                if success:
                    # Extract model name if possible
                    model_name = await self.extract_model_name(session, result, line)
                    
                    # Create CSV row: SrNo, Model_ID, Model_Name, Model_URL
                    csv_row = [
                        str(i + 1),  # SrNo
                        self.extract_model_id_from_url(result) or "Unknown",  # Model_ID
                        model_name or f"Model_{i+1}",  # Model_Name
                        result  # Model_URL (download URL)
                    ]
                    csv_rows.append(csv_row)
                    successfully_resolved += 1
                    logger.info(f"✓ Resolved: {line}")
                else:
                    # Add failed entry with original data
                    csv_row = [
                        str(i + 1),  # SrNo
                        "Failed",  # Model_ID
                        line,  # Model_Name (use original input)
                        line  # Model_URL (keep original for manual review)
                    ]
                    csv_rows.append(csv_row)
                    failed_to_resolve += 1
                    logger.warning(f"✗ Failed: {line} - {result}")
        
        # Write the CSV file
        try:
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow(['SrNo', 'Model_ID', 'Model_Name', 'Model_URL'])
                # Write data rows
                writer.writerows(csv_rows)
            
            logger.success(f"CSV file created: {output_path}")
        except Exception as e:
            logger.error(f"Error writing CSV to {output_path}: {e}")
        
        return total_processed, successfully_resolved, failed_to_resolve
    
    def extract_model_id_from_url(self, url: str) -> Optional[str]:
        """Extract model ID from a download URL"""
        match = self.url_patterns['download_url'].match(url)
        if match:
            return match.group(1)
        return None
    
    async def extract_model_name(self, session: aiohttp.ClientSession, download_url: str, original_input: str) -> Optional[str]:
        """Try to extract model name from download URL or return original input"""
        # If original input looks like a name (not URL or ID), use it
        if not (original_input.startswith('http') or original_input.isdigit()):
            return original_input
        
        # Try to get model name from API using the download URL
        model_id = self.extract_model_id_from_url(download_url)
        if model_id:
            model_info = await self.get_model_info(session, model_id)
            if model_info:
                return model_info.get('name', f"Model_{model_id}")
        
        return None
        """
        Process all CSV files in a directory
        
        Returns:
            Dict mapping filename to (total_processed, successfully_resolved, failed_to_resolve)
        """
        if not csv_dir.exists():
            logger.error(f"CSV directory not found: {csv_dir}")
            return {}
        
        csv_files = list(csv_dir.glob("*.csv"))
        if not csv_files:
            logger.warning(f"No CSV files found in directory: {csv_dir}")
            return {}
        
        logger.info(f"Found {len(csv_files)} CSV files to process")
        
        results = {}
        for csv_file in csv_files:
            if csv_file.name.lower() in ['template.csv', '_csv files go here.txt']:
                logger.info(f"Skipping template file: {csv_file.name}")
                continue
            
            logger.info(f"Processing: {csv_file.name}")
            result = await self.process_csv_file(csv_file)
            results[csv_file.name] = result
        
        return results


        return None


    async def process_directory(self, csv_dir: Path) -> Dict[str, Tuple[int, int, int]]:
        """
        Process all CSV files in a directory
        
        Returns:
            Dict mapping filename to (total_processed, successfully_resolved, failed_to_resolve)
        """
        if not csv_dir.exists():
            logger.error(f"CSV directory not found: {csv_dir}")
            return {}
        
        csv_files = list(csv_dir.glob("*.csv"))
        if not csv_files:
            logger.warning(f"No CSV files found in directory: {csv_dir}")
            return {}
        
        logger.info(f"Found {len(csv_files)} CSV files to process")
        
        results = {}
        for csv_file in csv_files:
            if csv_file.name.lower() in ['template.csv', '_csv files go here.txt']:
                logger.info(f"Skipping template file: {csv_file.name}")
                continue
            
            logger.info(f"Processing: {csv_file.name}")
            result = await self.process_csv_file(csv_file)
            results[csv_file.name] = result
        
        return results
    
    async def process_mixed_directory(self, input_dir: Path) -> Dict[str, Tuple[int, int, int]]:
        """
        Process all CSV and text files in a directory
        
        Returns:
            Dict mapping filename to (total_processed, successfully_resolved, failed_to_resolve)
        """
        if not input_dir.exists():
            logger.error(f"Input directory not found: {input_dir}")
            return {}
        
        # Find CSV and text files
        csv_files = list(input_dir.glob("*.csv"))
        txt_files = list(input_dir.glob("*.txt"))
        
        if not csv_files and not txt_files:
            logger.warning(f"No CSV or text files found in directory: {input_dir}")
            return {}
        
        logger.info(f"Found {len(csv_files)} CSV files and {len(txt_files)} text files to process")
        
        results = {}
        
        # Process CSV files
        for csv_file in csv_files:
            if csv_file.name.lower() in ['template.csv', '_csv files go here.txt']:
                logger.info(f"Skipping template file: {csv_file.name}")
                continue
            
            logger.info(f"Processing CSV: {csv_file.name}")
            result = await self.process_csv_file(csv_file)
            results[csv_file.name] = result
        
        # Process text files
        for txt_file in txt_files:
            if txt_file.name.lower() in ['_csv files go here.txt']:
                logger.info(f"Skipping info file: {txt_file.name}")
                continue
            
            logger.info(f"Processing text file: {txt_file.name}")
            result = await self.process_text_file(txt_file)
            results[f"{txt_file.name} -> {txt_file.stem}.csv"] = result
        
        return results


async def process_single_url(url: str, api_key: Optional[str] = None) -> Tuple[bool, str, Dict[str, str]]:
    """
    Process a single URL and return download URL with metadata
    
    Args:
        url: The URL/ID/name to process
        api_key: CivitAI API key for authentication
    
    Returns:
        Tuple of (success, download_url_or_error, metadata_dict)
    """
    preprocessor = URLPreprocessor(api_key)
    
    async with aiohttp.ClientSession() as session:
        success, result = await preprocessor.resolve_url(session, url, url)
        
        metadata = {}
        if success:
            # Try to get additional metadata
            model_id = preprocessor.extract_model_id_from_url(result)
            if model_id:
                model_info = await preprocessor.get_model_info(session, model_id)
                if model_info:
                    metadata = {
                        'model_id': model_id,
                        'model_name': model_info.get('name', 'Unknown'),
                        'model_type': model_info.get('type', 'Unknown'),
                        'creator': model_info.get('creator', {}).get('username', 'Unknown'),
                        'download_url': result
                    }
        
        return success, result, metadata


async def preprocess_urls(api_key: Optional[str] = None, csv_dir: Optional[Path] = None, include_text_files: bool = True) -> Dict[str, Tuple[int, int, int]]:
    """
    Main function to preprocess URLs in CSV files and optionally text files
    
    Args:
        api_key: CivitAI API key for authentication
        csv_dir: Directory containing CSV/text files (defaults to CSVs)
        include_text_files: Whether to process .txt files as well
    
    Returns:
        Dict mapping filename to processing results
    """
    if csv_dir is None:
        csv_dir = Path.cwd() / "CSVs"
    
    preprocessor = URLPreprocessor(api_key)
    
    if include_text_files:
        return await preprocessor.process_mixed_directory(csv_dir)
    else:
        return await preprocessor.process_directory(csv_dir)


if __name__ == "__main__":
    # Example usage
    import sys
    
    async def main():
        # You can provide an API key as a command line argument
        api_key = sys.argv[1] if len(sys.argv) > 1 else None
        
        if not api_key:
            print("Warning: No API key provided. Some protected models may not be accessible.")
            print("Usage: python preprocess.py [API_KEY]")
        
        results = await preprocess_urls(api_key)
        
        print("\n=== URL Preprocessing Results ===")
        total_all = 0
        success_all = 0
        failed_all = 0
        
        for filename, (total, success, failed) in results.items():
            print(f"\n{filename}:")
            print(f"  Total processed: {total}")
            print(f"  Successfully resolved: {success}")
            print(f"  Failed to resolve: {failed}")
            
            total_all += total
            success_all += success
            failed_all += failed
        
        print(f"\n=== Overall Summary ===")
        print(f"Total URLs processed: {total_all}")
        print(f"Successfully resolved: {success_all}")
        print(f"Failed to resolve: {failed_all}")
        
        if total_all > 0:
            success_rate = (success_all / total_all) * 100
            print(f"Success rate: {success_rate:.1f}%")
    
    asyncio.run(main())
