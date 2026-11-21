"""Verify the distributed files before or after restoring compressed records."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / "FILE_MANIFEST.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        path = ROOT / entry["path"]
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError(f"Checksum mismatch: {entry['path']}")
        if "uncompressed_sha256" in entry:
            digest = hashlib.sha256(gzip.decompress(data)).hexdigest()
            if digest != entry["uncompressed_sha256"]:
                raise ValueError(f"Uncompressed checksum mismatch: {entry['path']}")
    print(f"Verified {len(manifest['files'])} distributed files.")


if __name__ == "__main__":
    main()
