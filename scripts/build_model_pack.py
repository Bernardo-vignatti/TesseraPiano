"""Empacota o ambiente CPU separado; pesos e bibliotecas não entram no Git."""

import argparse
import base64
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request
import zipfile

from cryptography.hazmat.primitives import serialization
from tessera_piano.model_pack import PACK_VERSION, PACK_RELEASE, verify_pack
from tessera_piano.update_trust import REPOSITORY
from tessera_piano.updates import canonical_manifest

ROOT = Path(__file__).resolve().parent.parent
SOURCE = "747df2d12291e37f6638b39f1b71517e579ad48c"
WEIGHTS = "8f1568201d1ec035c73939d5a67c5168c0b80221"


def download(url, target, sha=None):
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        urllib.request.urlretrieve(url, target)
    if sha and hashlib.file_digest(target.open("rb"), "sha256").hexdigest() != sha:
        raise ValueError(f"Hash inválido: {target.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", type=Path, default=ROOT / ".local/model-build")
    parser.add_argument("--key-file", required=True, type=Path)
    args = parser.parse_args()
    work = args.work.resolve()
    runtime = work / "venv/Scripts/python.exe"
    if not runtime.exists():
        subprocess.run(["py", "-3.12", "-m", "venv", str(work / "venv")], check=True)
        subprocess.run(
            [
                str(runtime),
                "-m",
                "pip",
                "install",
                "--extra-index-url",
                "https://download.pytorch.org/whl/cpu",
                "-r",
                str(ROOT / "packaging/model-requirements.lock"),
            ],
            check=True,
        )
    pack = work / "pack"
    python = pack / "python"
    python.mkdir(parents=True, exist_ok=True)
    embedded = work / "python-3.12.10-embed-amd64.zip"
    download(
        "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip",
        embedded,
        "4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3",
    )
    with zipfile.ZipFile(embedded) as zipped:
        zipped.extractall(python)
    (python / "python312._pth").write_text(
        "python312.zip\n.\nLib/site-packages\nimport site\n", encoding="utf-8"
    )
    shutil.copytree(
        work / "venv/Lib/site-packages",
        python / "Lib/site-packages",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "pip", "pip-*.dist-info"),
    )
    engine = pack / "engine"
    for filename in (
        "src/model/pianoformer.py",
        "src/model/generate.py",
        "src/utils/midi.py",
        "LICENSE",
    ):
        download(
            f"https://raw.githubusercontent.com/yhj137/PianistTransformer/{SOURCE}/{filename}",
            engine / filename,
        )
    for filename in ("config.json", "generation_config.json", "model.safetensors"):
        download(
            f"https://huggingface.co/yhj137/pianist-transformer-rendering/resolve/{WEIGHTS}/{filename}",
            engine / "weights" / filename,
            "8fb9111efc147adcc61a4885bd42a6e6b625626d9fb8576811916927aa8281d0"
            if filename == "model.safetensors"
            else None,
        )
    shutil.copy2(ROOT / "packaging/model-requirements.lock", pack / "requirements.lock")
    (pack / "NOTICE.txt").write_text(
        f"Pianist Transformer — Hong-Jie You et al.\nhttps://github.com/yhj137/PianistTransformer\nCode revision: {SOURCE}\nWeights: yhj137/pianist-transformer-rendering@{WEIGHTS}\nApache-2.0: engine/LICENSE\nInference adapter: Tessera Piano, MIT.\nPython: python/LICENSE.txt\nDependency licenses: python/Lib/site-packages/*.dist-info\n",
        encoding="utf-8",
    )
    # O pacote publicado precisa rodar sem o Python e o venv usados na compilação.
    proof = work / "pack-proof.json"
    if not (work / "input.json").is_file():
        pitches = (60, 64, 67, 72, 71, 67, 65, 62, 60, 64, 67, 60)
        (work / "input.json").write_text(
            json.dumps(
                {
                    "seed": 17,
                    "notes": [
                        {"pitch": p, "start": i * 0.45, "gate": 0.32, "velocity": 80}
                        for i, p in enumerate(pitches)
                    ],
                }
            ),
            encoding="utf-8",
        )
    subprocess.run(
        [
            str(python / "python.exe"),
            str(ROOT / "src/tessera_piano/resources/model_worker.py"),
            str(pack),
            str(work / "input.json"),
            str(proof),
        ],
        check=True,
        timeout=180,
    )
    result = json.loads(proof.read_text(encoding="utf-8"))
    source = json.loads((work / "input.json").read_text(encoding="utf-8"))
    assert [n["pitch"] for n in result["notes"]] == [n["pitch"] for n in source["notes"]]
    destination = ROOT / ".local/model-release"
    destination.mkdir(exist_ok=True)
    archive = destination / (PACK_VERSION + ".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
        for file in sorted(pack.rglob("*")):
            if file.is_file() and "__pycache__" not in file.parts:
                zipped.write(file, file.relative_to(pack).as_posix())
    manifest = {
        "schema": 1,
        "pack": PACK_VERSION,
        "asset": {
            "url": f"https://github.com/{REPOSITORY}/releases/download/{PACK_RELEASE}/{archive.name}",
            "size": archive.stat().st_size,
            "sha256": hashlib.file_digest(archive.open("rb"), "sha256").hexdigest(),
        },
    }
    key = serialization.load_pem_private_key(args.key_file.read_bytes(), password=None)
    manifest["signature"] = base64.b64encode(key.sign(canonical_manifest(manifest))).decode()
    verify_pack(manifest)
    (destination / "models.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(
        "Package:", archive.name, "bytes:", archive.stat().st_size, "proof:", result["seconds"], "s"
    )


if __name__ == "__main__":
    main()
