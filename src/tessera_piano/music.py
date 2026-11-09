"""Modelo musical e formato de biblioteca compatível com piano-2."""

from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field, replace
import json
import math

from .keymap import BLACK_BASE, VALID_KEYS, KEY_TO_MIDI, fit_pitch, physical_key, layout_keys


@dataclass(frozen=True)
class Note:
    key: str
    start: float
    duration: float
    velocity: int = 80
    pitch: int | None = field(default=None, compare=False)
    gate_duration: float | None = field(default=None, compare=False)
    track: int | None = field(default=None, compare=False)
    channel: int | None = field(default=None, compare=False)


@dataclass(frozen=True)
class PedalChange:
    time: float
    down: bool  # True = sustentação ligada; Espaço SOLTO no jogo.


@dataclass
class Song:
    title: str
    notes: list[Note]
    metadata: dict = field(default_factory=dict)
    pedal: list[PedalChange] = field(default_factory=list)

    @property
    def duration(self):
        return max(
            [n.start + n.duration for n in self.notes]
            + [p.time for p in self.pedal]
            + [float(self.metadata.get("total_duration", 0))]
        )

    def to_dict(self):
        return {
            "format": "piano-2",
            "time_unit": "seconds",
            "title": self.title,
            "metadata": self.metadata,
            "notes": [
                {
                    "key": n.key,
                    "start": round(n.start, 6),
                    "duration": round(n.duration, 6),
                    "velocity": n.velocity,
                    **({"pitch": n.pitch} if n.pitch is not None else {}),
                    **(
                        {"gate_duration": round(n.gate_duration, 6)}
                        if n.gate_duration is not None
                        else {}
                    ),
                    **({"track": n.track} if n.track is not None else {}),
                    **({"channel": n.channel} if n.channel is not None else {}),
                }
                for n in self.notes
            ],
            "pedal": [{"time": round(p.time, 6), "down": p.down} for p in self.pedal],
        }

    def to_text(self):
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n"


def parse_song(text):
    obj = json.loads(text.lstrip("\ufeff"))
    if (
        not isinstance(obj, dict)
        or obj.get("format") != "piano-2"
        or obj.get("time_unit") != "seconds"
    ):
        raise ValueError("Formato esperado: piano-2, com time_unit = seconds.")
    rows = obj.get("notes")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100000:
        raise ValueError("A partitura precisa de 1 a 100.000 notas.")
    notes = []
    for i, row in enumerate(rows, 1):
        try:
            key = row["key"]
            start, duration = float(row["start"]), float(row["duration"])
            velocity = int(row.get("velocity", 80))
            pitch = row.get("pitch")
            gate = float(row["gate_duration"]) if row.get("gate_duration") is not None else None
            if (
                not isinstance(key, str)
                or key not in VALID_KEYS
                or not math.isfinite(start)
                or not math.isfinite(duration)
                or start < 0
                or duration < 0.001
                or start + duration > 7200
                or not 1 <= velocity <= 127
            ):
                raise ValueError()
            if pitch is not None and (type(pitch) is not int or not 0 <= pitch <= 127):
                raise ValueError()
            if gate is not None and (
                not math.isfinite(gate) or not 0.001 <= gate <= duration + 0.000002
            ):
                raise ValueError()
        except (KeyError, ValueError, TypeError, OverflowError):
            raise ValueError(
                f"Nota {i} inválida. Confira key, start, duration e velocity."
            ) from None
        track, channel = row.get("track"), row.get("channel")
        if track is not None and (type(track) is not int or not 0 <= track <= 65535):
            raise ValueError(f"Faixa inválida na nota {i}.")
        if channel is not None and (type(channel) is not int or not 0 <= channel <= 15):
            raise ValueError(f"Canal inválido na nota {i}.")
        notes.append(
            Note(
                key,
                start,
                duration,
                velocity,
                pitch,
                min(gate, duration) if gate is not None else None,
                track,
                channel,
            )
        )
    metadata = obj.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("metadata precisa ser um objeto JSON.")
    try:
        tail = float(metadata.get("total_duration", 0))
        if not math.isfinite(tail) or not 0 <= tail <= 7200:
            raise ValueError()
    except (TypeError, ValueError, OverflowError):
        raise ValueError("total_duration inválida nos metadados.") from None
    changes = obj.get("pedal", [])
    if not isinstance(changes, list) or len(changes) > 100000:
        raise ValueError("Lista de pedal inválida.")
    pedal = []
    for change in changes:
        try:
            moment = float(change["time"])
            down = change["down"]
            if not math.isfinite(moment) or not 0 <= moment <= 7200 or type(down) is not bool:
                raise ValueError()
        except (KeyError, TypeError, ValueError, OverflowError):
            raise ValueError("Evento de pedal inválido.") from None
        pedal.append(PedalChange(moment, down))
    return Song(
        str(obj.get("title", "Sem título")), notes, metadata, sorted(pedal, key=lambda p: p.time)
    )


