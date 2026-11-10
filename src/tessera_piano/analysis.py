"""Análise simbólica leve; as estimativas não alteram a partitura de origem."""

from bisect import bisect_right
from collections import Counter
from itertools import groupby
from statistics import median

from .keymap import KEY_TO_MIDI

ANALYSIS_VERSION = 1
PROFILES = {"restrained": "Contido", "cantabile": "Cantabile", "rhythmic": "Rítmico"}
NAMES = ("C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B")


def pitch(note):
    return note.pitch if note.pitch is not None else KEY_TO_MIDI[note.key]


class TempoMap:
    def __init__(self, song):
        entries = [(0.0, 60 / max(20, min(400, song.metadata.get("bpm_reference", 120))))]
        entries.extend(
            (float(e["time"]), max(0.15, min(3, e["tempo"] / 1_000_000)))
            for e in song.metadata.get("tempo_map", [])
        )
        self.times, self.lengths, self.beats = [], [], []
        for moment, length in sorted(dict(entries).items()):
            previous = self.times[-1] if self.times else 0
            beats = self.beats[-1] + (moment - previous) / self.lengths[-1] if self.times else 0
            self.times.append(moment)
            self.lengths.append(length)
            self.beats.append(beats)

    def length(self, moment):
        return self.lengths[max(0, bisect_right(self.times, moment) - 1)]

    def beat(self, moment):
        i = max(0, bisect_right(self.times, moment) - 1)
        return self.beats[i] + (moment - self.times[i]) / self.lengths[i]


def pedal_quality(song):
    changes = song.metadata.get("channel_pedal", [])
    if changes and all(not p["down"] and p["time"] <= song.notes[0].start + 0.05 for p in changes):
        return "resets"
    if not song.pedal:
        return "explicit_off" if song.metadata.get("cc64_events", 0) else "missing"
    if not any(p.down for p in song.pedal):
        return "explicit_off"
    return (
        "valid"
        if any(not p.down and p.time > song.pedal[0].time for p in song.pedal)
        else "suspect"
    )


def chord(context):
    weights = Counter()
    for note, weight in context:
        weights[pitch(note) % 12] += weight
    if not weights:
        return "", 0.0
    bass = min(pitch(n) for n, _ in context) % 12
    best = (-1, 0, "", ())
    for root in range(12):
        for suffix, intervals in (
            ("", (0, 4, 7)),
            ("m", (0, 3, 7)),
            ("dim", (0, 3, 6)),
            ("7", (0, 4, 7, 10)),
        ):
            pcs = {(root + i) % 12 for i in intervals}
            present = sum(weights.get(p, 0) for p in pcs)
            score = present - 0.65 * sum(v for p, v in weights.items() if p not in pcs)
            score += 0.25 * weights.get(root, 0) + (0.25 if bass == root else 0)
            if score > best[0]:
                best = score, root, suffix, pcs
    _, root, suffix, pcs = best
    confidence = min(1, sum(p in weights for p in pcs) / len(pcs))
    confidence *= sum(weights.get(p, 0) for p in pcs) / max(0.01, sum(weights.values()))
    name = NAMES[root] + suffix
    if bass != root and bass in pcs:
        name += "/" + NAMES[bass]
    return name, round(confidence, 2)


def analyze(song, cancel=None):
    notes = sorted(song.notes, key=lambda n: (n.start, pitch(n)))
    tempo = TempoMap(song)
    groups = [list(g) for _, g in groupby(notes, key=lambda n: round(n.start, 2))]
    phrases, harmony, recent = [0.0], [], []
    previous = 0.0
    next_window = -1.0
    quantized = 0
    for index, group in enumerate(groups):
        if cancel is not None and index % 64 == 0 and cancel.is_set():
            raise InterruptedError("Preparação cancelada.")
        moment = group[0].start
        beat = tempo.length(moment)
        quantized += abs(tempo.beat(moment) * 4 - round(tempo.beat(moment) * 4)) < 0.045
        gap = moment - previous
        if (gap > beat * 0.9 and moment - phrases[-1] > beat * 2) or tempo.beat(
            moment
        ) - tempo.beat(phrases[-1]) >= 8:
            phrases.append(moment)
        previous = max(previous, max(n.start + (n.gate_duration or n.duration) for n in group))
        recent = [
            n for n in recent if n.start + max(n.gate_duration or n.duration, beat * 0.8) > moment
        ]
        recent.extend(group)
        if moment >= next_window:
            current_ids = {id(n) for n in group}
            context = [(n, 1.5 if id(n) in current_ids else 0.65) for n in recent]
            name, confidence = chord(context)
            bass = min(pitch(n) for n in recent)
            harmony.append({"time": moment, "chord": name, "confidence": confidence, "bass": bass})
            next_window = moment + beat * 0.7
    density = len(notes) / max(1, song.duration)
    gate_ratio = median((n.gate_duration or n.duration) / tempo.length(n.start) for n in notes)
    profile = (
        "rhythmic"
        if density > 5 or gate_ratio < 0.3
        else "cantabile"
        if gate_ratio > 0.65
        else "restrained"
    )
    confidence = min(0.95, 0.5 + abs(gate_ratio - 0.5) * 0.3 + min(density, 10) * 0.02)
    return {
        "version": ANALYSIS_VERSION,
        "profile": profile,
        "profile_label": PROFILES[profile],
        "confidence": round(confidence, 2),
        "quantized": quantized / max(1, len(groups)),
        "phrases": phrases,
        "harmony": harmony,
        "pedal_quality": pedal_quality(song),
        "density": round(density, 2),
    }
