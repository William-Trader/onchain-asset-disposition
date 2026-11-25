#!/usr/bin/env python3
"""Run the complete frozen-data audit without network access."""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, default=ROOT / 'verification')
args = parser.parse_args()
destination = args.out.resolve()
for file in ('census.py', 'thresholds.py', 'deployment.py'):
    subprocess.run([sys.executable, str(ROOT/file), '--out', str(destination)], check=True)
