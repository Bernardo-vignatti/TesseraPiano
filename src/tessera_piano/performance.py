"""Interpretação reproduzível: fraseado, articulação e pedal harmônico."""

from bisect import bisect_right
from dataclasses import replace
from itertools import groupby
import math
import random

from .keymap import KEY_TO_MIDI
from .music import PedalChange, Song, prepare_keyboard


def pitch(note):
    return note.pitch if note.pitch is not None else KEY_TO_MIDI[note.key]


def beat_length(song):
    tempos = song.metadata.get("tempo_map", [])
    fallback = 60 / max(40, min(240, float(song.metadata.get("bpm_reference", 120))))
    return max(0.2, min(1.5, tempos[0]["tempo"] / 1_000_000 if tempos else fallback))


def auto_pedal(song):
    """Agrupa ataques e limpa a sustentação em mudanças de contexto e pausas."""
    beat = beat_length(song)
    groups = []
    for note in sorted(song.notes, key=lambda n: n.start):
        if not groups or note.start - groups[-1][0].start > min(0.055, beat * 0.12):
            groups.append([])
        groups[-1].append(note)
    if not groups:
        return []
    changes = [PedalChange(0, False)]
    last_clear = -beat
    previous_classes, previous_bass = set(), None
    previous_end = 0
    for group in groups:
        moment = group[0].start
        classes = {pitch(n) % 12 for n in group}
        bass = min(pitch(n) for n in group)
        distance = 1 - len(classes & previous_classes) / max(1, len(classes | previous_classes))
        silence = moment - previous_end > beat * 0.5
        changed_bass = bass < 65 and bass != previous_bass
        harmonic_change = distance > 0.55 and (len(group) >= 2 or changed_bass)
        if (
            last_clear < 0
            or silence
            or (moment - last_clear >= beat * 0.7 and harmonic_change)
            or moment - last_clear >= beat * 3
        ):
            if moment > 0.04:
                changes.append(
                    PedalChange(
                        max(
                            last_clear + 0.01,
                            min(moment - 0.025, previous_end + 0.04) if silence else moment - 0.025,
                        ),
                        False,
                    )
                )
            changes.append(PedalChange(moment + min(0.035, beat * 0.06), True))
            last_clear = moment
        previous_classes = classes if len(classes) >= 2 else (previous_classes | classes)
        if len(previous_classes) > 5:
            previous_classes = classes
        previous_bass = bass
        previous_end = max(n.start + (n.gate_duration or n.duration) for n in group)
    changes.append(PedalChange(song.duration + 0.12, False))
    result = []
    for change in sorted(changes, key=lambda p: p.time):
        if not result or result[-1].down != change.down:
            result.append(change)
    return result


def interpret(song, style="natural", intensity=0.55, seed=17, pedal_mode="auto", speed=1.0):
    if style not in ("original", "natural", "expressive"):
        raise ValueError("Interpretação desconhecida.")
    if pedal_mode not in ("auto", "midi", "on", "off", "ignore"):
        raise ValueError("Modo de pedal desconhecido.")
    intensity = max(0.0, min(1.0, float(intensity)))
    strength = 0 if style == "original" else intensity * (1.5 if style == "expressive" else 1)
    beat = beat_length(song)
    onsets = sorted({n.start for n in song.notes})
    # Arquivos gravados ao vivo já carregam desvios; o complemento fica mais discreto.
    quantized = sum(abs((t / (beat / 4)) - round(t / (beat / 4))) < 0.035 for t in onsets) / max(
        1, len(onsets)
    )
    if quantized < 0.45:
        strength *= 0.35
    phrases = [0.0]
    for before, current in zip(onsets, onsets[1:]):
        if (
            current - before > max(0.4, beat * 0.9) and current - phrases[-1] > beat * 2
        ) or current - phrases[-1] >= beat * 8:
            phrases.append(current)
    end = max(song.duration, onsets[-1] + 0.001)
    phrases.append(end)

    def warp(moment):
        index = min(len(phrases) - 2, max(0, bisect_right(phrases, moment) - 1))
        start, finish = phrases[index : index + 2]
        phase = min(1, max(0, (moment - start) / max(0.001, finish - start)))
        arch = strength * min(beat * 0.06, (finish - start) * 0.02) * math.sin(2 * math.pi * phase)
        final = strength * beat * 0.18 * max(0, (moment - end * 0.9) / max(0.01, end * 0.1)) ** 2
        return max(0, moment + arch + final)

    rng = random.Random(seed)
    output = []
    for _, simultaneous in groupby(
        sorted(song.notes, key=lambda n: (n.start, pitch(n))), key=lambda n: round(n.start, 3)
    ):
        chord = list(simultaneous)
        if not strength:
            output.extend(
                replace(
                    n, gate_duration=n.gate_duration if n.gate_duration is not None else n.duration
                )
                for n in chord
            )
            continue
        common = rng.uniform(-0.003, 0.003) * strength
        for index, note in enumerate(chord):
            attack = common + strength * min(0.016, index * 0.0035)
            if pitch(note) >= 64:
                attack -= strength * 0.002
            start = max(0, warp(note.start) + attack)
            original_gate = note.gate_duration if note.gate_duration is not None else note.duration
            gate = max(0.012 * speed, warp(note.start + original_gate) - start)
            # Respiração proporcional; ataques e caudas seguem a mesma curva de tempo.
            gate *= 1 - strength * 0.025
            duration = max(gate, warp(note.start + note.duration) - start)
            output.append(
                replace(note, start=start, duration=duration, gate_duration=min(gate, duration))
            )
    transformed = Song(
        song.title,
        sorted(output, key=lambda n: n.start),
        dict(song.metadata, total_duration=warp(end), source_duration=song.duration),
        [PedalChange(warp(p.time), p.down) for p in song.pedal],
    )
    explicit = bool(song.pedal or song.metadata.get("cc64_events", 0))
    if pedal_mode == "auto" and not explicit:
        transformed.pedal = auto_pedal(transformed)
        origin = "Gerado"
    elif pedal_mode == "on":
        transformed.pedal = [PedalChange(0, True), PedalChange(transformed.duration, False)]
        origin = "Ligado"
    elif pedal_mode in ("off", "ignore"):
        transformed.pedal = []
        origin = "Desligado" if pedal_mode == "off" else "Manual"
    else:
        origin = "MIDI" if explicit else "Sem CC64"
    if transformed.pedal and pedal_mode != "ignore":
        times = [p.time for p in transformed.pedal]
        clear = [p.time for p in transformed.pedal if not p.down]
        sustained = []
        for note in transformed.notes:
            gate_end = note.start + (note.gate_duration or note.duration)
            state = bisect_right(times, gate_end) - 1
            release = bisect_right(clear, gate_end)
            if state >= 0 and transformed.pedal[state].down and release < len(clear):
                note = replace(note, duration=max(note.duration, clear[release] - note.start))
            sustained.append(note)
        transformed.notes = sustained
    transformed.metadata.update(
        performance_style=style,
        performance_seed=seed,
        pedal_origin=origin,
        phrase_count=len(phrases) - 1,
    )
    prepared, adjustments = prepare_keyboard(transformed, pedal_mode, speed)
    prepared.metadata["keyboard_adjustments"] = adjustments
    return prepared
