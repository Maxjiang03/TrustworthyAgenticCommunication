"""Restore large records from the tracked, losslessly compressed files."""
import gzip
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    files = sorted((ROOT / "results").rglob("*.json.gz"))
    for path in files:
        destination = path.with_suffix("")
        data = gzip.decompress(path.read_bytes())
        if not destination.exists() or destination.read_bytes() != data:
            destination.write_bytes(data)
    print(f"Prepared {len(files)} compressed data files.")


if __name__ == "__main__":
    main()
