"""Releases públicas autenticadas por manifesto Ed25519."""

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from packaging.version import Version, InvalidVersion

from . import __version__
from .update_trust import PUBLIC_KEY, REPOSITORY

MAX_DOWNLOAD = 250 * 1024 * 1024


def canonical_manifest(manifest):
    return json.dumps(
        {k: v for k, v in manifest.items() if k != "signature"},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def verify_manifest(manifest, public_key=PUBLIC_KEY):
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key, validate=True)).verify(
            base64.b64decode(manifest["signature"], validate=True), canonical_manifest(manifest)
        )
        version = Version(manifest["version"])
        asset = manifest["windows-x64"]
        if manifest["schema"] != 1 or version.is_prerelease:
            raise ValueError("Versão incompatível com o canal estável.")
        url = urlparse(asset["url"])
        if (
            url.scheme != "https"
            or url.hostname != "github.com"
            or not url.path.startswith(f"/{REPOSITORY}/releases/download/")
        ):
            raise ValueError("Origem da atualização inválida.")
        if type(asset["size"]) is not int or not 0 < asset["size"] <= MAX_DOWNLOAD:
            raise ValueError("Tamanho de atualização inválido.")
        if len(asset["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in asset["sha256"]):
            raise ValueError("Hash de atualização inválido.")
    except Exception as exc:
        raise ValueError("Não foi possível autenticar a atualização.") from exc
    return manifest


def read_json(url):
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"TesseraPiano/{__version__}",
        },
    )
    with urlopen(request, timeout=20) as response:
        data = response.read(512 * 1024 + 1)
    if len(data) > 512 * 1024:
        raise ValueError("Resposta de atualização excede o limite.")
    return json.loads(data)


def check_release():
    release = read_json(f"https://api.github.com/repos/{REPOSITORY}/releases/latest")
    try:
        if Version(release["tag_name"].lstrip("v")) <= Version(__version__):
            return None
    except (InvalidVersion, KeyError) as exc:
        raise ValueError("Resposta de versão inválida.") from exc
    asset = next((a for a in release.get("assets", []) if a.get("name") == "update.json"), None)
    if not asset:
        raise ValueError("A versão publicada ainda não tem manifesto de atualização.")
    url = asset["browser_download_url"]
    if not url.startswith(f"https://github.com/{REPOSITORY}/releases/download/"):
        raise ValueError("Endereço do manifesto inválido.")
    manifest = verify_manifest(read_json(url))
    if Version(manifest["version"]) != Version(release["tag_name"].lstrip("v")):
        raise ValueError("A versão do manifesto diverge da release.")
    return manifest


def download_update(manifest, directory, progress=lambda value: None, cancel=None):
    verify_manifest(manifest)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    asset = manifest["windows-x64"]
    target = directory / f"TesseraPiano-{Version(manifest['version'])}-setup.exe"
    temporary = target.with_suffix(".partial")
    digest, count = hashlib.sha256(), 0
    try:
        with (
            urlopen(
                Request(asset["url"], headers={"User-Agent": f"TesseraPiano/{__version__}"}),
                timeout=30,
            ) as response,
            temporary.open("wb") as stream,
        ):
            while block := response.read(256 * 1024):
                if cancel and cancel.is_set():
                    raise InterruptedError("Download cancelado.")
                count += len(block)
                if count > asset["size"]:
                    raise ValueError("O download excedeu o tamanho assinado.")
                stream.write(block)
                digest.update(block)
                progress(count / asset["size"])
        if count != asset["size"] or digest.hexdigest() != asset["sha256"]:
            raise ValueError("O arquivo recebido não corresponde à atualização assinada.")
        temporary.replace(target)
        target.with_suffix(".json").write_text(json.dumps(manifest), encoding="utf-8")
        return target
    finally:
        temporary.unlink(missing_ok=True)


def launch_installer(installer, profile):
    installer = Path(installer).resolve()
    manifest = verify_manifest(
        json.loads(installer.with_suffix(".json").read_text(encoding="utf-8"))
    )
    if Version(manifest["version"]) <= Version(__version__):
        raise ValueError("A atualização precisa ser mais recente que a instalação atual.")
    if (
        hashlib.file_digest(installer.open("rb"), "sha256").hexdigest()
        != manifest["windows-x64"]["sha256"]
    ):
        raise ValueError("O instalador foi alterado após o download.")
    if not getattr(sys, "frozen", False):
        raise ValueError("Instale a versão distribuída para aplicar atualizações pelo aplicativo.")
    helper = Path(profile) / "updates" / "apply_update.ps1"
    helper.parent.mkdir(exist_ok=True)
    shutil.copy2(Path(__file__).parent / "resources" / "apply_update.ps1", helper)
    subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-WindowStyle",
            "Hidden",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(helper),
            "-Installer",
            str(installer),
            "-AppProcessId",
            str(os.getpid()),
            "-InstallDirectory",
            str(Path(sys.executable).parent),
            "-ProfileDirectory",
            str(profile),
            "-ExpectedVersion",
            manifest["version"],
        ],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
