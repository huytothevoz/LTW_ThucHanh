#!/usr/bin/env python3
"""Compatibility launcher that delegates the web server to Laravel."""

from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
PHP = shutil.which("php")

if PHP is None:
    raise SystemExit("PHP 8.2+ is required. Run scripts/setup_windows.ps1 and start Laravel with scripts/start_windows.ps1.")

raise SystemExit(
    subprocess.call(
        [PHP, "artisan", "serve", "--host=127.0.0.1", "--port=8000"],
        cwd=ROOT,
    )
)
