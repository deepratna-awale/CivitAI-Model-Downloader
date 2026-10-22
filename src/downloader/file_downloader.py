"""
Async file downloader with retry logic and progress tracking
"""

import asyncio
import hashlib
import re
import aiofiles
import aiohttp
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from urllib.parse import unquote
from tqdm.asyncio import tqdm
from loguru import logger
import threading

from ..config.urls import to_civitai_host


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
        # No total limit: large models take far longer than the timeout to download.
        # The timeout instead applies to connecting and to each read stalling.
        timeout_seconds = self.download_settings.get("timeout", 30)
        timeout = aiohttp.ClientTimeout(total=None, sock_connect=timeout_seconds, sock_read=timeout_seconds)
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
    
    @staticmethod
    def filename_from_content_disposition(content_disposition: str) -> Optional[str]:
        """Extract a safe file name from a Content-Disposition header"""
        match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', content_disposition, re.IGNORECASE)
        if not match:
            return None
        name = Path(unquote(match.group(1).strip())).name
        return name or None
    
    @staticmethod
    def sha256_of(file_path: Path) -> str:
        """Compute a file's SHA256 hash"""
        digest = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(1024 * 1024), b''):
                digest.update(block)
        return digest.hexdigest().upper()
    
    async def check_existing_file(self, file_path: Path, expected_size: Optional[int],
                                  expected_sha256: Optional[str]) -> Optional[str]:
        """
        Decide whether an existing file is complete
        
        Returns a skip message if the file is complete, or None if it must be
        (re)downloaded. Files whose expected size is unknown are not judged here.
        """
        actual_size = file_path.stat().st_size
        if expected_size is not None and actual_size != expected_size:
            logger.warning(f"{file_path.name} is {actual_size} bytes but should be {expected_size}, re-downloading")
            return None
        
        if expected_sha256 and self.download_settings.get("verify_hash", False):
            actual_sha256 = await asyncio.to_thread(self.sha256_of, file_path)
            if actual_sha256 != expected_sha256.upper():
                logger.warning(f"{file_path.name} hash does not match CivitAI's, re-downloading")
                return None
        
        logger.info(f"File already exists and is complete, skipping: {file_path.name}")
        return f"Skipped (already exists): {file_path.name}"
    
    async def download_file(self, url: str, file_path: Path, semaphore: asyncio.Semaphore, 
                          progress_manager: ProgressManager,
                          expected: Optional[Dict] = None) -> Tuple[bool, str]:
        """
        Download a single file with retry logic, resume support and progress tracking
        
        Data is written to "<name>.part" and only renamed once the size (and,
        with verify_hash, the SHA256) matches, so an interrupted download is
        resumed next time instead of being mistaken for a finished file.
        
        Args:
            expected: Optional {"size": bytes, "sha256": hex} from CivitAI metadata
        """
        file_id = f"{file_path.name}_{id(asyncio.current_task())}"
        expected = expected or {}
        expected_size = expected.get("size")
        expected_sha256 = expected.get("sha256")
        retry_attempts = self.download_settings.get("retry_attempts", 3)
        
        # Check if file already exists (if skip_existing_files is enabled)
        skip_existing = self.download_settings.get("skip_existing_files", True)
        checked_path = None
        if skip_existing and file_path.exists() and expected_size is not None:
            checked_path = file_path
            skip_message = await self.check_existing_file(file_path, expected_size, expected_sha256)
            if skip_message:
                return True, skip_message
        
        async with semaphore:
            logger.debug(f"Starting download: {file_path.name}")
            for attempt in range(retry_attempts):
                try:
                    request_url = to_civitai_host(url)
                    download_url = request_url if self.api_key else self.add_api_key_to_url(request_url)
                    
                    # Resolve the final file name before deciding whether to resume
                    async with self.session.get(download_url) as response: # type: ignore
                        if response.status == 401:
                            return False, f"Authentication failed for {url}. Check your API key."
                        if response.status == 404:
                            return False, f"File not found: {url}"
                        if response.status != 200:
                            raise aiohttp.ClientResponseError(
                                response.request_info, response.history,
                                status=response.status, message=f"HTTP {response.status} for {url}"
                            )
                        
                        server_name = self.filename_from_content_disposition(
                            response.headers.get('content-disposition', '')
                        )
                        if server_name:
                            file_path = file_path.parent / server_name
                        
                        total_size = response.content_length
                        if expected_size is None and total_size:
                            expected_size = total_size
                        
                        # Now that the real name and size are known, check for a finished file
                        if skip_existing and file_path.exists() and file_path != checked_path:
                            skip_message = await self.check_existing_file(file_path, expected_size, expected_sha256)
                            if skip_message:
                                return True, skip_message
                        
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        part_path = file_path.with_name(file_path.name + ".part")
                        resume_from = part_path.stat().st_size if part_path.exists() else 0
                        if expected_size is not None and resume_from > expected_size:
                            resume_from = 0
                        
                        if resume_from == 0:
                            await self._write_body(response, part_path, 'wb', 0, expected_size,
                                                   file_id, file_path.name, progress_manager)
                    
                    if resume_from > 0:
                        # Continue a previous partial download where it stopped
                        logger.info(f"Resuming {file_path.name} from {resume_from} bytes")
                        headers = {"Range": f"bytes={resume_from}-"}
                        async with self.session.get(download_url, headers=headers) as response: # type: ignore
                            if response.status == 206:
                                await self._write_body(response, part_path, 'ab', resume_from, expected_size,
                                                       file_id, file_path.name, progress_manager)
                            elif response.status == 200:
                                await self._write_body(response, part_path, 'wb', 0, expected_size,
                                                       file_id, file_path.name, progress_manager)
                            elif response.status == 416 and part_path.stat().st_size == expected_size:
                                pass  # Already fully downloaded
                            else:
                                raise aiohttp.ClientResponseError(
                                    response.request_info, response.history,
                                    status=response.status, message=f"HTTP {response.status} resuming {url}"
                                )
                    
                    actual_size = part_path.stat().st_size
                    if expected_size is not None and actual_size != expected_size:
                        raise IOError(f"incomplete download ({actual_size} of {expected_size} bytes)")
                    
                    if expected_sha256 and self.download_settings.get("verify_hash", False):
                        actual_sha256 = await asyncio.to_thread(self.sha256_of, part_path)
                        if actual_sha256 != expected_sha256.upper():
                            part_path.unlink()
                            raise IOError("SHA256 does not match CivitAI's hash")
                    
                    part_path.replace(file_path)
                    logger.success(f"Successfully downloaded: {file_path.name}")
                    return True, f"Downloaded: {file_path.name}"
                
                except asyncio.TimeoutError:
                    error_msg = f"Timeout downloading {url}"
                except aiohttp.ClientResponseError as e:
                    error_msg = e.message or f"HTTP {e.status} for {url}"
                except Exception as e:
                    error_msg = f"Error downloading {url}: {str(e)}"
                
                logger.warning(f"Attempt {attempt + 1}/{retry_attempts} failed for {file_path.name}: {error_msg}")
                if attempt == retry_attempts - 1:
                    return False, error_msg
                await asyncio.sleep(2 ** attempt)
        
        return False, "Max retries exceeded"
    
    async def _write_body(self, response, part_path: Path, mode: str, already: int,
                          expected_size: Optional[int], file_id: str, display_name: str,
                          progress_manager: ProgressManager):
        """Stream a response body into part_path with a progress bar"""
        progress = progress_manager.create_file_progress(file_id, display_name, expected_size or 0)
        if already:
            progress.update(already)
        try:
            async with aiofiles.open(part_path, mode) as f:
                async for chunk in response.content.iter_chunked(1024 * 1024):
                    await f.write(chunk)
                    progress.update(len(chunk))
        finally:
            progress_manager.remove_file_progress(file_id)
    
    async def download_files(self, download_tasks: List[Tuple], 
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
            for url, file_path, *rest in download_tasks:
                # Tasks may carry a third item: {"size": bytes, "sha256": hex} to verify against
                extra = {"expected": rest[0]} if rest and rest[0] else {}
                task = self.download_file(url, file_path, semaphore, progress_manager, **extra)
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
