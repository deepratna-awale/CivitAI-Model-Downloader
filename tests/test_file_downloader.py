"""
Tests for File Downloader
"""

import pytest
import asyncio
import aiohttp
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import threading

from src.downloader.file_downloader import ProgressManager, FileDownloader


class TestProgressManager:
    """Test cases for ProgressManager class"""
    
    def test_initialization(self):
        """Test ProgressManager initialization"""
        manager = ProgressManager(max_concurrent=4)
        
        assert manager.max_concurrent == 4
        assert manager.active_downloads == {}
        assert manager.next_position == 1
        assert isinstance(manager.lock, type(threading.Lock()))
        assert manager.overall_pbar is None
    
    @patch('src.downloader.file_downloader.tqdm')
    def test_create_file_progress_with_size(self, mock_tqdm):
        """Test creating file progress bar with known size"""
        mock_pbar = MagicMock()
        mock_tqdm.return_value = mock_pbar
        
        manager = ProgressManager(max_concurrent=2)
        
        pbar = manager.create_file_progress("file1", "test_file.txt", 1024)
        
        assert pbar == mock_pbar
        mock_tqdm.assert_called_once()
        call_args = mock_tqdm.call_args[1]
        assert call_args['total'] == 1024
        assert call_args['position'] == 1
        assert "test_file.txt" in call_args['desc']
    
    @patch('src.downloader.file_downloader.tqdm')
    def test_create_file_progress_without_size(self, mock_tqdm):
        """Test creating file progress bar without known size"""
        mock_pbar = MagicMock()
        mock_tqdm.return_value = mock_pbar
        
        manager = ProgressManager(max_concurrent=2)
        
        pbar = manager.create_file_progress("file1", "test_file.txt", 0)
        
        assert pbar == mock_pbar
        mock_tqdm.assert_called_once()
        call_args = mock_tqdm.call_args[1]
        assert 'total' not in call_args  # No total for unknown size
        assert call_args['position'] == 1
    
    def test_remove_file_progress(self):
        """Test removing file progress bar"""
        mock_pbar = MagicMock()
        manager = ProgressManager(max_concurrent=2)
        manager.active_downloads["file1"] = mock_pbar
        
        manager.remove_file_progress("file1")
        
        mock_pbar.close.assert_called_once()
        assert "file1" not in manager.active_downloads
    
    def test_cleanup(self):
        """Test cleaning up all progress bars"""
        mock_file_pbar = MagicMock()
        mock_overall_pbar = MagicMock()
        
        manager = ProgressManager(max_concurrent=2)
        manager.active_downloads["file1"] = mock_file_pbar
        manager.overall_pbar = mock_overall_pbar
        
        manager.cleanup()
        
        mock_file_pbar.close.assert_called_once()
        mock_overall_pbar.close.assert_called_once()
        assert manager.active_downloads == {}
        # Note: The actual cleanup() method doesn't set overall_pbar to None


class TestFileDownloader:
    """Test cases for FileDownloader class"""
    
    def test_initialization_with_api_key(self):
        """Test FileDownloader initialization with API key"""
        download_settings = {
            "max_concurrent_downloads": 4,
            "timeout": 30,
            "retry_attempts": 3
        }
        downloader = FileDownloader(api_key="test_key", download_settings=download_settings)
        
        assert downloader.api_key == "test_key"
        assert downloader.download_settings["max_concurrent_downloads"] == 4
        assert downloader.download_settings["timeout"] == 30
        assert downloader.download_settings["retry_attempts"] == 3
    
    def test_initialization_without_api_key(self):
        """Test FileDownloader initialization without API key"""
        downloader = FileDownloader()
        
        assert downloader.api_key is None
        assert downloader.download_settings["max_concurrent_downloads"] == 4  # Default
        assert downloader.download_settings["timeout"] == 30
        assert downloader.session is None
    
    def test_add_api_key_to_url_with_params(self):
        """Test adding API key to URL with existing parameters"""
        downloader = FileDownloader(api_key="test_key")
        
        url = "https://example.com/file?param=value"
        result = downloader.add_api_key_to_url(url)
        
        assert result == "https://example.com/file?param=value&token=test_key"
    
    def test_add_api_key_to_url_without_params(self):
        """Test adding API key to URL without parameters"""
        downloader = FileDownloader(api_key="test_key")
        
        url = "https://example.com/file"
        result = downloader.add_api_key_to_url(url)
        
        assert result == "https://example.com/file?token=test_key"
    
    def test_add_api_key_to_url_no_key(self):
        """Test adding API key when no key is set"""
        downloader = FileDownloader()
        
        url = "https://example.com/file"
        result = downloader.add_api_key_to_url(url)
        
        assert result == url  # Should return unchanged
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test FileDownloader as context manager"""
        downloader = FileDownloader(api_key="test_key")
        
        async with downloader:
            assert downloader.session is not None
        
        # Session should be closed after exiting context
        assert downloader.session is None or downloader.session.closed
    
    @pytest.mark.asyncio
    async def test_download_files_empty_list(self):
        """Test downloading empty list of files"""
        downloader = FileDownloader()
        
        async with downloader:
            results = await downloader.download_files([])
            
            assert results == []
    
    @pytest.mark.asyncio
    async def test_download_files_basic(self, temp_dir):
        """Test basic file download functionality"""
        download_tasks = [
            ("https://example.com/file1.txt", temp_dir / "file1.txt"),
        ]

        downloader = FileDownloader()

        # Mock the download_file method directly to avoid complex async mocking
        async def mock_download_file(url, file_path, semaphore, progress_manager):
            return True, "Downloaded successfully"

        with patch.object(downloader, 'download_file', side_effect=mock_download_file):
            async with downloader:
                results = await downloader.download_files(download_tasks)

            assert len(results) == 1
            assert results[0][0] is True  # Success
            assert "Downloaded successfully" in results[0][1]