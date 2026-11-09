import base64
from io import BytesIO
import hashlib
import json
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import pytest

from tessera_piano import updates


def signed_manifest():
    key = Ed25519PrivateKey.generate()
    manifest = {
        "schema": 1,
        "version": "4.0.1",
        "windows-x64": {
            "url": f"https://github.com/{updates.REPOSITORY}/releases/download/v4.0.1/setup.exe",
            "size": 4,
            "sha256": hashlib.sha256(b"test").hexdigest(),
        },
    }
    manifest["signature"] = base64.b64encode(
        key.sign(updates.canonical_manifest(manifest))
    ).decode()
    public = base64.b64encode(
        key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    ).decode()
    return key, manifest, public


def test_valid_manifest_and_tampering():
    key, manifest, public = signed_manifest()
    assert updates.verify_manifest(manifest, public) == manifest
    manifest["version"] = "9.0.0"
    with pytest.raises(ValueError):
        updates.verify_manifest(manifest, public)


@pytest.mark.parametrize(
    "field,value",
    [
        ("url", "https://example.org/payload.exe"),
        ("size", -1),
        ("size", updates.MAX_DOWNLOAD + 1),
        ("sha256", "bad"),
    ],
)
def test_even_signed_invalid_payloads_are_rejected(field, value):
    key, manifest, public = signed_manifest()
    manifest["windows-x64"][field] = value
    manifest["signature"] = base64.b64encode(
        key.sign(updates.canonical_manifest(manifest))
    ).decode()
    with pytest.raises(ValueError):
        updates.verify_manifest(manifest, public)


def test_interrupted_or_corrupt_download_never_becomes_installer(tmp_path):
    _, manifest, _ = signed_manifest()
    with (
        patch.object(updates, "verify_manifest", return_value=manifest),
        patch.object(updates, "urlopen", return_value=BytesIO(b"evil")),
    ):
        with pytest.raises(ValueError):
            updates.download_update(manifest, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_download_verifies_and_saves_manifest(tmp_path):
    _, manifest, _ = signed_manifest()
    with (
        patch.object(updates, "verify_manifest", return_value=manifest),
        patch.object(updates, "urlopen", return_value=BytesIO(b"test")),
    ):
        path = updates.download_update(manifest, tmp_path)
    assert path.read_bytes() == b"test"
    assert json.loads(path.with_suffix(".json").read_text(encoding="utf-8")) == manifest


def test_same_version_does_not_offer_update():
    with patch.object(updates, "read_json", return_value={"tag_name": "v" + updates.__version__}):
        assert updates.check_release() is None
