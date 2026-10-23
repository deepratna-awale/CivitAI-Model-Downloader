#!/usr/bin/env python3
"""
CivitAI Model Downloader - CLI Interface

Runs the same CLI as the installed `civitai-download` command.
"""

import sys

try:
    from civitai_downloader.cli import run
except ImportError as e:
    print(f"Error: Missing required dependency: {e}")
    print("Please install the required packages:")
    print("pip install -r requirements.txt")
    sys.exit(1)

if __name__ == "__main__":
    run()
