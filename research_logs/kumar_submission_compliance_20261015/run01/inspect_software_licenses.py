#!/usr/bin/env python3
"""Record installed license metadata and files without importing scientific packages."""

import argparse
import hashlib
import importlib.metadata
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    records = []
    for distribution in sorted(
        importlib.metadata.distributions(),
        key=lambda item: item.metadata.get("Name", "").lower(),
    ):
        files = []
        for relative in distribution.files or []:
            basename = str(relative).rsplit("/", 1)[-1].lower()
            if not any(
                marker in basename
                for marker in ("license", "licence", "copying", "copyright", "notice")
            ):
                continue
            path = Path(distribution.locate_file(relative))
            if path.is_file():
                data = path.read_bytes()
                files.append(
                    {
                        "relative_path": str(relative),
                        "path": str(path),
                        "bytes": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(),
                    }
                )
        metadata = distribution.metadata
        records.append(
            {
                "name": metadata.get("Name", ""),
                "version": distribution.version,
                "license_expression": metadata.get("License-Expression"),
                "license_field": metadata.get("License"),
                "license_classifiers": [
                    value
                    for value in metadata.get_all("Classifier") or []
                    if value.startswith("License")
                ],
                "project_urls": metadata.get_all("Project-URL") or [],
                "license_files": files,
            }
        )
    result = {
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "executable": sys.executable,
        "scope": "Installed metadata and license-file hashes; no scientific imports or execution",
        "all_bundled_third_party_licenses_independently_classified": False,
        "packages": records,
    }
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    main()
