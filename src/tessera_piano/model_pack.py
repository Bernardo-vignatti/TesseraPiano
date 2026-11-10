"""Instalação autenticada e inferência cancelável do pacote musical opcional."""

from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from urllib.parse import urlparse
import zipfile

from .analysis import pitch
from .music import Song, PedalChange
from .storage import atomic_text
from .updates import canonical_manifest, read_json
from .update_trust import PUBLIC_KEY, REPOSITORY

PACK_VERSION = "pianist-cpu-1"
PACK_RELEASE = "v4.2.0-beta.1"
PACK_MANIFEST = f"https://github.com/{REPOSITORY}/releases/download/{PACK_RELEASE}/models.json"


def verify_pack(manifest, public_key=PUBLIC_KEY):
    import base64
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key, validate=True)).verify(
            base64.b64decode(manifest["signature"], validate=True), canonical_manifest(manifest)
        )
        asset = manifest["asset"]
        url = urlparse(asset["url"])
        if manifest["schema"] != 1 or manifest["pack"] != PACK_VERSION:
            raise ValueError("Pacote incompatível.")
        if not (
            url.scheme == "https"
            and url.hostname == "github.com"
            and url.path.startswith(f"/{REPOSITORY}/releases/download/")
        ):
            raise ValueError("Origem inválida.")
        if type(asset["size"]) is not int or not 0 < asset["size"] < 1024**3:
            raise ValueError("Tamanho inválido.")
        if len(asset["sha256"]) != 64 or not all(c in "0123456789abcdef" for c in asset["sha256"]):
            raise ValueError("Hash inválido.")
    except Exception as exc:
        raise ValueError("Não foi possível autenticar o pacote musical.") from exc
    return manifest


class ModelPack:
    def __init__(self, directory):
        self.directory = Path(directory) / "models"
        self.root = self.directory / PACK_VERSION

    def ready(self):
        try:
            verify_pack(json.loads((self.root / "installed.json").read_text(encoding="utf-8")))
            return (self.root / "python/python.exe").is_file()
        except (OSError, ValueError, KeyError, TypeError):
            return False

    def install(self, progress, cancel, force=False):
        from urllib.request import urlopen

        manifest = verify_pack(read_json(PACK_MANIFEST))
        self.directory.mkdir(parents=True, exist_ok=True)
        if self.ready() and not force:
            return
        asset = manifest["asset"]
        if shutil.disk_usage(self.directory).free < asset["size"] + 2 * 1024**3:
            raise OSError("São necessários cerca de 2,5 GB livres para instalar o motor.")
        with tempfile.TemporaryDirectory(prefix="install-", dir=self.directory) as temporary:
            temporary = Path(temporary)
            archive = temporary / "pack.zip"
            digest, count = hashlib.sha256(), 0
            with urlopen(asset["url"], timeout=30) as response, archive.open("wb") as stream:
                while block := response.read(1024 * 1024):
                    if cancel.is_set():
                        raise InterruptedError("Instalação do motor cancelada.")
                    count += len(block)
                    if count > asset["size"]:
                        raise ValueError("O pacote excedeu o tamanho assinado.")
                    stream.write(block)
                    digest.update(block)
                    progress(0.9 * count / asset["size"])
            if count != asset["size"] or digest.hexdigest() != asset["sha256"]:
                raise ValueError("O pacote musical não corresponde à assinatura.")
            extracted = temporary / "content"
            extracted.mkdir()
            with zipfile.ZipFile(archive) as zipped:
                entries = zipped.infolist()
                if sum(e.file_size for e in entries) > 3 * 1024**3 or len(entries) > 100000:
                    raise ValueError("Conteúdo do pacote excede o limite.")
                for entry in entries:
                    target = (extracted / entry.filename).resolve()
                    if (
                        not target.is_relative_to(extracted.resolve())
                        or ":" in entry.filename
                        or (entry.external_attr >> 16) & 0o170000 == 0o120000
                    ):
                        raise ValueError("Caminho inválido no pacote musical.")
                    if cancel.is_set():
                        raise InterruptedError("Instalação do motor cancelada.")
                    zipped.extract(entry, extracted)
            if (
                not (extracted / "python/python.exe").is_file()
                or not (extracted / "engine/weights/model.safetensors").is_file()
            ):
                raise ValueError("O pacote musical está incompleto.")
            atomic_text(extracted / "installed.json", json.dumps(manifest))
            if cancel.is_set():
                raise InterruptedError("Instalação do motor cancelada.")
            previous = temporary / "previous"
            if self.root.exists():
                self.root.rename(previous)
            try:
                extracted.rename(self.root)
            except OSError:
                if previous.exists():
                    previous.rename(self.root)
                raise
            progress(1)

    def render(self, song, intensity, seed, cancel, progress=lambda value: None):
        if not self.ready():
            raise ValueError("Instale o motor local nas configurações.")
        source = sorted(song.notes, key=lambda n: (n.start, pitch(n)))
        request = {
            "seed": seed,
            "notes": [
                {
                    "pitch": pitch(n),
                    "start": n.start,
                    "gate": n.gate_duration or n.duration,
                    "velocity": n.velocity,
                }
                for n in source
            ],
        }
        with tempfile.TemporaryDirectory(prefix="render-", dir=self.directory) as temporary:
            temporary = Path(temporary)
            input_path, output_path = temporary / "input.json", temporary / "output.json"
            input_path.write_text(json.dumps(request), encoding="utf-8")
            log = temporary / "worker.log"
            with log.open("w", encoding="utf-8") as stream:
                process = subprocess.Popen(
                    [
                        str(self.root / "python/python.exe"),
                        str(Path(__file__).parent / "resources/model_worker.py"),
                        str(self.root),
                        str(input_path),
                        str(output_path),
                    ],
                    stdout=stream,
                    stderr=stream,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                deadline = time.monotonic() + max(180, min(1800, len(source) * 1.5))
                try:
                    while process.poll() is None:
                        if cancel.wait(0.1):
                            raise InterruptedError("Preparação cancelada.")
                        if time.monotonic() > deadline:
                            raise TimeoutError("O motor excedeu o tempo de preparação.")
                        # O trabalhador escreve progresso JSON entre mensagens de biblioteca.
                        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
                        for line in reversed(lines[-20:]):
                            if line.startswith('{"progress":'):
                                progress(json.loads(line)["progress"])
                                break
                    if process.returncode or not output_path.is_file():
                        raise ValueError(
                            "O motor local não concluiu a análise; usando regras musicais."
                        )
                finally:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=5)
            return apply_render(
                song, source, json.loads(output_path.read_text(encoding="utf-8")), intensity
            )


