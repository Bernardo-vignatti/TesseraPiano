"""Assina o manifesto; a chave privada é fornecida pelo ambiente de publicação."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from tessera_piano import __version__
from tessera_piano.updates import canonical_manifest
from tessera_piano.update_trust import REPOSITORY


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("installer", type=Path)
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("--output", type=Path, default=Path("dist/update.json"))
    args = parser.parse_args()
    pem = (
        args.key_file.read_bytes() if args.key_file else os.environ["TESSERA_SIGNING_KEY"].encode()
    )
    key = serialization.load_pem_private_key(pem, password=None)
    with args.installer.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    manifest = {
        "schema": 1,
        "version": __version__,
        "windows-x64": {
            "url": f"https://github.com/{REPOSITORY}/releases/download/v{__version__}/{args.installer.name}",
            "size": args.installer.stat().st_size,
            "sha256": digest,
        },
    }
    manifest["signature"] = base64.b64encode(key.sign(canonical_manifest(manifest))).decode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    args.installer.with_suffix(".exe.sha256").write_text(
        f"{digest}  {args.installer.name}\n", encoding="utf-8"
    )
    print("Manifesto assinado:", args.output)


if __name__ == "__main__":
    main()
