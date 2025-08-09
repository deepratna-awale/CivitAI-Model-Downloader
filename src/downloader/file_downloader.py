"""
Async file downloader with retry logic and progress tracking
"""

import asyncio
import aiofiles
import aiohttp
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from tqdm.asyncio import tqdm
from loguru import logger
import threading


class ProgressManager:
    """Manages multiple concurrent progress bars"""
    
    def __init__(self, max_concurrent: int):
        self.max_concurrent = max_concurrent
        self.active_downloads = {}
        self.next_position = 1
        self.lock = threading.Lock()
        self.overall_pbar = None  # type: Optional[tqdm]
    
    def create_file_progress(self, file_id: str, filename: str, total_size: int) -> tqdm:
        """Create a progress bar for a specific file"""
        with self.lock:
            position = self.next_position
            self.next_position += 1
            
            if total_size > 0:
                pbar = tqdm(
                    total=total_size,
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=f"📥 {filename[:35]}",
                    position=position,
                    leave=False,
                    bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
                )
            else:
                pbar = tqdm(
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=f"📥 {filename[:35]}",
                    position=position,
                    leave=False,
                    bar_format="{desc}: {n_fmt} [{elapsed}, {rate_fmt}]"
                )
            
            self.active_downloads[file_id] = pbar
            return pbar
    
    def remove_file_progress(self, file_id: str):
        """Remove a file's progress bar"""
        with self.lock:
            if file_id in self.active_downloads:
                self.active_downloads[file_id].close()
                del self.active_downloads[file_id]
    
    def cleanup(self):
        """Clean up all progress bars"""
        with self.lock:
            for pbar in self.active_downloads.values():
                pbar.close()
            self.active_downloads.clear()
            if self.overall_pbar:
                self.overall_pbar.close()