def apply_render(song, source, result, intensity):
    rows = result["notes"]
    if len(rows) != len(source) or any(row["pitch"] != pitch(n) for n, row in zip(source, rows)):
        raise ValueError("A interpretação alterou a sequência de notas; usando regras musicais.")
    output = []
    intensity = max(0, min(1, intensity))
    first = rows[0]["start"]
    span = rows[-1]["start"] - first
    source_span = source[-1].start - source[0].start
    scale = source_span / span if span > 0.01 and source_span > 0.01 else 1
    if not 0.2 <= scale <= 5:
        raise ValueError("A interpretação não preservou a estrutura temporal.")
    for note, row in zip(source, rows):
        if (
            any(not math.isfinite(row[k]) for k in ("start", "gate"))
            or row["start"] < 0
            or not 0.001 <= row["gate"] <= 60
        ):
            raise ValueError("A interpretação contém tempos inválidos.")
        predicted_start = source[0].start + (row["start"] - first) * scale
        start = max(0, note.start + (predicted_start - note.start) * intensity)
        gate = (note.gate_duration or note.duration) * (1 - intensity) + row[
            "gate"
        ] * scale * intensity
        output.append(
            replace(
                note,
                start=start,
                duration=gate,
                gate_duration=gate,
                velocity=max(1, min(127, row["velocity"])),
            )
        )
    end = max(n.start + n.duration for n in output)
    source_end = max(n.start + (n.gate_duration or n.duration) for n in source)
    if end > 7200 or not 0.5 <= end / max(0.01, source_end) <= 2:
        raise ValueError("A interpretação alterou demais o andamento.")
    from bisect import bisect_right

    original_times = [n.start for n in source]

    def warp(moment):
        i = max(0, bisect_right(original_times, moment) - 1)
        if i + 1 == len(source) or original_times[i + 1] == original_times[i]:
            return max(0, output[i].start + moment - original_times[i])
        ratio = (moment - original_times[i]) / (original_times[i + 1] - original_times[i])
        return max(0, output[i].start + ratio * (output[i + 1].start - output[i].start))

    pedal = [PedalChange(warp(p.time), p.down) for p in song.pedal]
    predicted = []
    state, previous = False, -1.0
    model_times = [r["start"] for r in rows]
    for item in result.get("pedal", []):
        raw, value = item["time"], item["value"]
        i = max(0, bisect_right(model_times, raw) - 1)
        original_moment = source[i].start + (raw - model_times[i]) * scale
        if i + 1 < len(rows) and model_times[i + 1] > model_times[i]:
            fraction = (raw - model_times[i]) / (model_times[i + 1] - model_times[i])
            original_moment = source[i].start + fraction * (source[i + 1].start - source[i].start)
        normalized_moment = source[0].start + (raw - first) * scale
        moment = max(0, original_moment * (1 - intensity) + normalized_moment * intensity)
        if not math.isfinite(moment) or moment < 0 or moment > end + 0.12:
            continue
        down = value >= (48 if state else 72)
        if state != down and moment - previous >= 0.06:
            predicted.append(PedalChange(moment, down))
            state, previous = down, moment
    if state:
        predicted.append(PedalChange(end + 0.12, False))
    metadata = dict(
        song.metadata,
        total_duration=max(end, warp(song.duration)),
        model_pedal=[{"time": p.time, "down": p.down} for p in predicted],
        model_version=PACK_VERSION,
        model_seconds=result.get("seconds", 0),
        model_peak_mb=result.get("peak_mb", 0),
    )
    metadata["tempo_map"] = [
        dict(e, time=warp(e["time"])) for e in song.metadata.get("tempo_map", [])
    ]
    metadata.pop("analysis", None)
    return Song(song.title, output, metadata, pedal)
