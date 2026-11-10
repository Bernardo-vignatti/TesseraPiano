"""Interpretação reproduzível: fraseado, articulação e pedal harmônico."""

from bisect import bisect_right
from dataclasses import replace
from itertools import groupby
import math
import random

from .keymap import KEY_TO_MIDI
from .analysis import TempoMap, analyze
from .music import PedalChange, Song, prepare_keyboard


def pitch(note):
    return note.pitch if note.pitch is not None else KEY_TO_MIDI[note.key]


def beat_length(song):
    tempos = song.metadata.get("tempo_map", [])
    fallback = 60 / max(40, min(240, float(song.metadata.get("bpm_reference", 120))))
    return max(0.2, min(1.5, tempos[0]["tempo"] / 1_000_000 if tempos else fallback))


def auto_pedal(song):
    """Repedaliza por contexto harmônico, respeitando pausas e articulação."""
    analysis = song.metadata.get("analysis") or analyze(song)
    tempo = TempoMap(song)
    profile = analysis["profile"]
    changes = [PedalChange(0, False)]
    last, previous_chord, previous_bass = -10.0, "", None
    for item in analysis["harmony"]:
        moment = item["time"]
        beat = tempo.length(moment)
        harmonic = item["confidence"] >= 0.55 and item["chord"] != previous_chord
        bass_change = item["bass"] != previous_bass
        maximum = beat * (1.3 if profile == "rhythmic" else 3)
        if moment - last >= maximum or (harmonic and bass_change and moment - last >= beat * 0.6):
            if moment > 0.04:
                changes.append(PedalChange(max(0, moment - 0.012), False))
            changes.append(PedalChange(moment + min(0.045, beat * 0.07), True))
            last = moment
        previous_chord, previous_bass = item["chord"], item["bass"]
    # Une intervalos de som antes de localizar respirações reais, inclusive em acordes.
    end = 0
    for note in sorted(song.notes, key=lambda n: n.start):
        beat = tempo.length(note.start)
        if note.start - end > beat * 0.6 and end > 0:
            changes.append(PedalChange(end + min(0.08, beat * 0.15), False))
        end = max(end, note.start + (note.gate_duration or note.duration))
    changes.append(PedalChange(song.duration + 0.12, False))
    result = []
    for change in sorted(changes, key=lambda p: p.time):
        if not result or result[-1].down != change.down:
            if result and change.time - result[-1].time < 0.012:
                continue
            result.append(change)
    return result


def interpret(
    song,
    style="natural",
    intensity=0.55,
    seed=17,
    pedal_mode="auto",
    speed=1.0,
    profile="auto",
    learned=False,
    adapt=True,
):
    if style not in ("original", "natural", "expressive"):
        raise ValueError("Interpretação desconhecida.")
    if pedal_mode not in ("auto", "midi", "on", "off", "ignore"):
        raise ValueError("Modo de pedal desconhecido.")
    intensity = max(0.0, min(1.0, float(intensity)))
    strength = 0 if style == "original" else intensity * (1.5 if style == "expressive" else 1)
    analysis = song.metadata.get("analysis") or analyze(song)
    selected = analysis["profile"] if profile == "auto" else profile
    analysis = dict(analysis, profile=selected)
    strength *= {"restrained": 0.65, "cantabile": 1.0, "rhythmic": 0.4}.get(selected, 1)
    if learned:
        strength = 0  # O modelo já fornece fraseado; não aplicar uma segunda humanização.
    tempo = TempoMap(song)
    beat = tempo.length(0)
    onsets = sorted({n.start for n in song.notes})
    # Arquivos gravados ao vivo já carregam desvios; o complemento fica mais discreto.
    if analysis["quantized"] < 0.45:
        strength *= 0.35
    phrases = list(analysis["phrases"])
    end = max(song.duration, onsets[-1] + 0.001)
    phrases.append(end)

    def warp(moment):
        index = min(len(phrases) - 2, max(0, bisect_right(phrases, moment) - 1))
        start, finish = phrases[index : index + 2]
        phase = min(1, max(0, (moment - start) / max(0.001, finish - start)))
        arch = (
            strength
            * min(tempo.length(moment) * 0.06, (finish - start) * 0.02)
            * math.sin(2 * math.pi * phase)
        )
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
    transformed.metadata["analysis"] = dict(
        analysis, harmony=[dict(h, time=warp(h["time"])) for h in analysis["harmony"]]
    )
    explicit = analysis["pedal_quality"] in ("valid", "explicit_off")
    resets = song.metadata.get("channel_pedal", [])
    if resets and all(not event["down"] and event["time"] <= onsets[0] + 0.05 for event in resets):
        explicit = False
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
        origin = (
            ("Modelo" if song.metadata.get("model_pedal_used") else "MIDI")
            if explicit
            else "Sem CC64"
        )
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
        analysis=transformed.metadata["analysis"],
        expression_origin="Modelo local" if learned else "Regras musicais",
        performance_style=style,
        performance_seed=seed,
        pedal_origin=origin,
        phrase_count=len(phrases) - 1,
    )
    if not adapt:
        return transformed
    prepared, adjustments = prepare_keyboard(transformed, pedal_mode, speed)
    prepared.metadata["keyboard_adjustments"] = adjustments
    return prepared