class FileDownloader:
    """Handles async file downloads with retry logic"""
    
    def __init__(self, api_key: Optional[str] = None, download_settings: Optional[Dict] = None):
        self.api_key = api_key
        self.download_settings = download_settings or {
            "max_concurrent_downloads": 4,
            "timeout": 30,
            "retry_attempts": 3
        }
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=self.download_settings.get("timeout", 30))
        connector = aiohttp.TCPConnector(limit=self.download_settings.get("max_concurrent_downloads", 4))
        
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers=headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def add_api_key_to_url(self, url: str) -> str:
        """Add API key to URL if not using headers"""
        if not self.api_key:
            return url
        
        if "?" in url:
            return f"{url}&token={self.api_key}"
        else:
            return f"{url}?token={self.api_key}"
    
    async def download_file(self, url: str, file_path: Path, semaphore: asyncio.Semaphore, 
                          progress_manager: ProgressManager) -> Tuple[bool, str]:
        """Download a single file with retry logic and progress tracking"""
        file_id = f"{file_path.name}_{id(asyncio.current_task())}"
        
        # Check if file already exists (if skip_existing_files is enabled)
        skip_existing = self.download_settings.get("skip_existing_files", True)
        if skip_existing and file_path.exists():
            logger.info(f"File already exists, skipping: {file_path.name}")
            return True, f"Skipped (already exists): {file_path.name}"
        
        async with semaphore:
            logger.debug(f"Starting download: {file_path.name}")
            for attempt in range(self.download_settings.get("retry_attempts", 3)):
                try:
                    download_url = url if self.api_key else self.add_api_key_to_url(url)
                    
                    async with self.session.get(download_url) as response: # type: ignore
                        if response.status == 200:
                            file_path.parent.mkdir(parents=True, exist_ok=True)
                            
                            # Get filename from Content-Disposition header if available
                            content_disposition = response.headers.get('content-disposition', '')
                            if 'filename=' in content_disposition:
                                filename = content_disposition.split('filename=')[1].strip('"')
                                final_file_path = file_path.parent / filename
                                
                                # Check again with the actual filename from server (if skip_existing is enabled)
                                if skip_existing and final_file_path.exists():
                                    logger.info(f"File already exists with server filename, skipping: {final_file_path.name}")
                                    return True, f"Skipped (already exists): {final_file_path.name}"
                                
                                file_path = final_file_path
                            
                            async with aiofiles.open(file_path, 'wb') as f:
                                total_size = int(response.headers.get('content-length', 0))
                                logger.debug(f"Downloading {file_path.name} ({total_size} bytes)")
                                
                                # Create progress bar using the progress manager
                                progress = progress_manager.create_file_progress(
                                    file_id, file_path.name, total_size
                                )
                                
                                try:
                                    downloaded = 0
                                    async for chunk in response.content.iter_chunked(8192):
                                        await f.write(chunk)
                                        downloaded += len(chunk)
                                        progress.update(len(chunk))
                                finally:
                                    progress_manager.remove_file_progress(file_id)
                            
                            logger.success(f"Successfully downloaded: {file_path.name}")
                            return True, f"Downloaded: {file_path.name}"
                        
                        elif response.status == 401:
                            return False, f"Authentication failed for {url}. Check your API key."
                        
                        elif response.status == 404:
                            return False, f"File not found: {url}"
                        
                        else:
                            error_msg = f"HTTP {response.status} for {url}"
                            if attempt == self.download_settings.get("retry_attempts", 3) - 1:
                                return False, error_msg
                
                except asyncio.TimeoutError:
                    error_msg = f"Timeout downloading {url}"
                    if attempt == self.download_settings.get("retry_attempts", 3) - 1:
                        return False, error_msg
                
                except Exception as e:
                    error_msg = f"Error downloading {url}: {str(e)}"
                    if attempt == self.download_settings.get("retry_attempts", 3) - 1:
                        return False, error_msg
                
                if attempt < self.download_settings.get("retry_attempts", 3) - 1:
                    await asyncio.sleep(2 ** attempt)
        
        return False, "Max retries exceeded"
    
    async def download_files(self, download_tasks: List[Tuple[str, Path]], 
                           progress_desc: str = "Downloading") -> List[Tuple[bool, str]]:
        """Download multiple files with concurrent progress tracking"""
        if not download_tasks:
            return []
        
        logger.info(f"Starting batch download of {len(download_tasks)} files")
        max_concurrent = self.download_settings.get("max_concurrent_downloads", 4)
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # Create progress manager for concurrent downloads
        progress_manager = ProgressManager(max_concurrent)
        
        print(f"Starting download of {len(download_tasks)} files (max {max_concurrent} concurrent)...")
        
        try:
            # Create download tasks with progress manager
            tasks = []
            for url, file_path in download_tasks:
                task = self.download_file(url, file_path, semaphore, progress_manager)
                tasks.append(task)
            
            # Execute downloads with overall progress bar
            results = []
            successful_count = 0
            failed_count = 0
            skipped_count = 0
            
            # Enhanced overall progress bar
            progress_manager.overall_pbar = tqdm(
                total=len(tasks), 
                desc=f"🔄 {progress_desc}",
                unit="files",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}] {postfix}",
                position=0
            )
            
            for coro in asyncio.as_completed(tasks):
                result = await coro
                results.append(result)
                
                # Update counters based on result
                if result[0]:  # Success
                    if "Skipped" in result[1]:
                        skipped_count += 1
                    else:
                        successful_count += 1
                else:  # Failed
                    failed_count += 1
                
                # Update overall progress bar with current stats
                progress_manager.overall_pbar.set_postfix_str(f"✅{successful_count} ⏭️{skipped_count} ❌{failed_count}")
                progress_manager.overall_pbar.update(1)
        
        finally:
            # Clean up all progress bars
            progress_manager.cleanup()
        
        successful = sum(1 for success, message in results if success and "Skipped" not in message)
        skipped = sum(1 for success, message in results if success and "Skipped" in message)
        failed = sum(1 for success, _ in results if not success)
        logger.info(f"Batch download completed: {successful} downloaded, {skipped} skipped, {failed} failed")
        
        return results