def apply_layout(song, layout="61"):
    mapping = layout_keys(layout)
    notes = []
    folded = 0
    for n in song.notes:
        pitch = n.pitch if n.pitch is not None else KEY_TO_MIDI[n.key]
        fitted = fit_pitch(pitch, layout)
        folded += fitted != pitch
        notes.append(replace(n, key=mapping[fitted], pitch=pitch))
    metadata = dict(song.metadata, keyboard_layout=str(layout), octave_adjusted_notes=folded)
    metadata["legacy_pitch_recovery_unavailable"] = bool(
        song.metadata.get("octave_adjusted_notes", 0) and any(n.pitch is None for n in song.notes)
    )
    return Song(song.title, notes, metadata, list(song.pedal))


def from_steps(steps, bpm, gate, title="Partitura de teclas"):
    cursor, notes = 0.0, []
    for step in steps:
        duration = step.beats * 60 / bpm
        notes.extend(Note(key, cursor, duration * gate) for key in step.keys)
        cursor += duration
    if not notes:
        raise ValueError("A partitura só contém pausas.")
    return Song(title, notes, {"legacy": True, "total_duration": cursor})


def held_duration(note, pedal_mode="ignore"):
    return (
        note.gate_duration
        if pedal_mode != "ignore" and note.gate_duration is not None
        else note.duration
    )


def prepare_keyboard(song, pedal_mode="ignore", speed=1.0):
    """Resolve retriggers e as duas notas que compartilham uma tecla+Shift.

    Notas independentes em teclas distintas mantêm sua duração integral.
    A partitura original permanece intacta; retorna uma cópia para tocar.
    """
    grouped = defaultdict(list)
    for note in song.notes:
        grouped[physical_key(note.key)].append(note)
    output, shortened, rolled, duplicates = [], 0, 0, 0
    for group in grouped.values():
        group.sort(key=lambda n: (n.start, n.key in BLACK_BASE, n.key))
        adapted = []
        for note in group:
            if adapted:
                previous = adapted[-1]
                if abs(previous.start - note.start) < 0.000001 and previous.key == note.key:
                    adapted[-1] = replace(
                        previous,
                        duration=max(previous.duration, note.duration),
                        velocity=max(previous.velocity, note.velocity),
                        gate_duration=(
                            max(
                                previous.gate_duration
                                if previous.gate_duration is not None
                                else previous.duration,
                                note.gate_duration
                                if note.gate_duration is not None
                                else note.duration,
                            )
                            if previous.gate_duration is not None or note.gate_duration is not None
                            else None
                        ),
                    )
                    duplicates += 1
                    continue
                if note.start < previous.start + 0.018 * speed:
                    new_start = previous.start + 0.024 * speed
                    note = replace(
                        note,
                        start=new_start,
                        duration=max(0.015, note.start + note.duration - new_start),
                        gate_duration=(
                            max(0.001, note.start + note.gate_duration - new_start)
                            if note.gate_duration is not None
                            else None
                        ),
                    )
                    rolled += 1
                if (
                    previous.start + held_duration(previous, pedal_mode)
                    > note.start - 0.008 * speed
                ):
                    short = max(0.003 * speed, note.start - previous.start - 0.008 * speed)
                    if pedal_mode != "ignore" and previous.gate_duration is not None:
                        adapted[-1] = replace(previous, gate_duration=min(short, previous.duration))
                    else:
                        adapted[-1] = replace(
                            previous,
                            duration=short,
                            gate_duration=min(previous.gate_duration, short)
                            if previous.gate_duration is not None
                            else None,
                        )
                    shortened += 1
            adapted.append(note)
        output.extend(adapted)
    info = {
        "shortened_for_retrigger": shortened,
        "rolled_shared_key": rolled,
        "merged_duplicates": duplicates,
    }
    metadata = dict(song.metadata)
    metadata["keyboard_adjustments"] = info
    return Song(
        song.title, sorted(output, key=lambda n: (n.start, n.key)), metadata, list(song.pedal)
    ), info
