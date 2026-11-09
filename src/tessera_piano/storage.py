"""Biblioteca pessoal e preferências locais do Tessera Piano."""

from __future__ import annotations
from dataclasses import dataclass, replace
import copy
import math
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
import shutil

from .music import Song, PedalChange, parse_song, from_steps
from .midi import read_midi
from .names import clean_title, filename_title
from .score_text import parse_score

DEFAULTS = {
    "speed": 100,
    "countdown": 5,
    "mode": "scan",
    "repeat": False,
    "txt_bpm": 120,
    "txt_gate": 85,
    "favorites": [],
    "layout": "61",
    "pedal_mode": "auto",
    "hidden_songs": [],
    "deleted_songs": [],
    "title_overrides": {},
    "schema_version": 4,
    "theme": "dark",
    "reduced_motion": False,
    "performance": "natural",
    "intensity": 55,
    "seed": 17,
    "onboarding_completed": False,
    "minimize_to_tray": True,
    "check_updates": True,
    "auto_download": False,
    "track_filter": [],
    "last_song": "",
    "window_width": 1280,
    "window_height": 830,
    "last_update_check": 0,
}


def normalize_settings(values):
    result = copy.deepcopy(DEFAULTS)
    if not isinstance(values, dict):
        return result
    result.update({k: v for k, v in values.items() if k in DEFAULTS})
    ranges = {
        "speed": (25, 150),
        "countdown": (1, 30),
        "txt_bpm": (20, 400),
        "txt_gate": (10, 98),
        "intensity": (0, 100),
        "seed": (0, 2**31 - 1),
        "last_update_check": (0, 2**40),
        "window_width": (1040, 3840),
        "window_height": (720, 2160),
    }
    for key, (low, high) in ranges.items():
        value = result[key]
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            result[key] = DEFAULTS[key]
    choices = {
        "layout": ("61", "88"),
        "mode": ("scan", "virtual"),
        "pedal_mode": ("auto", "midi", "on", "off", "ignore"),
        "theme": ("dark", "light", "system"),
        "performance": ("original", "natural", "expressive"),
    }
    for key, valid in choices.items():
        if result[key] not in valid:
            result[key] = DEFAULTS[key]
    for key in (
        "repeat",
        "reduced_motion",
        "onboarding_completed",
        "minimize_to_tray",
        "check_updates",
        "auto_download",
    ):
        if type(result[key]) is not bool:
            result[key] = DEFAULTS[key]
    for key in ("favorites", "hidden_songs"):
        result[key] = (
            [v for v in result[key] if isinstance(v, str)] if isinstance(result[key], list) else []
        )
    for key in ("deleted_songs", "track_filter"):
        if not isinstance(result[key], list):
            result[key] = []
    result["deleted_songs"] = [v for v in result["deleted_songs"] if isinstance(v, dict)]
    result["track_filter"] = [v for v in result["track_filter"] if type(v) is int and v >= 0]
    if not isinstance(result["title_overrides"], dict):
        result["title_overrides"] = {}
    result["schema_version"] = 4
    if not isinstance(result["last_song"], str):
        result["last_song"] = ""
    return result


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
        stream.write(text)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


@dataclass
class LibraryItem:
    ident: str
    path: Path
    song: Song
    personal: bool = False


