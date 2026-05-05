#!/usr/bin/env python3
"""Render a CIMD metadata document with its public URL as client_id."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = ROOT / "client" / "client_metadata.example.json"


def _public_https_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path in ("", "/"):
        raise argparse.ArgumentTypeError(
            "CIMD_DOC_URL must be an HTTPS URL with a non-root path"
        )
    return value


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render client/client_metadata.example.json for a CIMD URL."
    )
    parser.add_argument(
        "client_id",
        type=_public_https_url,
        help="Public HTTPS URL where this metadata document will be hosted.",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=DEFAULT_TEMPLATE,
        help="Template JSON to read.",
    )
    args = parser.parse_args()

    with args.template.open(encoding="utf-8") as f:
        metadata = json.load(f)

    metadata["client_id"] = args.client_id
    json.dump(metadata, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
