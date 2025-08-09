#!/usr/bin/env python3
"""
Test runner script for CivitAI Model Downloader
"""

import subprocess
import sys
from pathlib import Path


def install_test_requirements():
    """Install test requirements"""
    requirements_file = Path(__file__).parent / "requirements-test.txt"
    if requirements_file.exists():
        print("Installing test requirements...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ])
    else:
        print("Installing basic test requirements...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "pytest", "pytest-asyncio", "pytest-mock", "pytest-cov"
        ])


def run_tests(test_type="all", verbose=False, coverage=True):
    """Run tests with specified options"""
    import os
    
    # Set PYTHONPATH to include current directory
    env = os.environ.copy()
    env['PYTHONPATH'] = '.'
    
    cmd = [sys.executable, "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=src", "--cov-report=term-missing"])
    
    if test_type == "unit":
        cmd.append("-m")
        cmd.append("unit")
    elif test_type == "integration":
        cmd.append("-m")
        cmd.append("integration")
    elif test_type == "fast":
        cmd.append("-m")
        cmd.append("not slow")
    
    cmd.append("tests/")
    
    print(f"Running command: {' '.join(cmd)}")
    return subprocess.call(cmd, env=env)


def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run tests for CivitAI Model Downloader")
    parser.add_argument(
        "--type", 
        choices=["all", "unit", "integration", "fast"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument("--install", action="store_true", help="Install test requirements")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-coverage", action="store_true", help="Skip coverage reporting")
    
    args = parser.parse_args()
    
    if args.install:
        install_test_requirements()
    
    return run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=not args.no_coverage
    )


if __name__ == "__main__":
    sys.exit(main())
