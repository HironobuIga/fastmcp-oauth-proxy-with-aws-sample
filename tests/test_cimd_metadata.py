from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fastmcp.server.auth.cimd import CIMDDocument


ROOT = Path(__file__).resolve().parent.parent


def test_cimd_metadata_template_is_schema_valid():
    metadata = json.loads(
        (ROOT / "client" / "client_metadata.example.json").read_text(encoding="utf-8")
    )

    CIMDDocument.model_validate(metadata)


def test_cimd_metadata_renderer_sets_matching_client_id():
    client_id = "https://example.com/oauth/client_metadata.json"

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "render_cimd_metadata.py"),
            client_id,
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    metadata = json.loads(result.stdout)
    document = CIMDDocument.model_validate(metadata)
    assert str(document.client_id).rstrip("/") == client_id