class Profile:
    def __init__(self, bundled, directory=None):
        self.bundled = Path(bundled)
        self.directory = (
            Path(directory)
            if directory
            else Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share")) / "TesseraPiano"
        )
        self.music_directory = self.directory / "musicas"
        self.music_directory.mkdir(parents=True, exist_ok=True)
        self.config_path = self.directory / "preferencias.json"
        config = {}
        try:
            config = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        self.config = normalize_settings(config)
        if isinstance(config, dict) and config and config.get("schema_version", 0) != 4:
            backup = self.directory / "backups" / "preferencias-v3.json"
            backup.parent.mkdir(exist_ok=True)
            if not backup.exists():
                shutil.copy2(self.config_path, backup)
        self.items = []
        self.errors = []
        self.refresh()

    def refresh(self):
        items, errors = [], []
        for folder, personal in [(self.bundled, False), (self.music_directory, True)]:
            for path in sorted(folder.glob("*.piano.json")):
                try:
                    song = parse_song(path.read_text(encoding="utf-8-sig"))
                    ident = ("user:" if personal else "bundled:") + path.name
                    if ident in self.config["hidden_songs"]:
                        continue
                    if ident in self.config["title_overrides"]:
                        song.title = (
                            clean_title(self.config["title_overrides"][ident]) or song.title
                        )
                    elif (
                        personal
                        and song.metadata.get("midi_format") is not None
                        and song.metadata.get("source_file")
                    ):
                        song.title = filename_title(song.metadata["source_file"])
                    else:
                        song.title = clean_title(song.title) or filename_title(path.name)
                    items.append(LibraryItem(ident, path, song, personal))
                except (OSError, ValueError) as error:
                    errors.append(f"{path.name}: {error}")
        self.items, self.errors = items, errors
        return items

    def save(self):
        atomic_text(self.config_path, json.dumps(self.config, ensure_ascii=False, indent=2) + "\n")

    def favorite(self, ident):
        before = list(self.config["favorites"])
        favorites = self.config["favorites"]
        if ident in favorites:
            favorites.remove(ident)
        else:
            favorites.append(ident)
        try:
            self.save()
        except OSError:
            self.config["favorites"] = before
            raise

    def import_file(self, path, parse_legacy=parse_score):
        path = Path(path)
        if path.stat().st_size > 32 * 1024 * 1024:
            raise ValueError("O arquivo excede o limite de 32 MB.")
        if path.suffix.lower() not in (".mid", ".midi", ".txt", ".json"):
            raise ValueError("Escolha um arquivo MIDI, piano.json ou TXT.")
        if path.suffix.lower() in (".mid", ".midi"):
            song = read_midi(path)
        else:
            text = path.read_text(encoding="utf-8-sig")
            song = (
                parse_song(text)
                if text.lstrip().startswith("{")
                else from_steps(
                    parse_legacy(text),
                    float(self.config["txt_bpm"]),
                    float(self.config["txt_gate"]) / 100,
                    path.stem,
                )
            )
        # Validar com o mesmo leitor antes de adicionar à biblioteca.
        if path.suffix.lower() in (".mid", ".midi"):
            song.metadata["source_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            originals = self.directory / "originais"
            originals.mkdir(exist_ok=True)
            original = originals / (song.metadata["source_sha256"] + ".mid")
            if not original.exists():
                temporary = original.with_suffix(".partial")
                try:
                    shutil.copy2(path, temporary)
                    temporary.replace(original)
                finally:
                    temporary.unlink(missing_ok=True)
        content = song.to_text()
        parse_song(content)
        digest = hashlib.sha256(content.encode()).hexdigest()[:10]
        stem = re.sub(r"[^\w-]+", "_", path.stem, flags=re.UNICODE).strip("_")[:75] or "musica"
        destination = self.music_directory / ("music-" + stem + "-" + digest + ".piano.json")
        for item in self.items:
            if not item.personal:
                continue
            same_hash = (
                song.metadata.get("source_sha256") is not None
                and item.song.metadata.get("source_sha256") == song.metadata["source_sha256"]
            )
            same_content = (
                item.song.notes == song.notes
                and item.song.metadata.get("source_file") == song.metadata.get("source_file")
                and (song.metadata.get("source_file") is not None or item.song.title == song.title)
            )
            if same_hash or same_content:
                destination = item.path
                break
        atomic_text(destination, content)
        self.refresh()
        return next(item for item in self.items if item.path == destination)

    def rename(self, ident, title):
        item = next((i for i in self.items if i.ident == ident), None)
        if item is None:
            raise ValueError("Música não encontrada.")
        title = clean_title(title)
        if not title:
            raise ValueError("Informe um nome para a música.")
        before = copy.deepcopy(self.config)
        self.config["title_overrides"][ident] = title
        try:
            self.save()
        except OSError:
            self.config = before
            raise
        self.refresh()
        return next(i for i in self.items if i.ident == ident)

    def delete(self, ident):
        item = next((i for i in self.items if i.ident == ident), None)
        if item is None:
            raise ValueError("Música não encontrada.")
        before = copy.deepcopy(self.config)
        record = {
            "ident": ident,
            "personal": item.personal,
            "filename": item.path.name,
            "favorite": ident in self.config["favorites"],
        }
        if item.personal:
            if item.path.resolve().parent != self.music_directory.resolve():
                raise ValueError("Arquivo fora da biblioteca pessoal.")
            trash = self.directory / "lixeira"
            trash.mkdir(exist_ok=True)
            destination = trash / (str(time.time_ns()) + "-" + item.path.name)
            item.path.replace(destination)
            record["trash_name"] = destination.name
        else:
            self.config["hidden_songs"].append(ident)
        self.config["favorites"] = [i for i in self.config["favorites"] if i != ident]
        self.config["deleted_songs"].append(record)
        try:
            self.save()
        except OSError:
            if item.personal:
                destination.replace(item.path)
            self.config = before
            raise
        self.refresh()

    def restore_deleted(self):
        if not self.config["deleted_songs"]:
            return None
        before = copy.deepcopy(self.config)
        record = self.config["deleted_songs"][-1]
        if record.get("personal"):
            trash_name = record.get("trash_name", "")
            filename = record.get("filename", "")
            if Path(trash_name).name != trash_name or Path(filename).name != filename:
                raise ValueError("Registro de exclusão inválido.")
            source = self.directory / "lixeira" / trash_name
            destination = self.music_directory / filename
            if destination.exists():
                raise ValueError("Essa música já está na biblioteca.")
            source.replace(destination)
        else:
            self.config["hidden_songs"] = [
                i for i in self.config["hidden_songs"] if i != record["ident"]
            ]
        if record.get("favorite") and record["ident"] not in self.config["favorites"]:
            self.config["favorites"].append(record["ident"])
        self.config["deleted_songs"].pop()
        try:
            self.save()
        except OSError:
            if record.get("personal"):
                destination.replace(source)
            self.config = before
            raise
        self.refresh()
        return next((i for i in self.items if i.ident == record["ident"]), None)


def excerpt(song, offset):
    """Inicia do ponto escolhido e retoma notas ainda sustentadas nesse ponto."""
    offset = float(offset)
    if not math.isfinite(offset) or offset < 0 or offset >= song.duration:
        raise ValueError("O ponto inicial precisa estar dentro da música.")
    notes = [
        replace(
            n,
            start=max(0, n.start - offset),
            duration=n.start + n.duration - max(offset, n.start),
            gate_duration=(
                min(
                    n.start + n.duration - max(offset, n.start),
                    max(0.001, n.start + n.gate_duration - max(offset, n.start)),
                )
                if n.gate_duration is not None
                else None
            ),
        )
        for n in song.notes
        if n.start + n.duration > offset + 0.001
    ]
    metadata = dict(song.metadata)
    metadata["total_duration"] = (
        max(song.duration, float(metadata.get("total_duration", 0))) - offset
    )
    state = False
    for p in song.pedal:
        if p.time <= offset:
            state = p.down
    pedal = (
        [PedalChange(0, state)]
        + [PedalChange(p.time - offset, p.down) for p in song.pedal if p.time > offset]
        if song.pedal
        else []
    )
    return Song(song.title, notes, metadata, pedal)
