#!/usr/bin/env python3
"""
CivitAI URL Preprocessor - Standalone Script
Converts non-download URLs to proper download URLs using CivitAI API

Runs the same CLI as the installed `civitai-preprocess` command.
"""

import sys

try:
    from civitai_downloader.preprocess_cli import run
except ImportError as e:
    print(f"Error: Missing required dependency: {e}")
    print("Please install the required packages:")
    print("pip install -r requirements.txt")
    sys.exit(1)

if __name__ == "__main__":
    run()
