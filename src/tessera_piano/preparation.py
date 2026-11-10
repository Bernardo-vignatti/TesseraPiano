"""Análise e interpretação em cache, independentes de Qt."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

from .analysis import analyze, PROFILES
from .midi import select_tracks
from .model_pack import ModelPack, PACK_VERSION
from .music import apply_layout, parse_song, PedalChange
from .performance import interpret
from .storage import atomic_text
from .guided import manual_song

CACHE_VERSION = 1


def prepare(song, config, directory, cancel, progress=lambda value: None):
    directory = Path(directory)
    model = ModelPack(directory)
    options = {
        k: config[k]
        for k in (
            "layout",
            "track_filter",
            "performance",
            "intensity",
            "seed",
            "pedal_mode",
            "speed",
            "expression_engine",
            "expression_profile",
            "session_mode",
            "guide_arrangement",
            "guide_rollover",
        )
    }
    identity = {
        "version": CACHE_VERSION,
        "model": PACK_VERSION if model.ready() else None,
        "song": song.to_dict(),
        "options": options,
    }
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    cache = directory / "analysis-cache" / (key + ".json")
    if cache.is_file():
        try:
            return parse_song(cache.read_text(encoding="utf-8"))
        except (OSError, ValueError, KeyError, TypeError):
            pass
    selected = select_tracks(song, config["track_filter"])
    source_analysis = analyze(selected, cancel)
    selected = replace(selected, metadata=dict(selected.metadata, analysis=source_analysis))
    fallback = selected
    warning = ""
    learned = False
    if config["expression_engine"] == "model" and config["performance"] != "original":
        try:
            chosen = (
                source_analysis["profile"]
                if config["expression_profile"] == "auto"
                else config["expression_profile"]
            )
            intensity = (
                config["intensity"]
                / 100
                * {"restrained": 0.65, "cantabile": 1, "rhythmic": 0.5}[chosen]
            )
            if config["performance"] == "expressive":
                intensity = min(1, intensity * 1.35)
            if source_analysis["quantized"] < 0.45:
                intensity *= 0.35
            selected = model.render(selected, intensity, config["seed"], cancel, progress)
            selected.metadata["analysis"] = analyze(selected, cancel)
            predicted = selected.metadata.get("model_pedal", [])
            if (
                config["pedal_mode"] == "auto"
                and source_analysis["pedal_quality"] in ("missing", "resets", "suspect")
                and any(p["down"] for p in predicted)
            ):
                selected.pedal = [PedalChange(p["time"], p["down"]) for p in predicted]
                selected.metadata["analysis"]["pedal_quality"] = "valid"
                selected.metadata["channel_pedal"] = []
                selected.metadata["model_pedal_used"] = True
            learned = True
        except InterruptedError:
            raise
        except Exception as exc:
            selected = fallback
            warning = str(exc)
    if cancel.is_set():
        raise InterruptedError("Preparação cancelada.")
    selected = apply_layout(selected, config["layout"])
    result = interpret(
        selected,
        config["performance"],
        config["intensity"] / 100,
        config["seed"],
        config["pedal_mode"],
        config["speed"] / 100,
        config["expression_profile"],
        learned,
        config["session_mode"] != "guided",
    )
    analysis = result.metadata["analysis"]
    analysis["profile_label"] = PROFILES[analysis["profile"]]
    result.metadata.update(preparation_warning=warning, preparation_cache=key)
    if config["session_mode"] == "guided":
        result = manual_song(result, config["guide_arrangement"], config["guide_rollover"])
    # Uma falha transitória do modelo não se torna um resultado permanente em cache.
    if not warning:
        atomic_text(cache, result.to_text())
        files = sorted(cache.parent.glob("*.json"), key=lambda p: p.stat().st_mtime)
        for old in files[:-64]:
            old.unlink(missing_ok=True)
    return result
