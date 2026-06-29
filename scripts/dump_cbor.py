#!/usr/bin/env python3
"""Pretty-print nested CBOR, peeling base64 wrappers and CBOR-inside-bytes.

    python scripts/dump_cbor.py <file>          # raw CBOR, or JSON whose string
                                                # values are base64-wrapped CBOR
    python scripts/dump_cbor.py --b64 <file>    # file content is base64 CBOR

mdoc structures nest CBOR inside byte strings (a device response whose documents
are themselves CBOR-encoded bytes), so this recurses into any byte string that
parses as CBOR and truncates the rest to hex.
"""

import base64
import json
import sys
from pathlib import Path

import cbor2


def _as_cbor(b: bytes):
    try:
        return cbor2.loads(b)
    except Exception:
        return None


def show(value, indent: int = 0, max_bytes: int = 24) -> None:
    pad = "  " * indent
    if isinstance(value, dict):
        for key, val in value.items():
            print(f"{pad}{key!r}:")
            show(val, indent + 1, max_bytes)
    elif isinstance(value, (list, tuple)):
        for i, val in enumerate(value):
            print(f"{pad}[{i}]")
            show(val, indent + 1, max_bytes)
    elif isinstance(value, (bytes, bytearray)):
        nested = _as_cbor(value)
        if isinstance(nested, (dict, list)):
            print(f"{pad}bytes({len(value)}) -> CBOR:")
            show(nested, indent + 1, max_bytes)
        else:
            tail = "..." if len(value) > max_bytes else ""
            print(f"{pad}bytes({len(value)}) {value[:max_bytes].hex()}{tail}")
    elif isinstance(value, cbor2.CBORTag):
        embedded = _as_cbor(value.value) if value.tag == 24 else None
        if embedded is not None:
            print(f"{pad}tag24 -> embedded CBOR ({len(value.value)} bytes):")
            show(embedded, indent + 1, max_bytes)
        else:
            print(f"{pad}tag{value.tag}:")
            show(value.value, indent + 1, max_bytes)
    else:
        print(f"{pad}{value!r}")


def load(path: str, force_b64: bool):
    raw = Path(path).read_bytes()
    if force_b64:
        return cbor2.loads(base64.b64decode(raw))
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return cbor2.loads(raw)
    # JSON whose string values are base64-wrapped CBOR (e.g. post*.json fixtures).
    if isinstance(obj, dict):
        return {
            k: (_as_cbor(base64.b64decode(v)) or v) if isinstance(v, str) else v
            for k, v in obj.items()
        }
    return obj


if __name__ == "__main__":
    paths = [a for a in sys.argv[1:] if a != "--b64"]
    if not paths:
        sys.exit(__doc__)
    show(load(paths[0], "--b64" in sys.argv))
