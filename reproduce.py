"""Rebuild paper statistics and run the included implementation tests offline."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()
    os.chdir(ROOT)
    os.environ["PYTHONHASHSEED"] = "0"
    os.environ["PYTHONUTF8"] = "1"
    commands = [["tools/prepare_data.py"], ["tools/reproduce_paper.py"]]
    if not args.skip_tests:
        commands.append(["-m", "pytest", "-q", "tests"])
    for command in commands:
        subprocess.run([sys.executable, *command], check=True)


if __name__ == "__main__":
    main()
