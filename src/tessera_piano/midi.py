"""Conversão de SMF para notas, pedal e metadados de tempo do Tessera."""

from collections import defaultdict, deque
from dataclasses import replace
from pathlib import Path

import mido

from .keymap import fit_pitch, layout_keys
from .music import Note, PedalChange, Song
from .names import filename_title

MAX_IMPORT_BYTES = 32 * 1024 * 1024
MAX_EVENTS = 500_000


def read_midi(path, layout="61"):
    path = Path(path)
    if path.stat().st_size > MAX_IMPORT_BYTES:
        raise ValueError("O arquivo excede o limite de 32 MB.")
    try:
        midi = mido.MidiFile(path, clip=False)
    except (EOFError, OSError, ValueError, KeyError, IndexError) as exc:
        raise ValueError("MIDI inválido ou incompleto.") from exc
    if midi.type not in (0, 1) or midi.ticks_per_beat <= 0:
        raise ValueError("Importação aceita MIDI SMF 0/1 com tempo PPQN.")
    if sum(len(t) for t in midi.tracks) > MAX_EVENTS:
        raise ValueError("O MIDI contém eventos demais para importar.")
    events = []
    tracks = []
    for track_id, track in enumerate(midi.tracks):
        tick = 0
        channels = set()
        for index, message in enumerate(track):
            tick += message.time
            if not message.is_meta and hasattr(message, "channel"):
                channels.add(message.channel)
            events.append((tick, track_id, index, message))
        tracks.append({"id": track_id, "name": track.name, "channels": sorted(channels)})
    events.sort(key=lambda event: event[:3])
    active, deferred = defaultdict(deque), defaultdict(list)
    sustain = defaultdict(bool)
    notes, pedal, tempo_map, signatures = [], [], [], []
    channel_pedal = []
    seconds, previous, tempo, drum_count, cc64_count = 0.0, 0, 500000, 0, 0
    mapping = layout_keys(layout)
    folded = 0

    def finish(pitch, start, velocity, end, gate_end, track, channel):
        nonlocal folded
        if end <= start:
            return
        fitted = fit_pitch(pitch, layout)
        folded += fitted != pitch
        duration = max(0.001, end - start)
        notes.append(
            Note(
                mapping[fitted],
                start,
                duration,
                velocity,
                pitch,
                min(duration, max(0.001, gate_end - start)),
                track,
                channel,
            )
        )
        if len(notes) > 100_000:
            raise ValueError("A música excede o limite de 100.000 notas.")

    def release_deferred(channel):
        for pitch, start, velocity, gate_end, track in deferred.pop(channel, []):
            finish(pitch, start, velocity, seconds, gate_end, track, channel)

    for tick, track, _, message in events:
        seconds += mido.tick2second(tick - previous, midi.ticks_per_beat, tempo)
        previous = tick
        if seconds > 7200:
            raise ValueError("A música excede o limite de duas horas.")
        if message.is_meta:
            if message.type == "set_tempo":
                tempo = message.tempo
                if tempo <= 0:
                    raise ValueError("Tempo MIDI inválido.")
                tempo_map.append({"time": seconds, "tick": tick, "tempo": tempo})
            elif message.type == "time_signature":
                signatures.append(
                    {
                        "time": seconds,
                        "numerator": message.numerator,
                        "denominator": message.denominator,
                    }
                )
            continue
        channel = getattr(message, "channel", None)
        if channel == 9:
            drum_count += message.type == "note_on" and message.velocity > 0
            continue
        if message.type == "note_on" and message.velocity:
            active[channel, message.note].append((seconds, message.velocity, track))
        elif message.type == "note_off" or message.type == "note_on":
            held = active[channel, message.note]
            if held:
                start, velocity, origin = held.popleft()
                if sustain[channel]:
                    deferred[channel].append((message.note, start, velocity, seconds, origin))
                else:
                    finish(message.note, start, velocity, seconds, seconds, origin, channel)
        elif message.type == "control_change":
            before = any(sustain.values())
            if message.control == 64:
                cc64_count += 1
                sustain[channel] = message.value >= 64
                channel_pedal.append(
                    {"time": seconds, "channel": channel, "down": sustain[channel]}
                )
                if not sustain[channel]:
                    release_deferred(channel)
            elif message.control == 121:
                sustain[channel] = False
                channel_pedal.append({"time": seconds, "channel": channel, "down": False})
                release_deferred(channel)
            elif message.control in (120, 123):
                for (ch, pitch), held in active.items():
                    if ch != channel:
                        continue
                    while held:
                        start, velocity, origin = held.popleft()
                        if message.control == 123 and sustain[channel]:
                            deferred[channel].append((pitch, start, velocity, seconds, origin))
                        else:
                            finish(pitch, start, velocity, seconds, seconds, origin, channel)
                if message.control == 120:
                    release_deferred(channel)
            if before != any(sustain.values()):
                pedal.append(PedalChange(seconds, any(sustain.values())))
    for (channel, pitch), held in active.items():
        for start, velocity, track in held:
            finish(pitch, start, velocity, seconds, seconds, track, channel)
    for channel in list(deferred):
        release_deferred(channel)
    if not notes:
        raise ValueError("O MIDI não contém notas melódicas utilizáveis.")
    return Song(
        filename_title(path.name),
        sorted(notes, key=lambda n: (n.start, n.key)),
        {
            "source_file": path.name,
            "midi_format": midi.type,
            "ticks_per_beat": midi.ticks_per_beat,
            "tempo_events": len(tempo_map),
            "tempo_map": tempo_map,
            "time_signatures": signatures,
            "tracks": tracks,
            "midi_track_names": [track.name for track in midi.tracks if track.name],
            "octave_adjusted_notes": folded,
            "drum_notes_ignored": drum_count,
            "total_duration": seconds,
            "velocity_preserved_not_transmitted": True,
            "cc64_events": cc64_count,
            "channel_pedal": channel_pedal,
            "keyboard_layout": str(layout),
        },
        pedal,
    )


def select_tracks(song, selected):
    if not selected:
        return song
    notes = [n for n in song.notes if n.track is None or n.track in selected]
    if not notes:
        raise ValueError("As faixas selecionadas não contêm notas.")
    metadata = dict(song.metadata)
    pedal = list(song.pedal)
    if "channel_pedal" in metadata:
        channels = {n.channel for n in notes}
        relevant = [p for p in metadata["channel_pedal"] if p["channel"] in channels]
        states = {}
        pedal = []
        for event in relevant:
            before = any(states.values())
            states[event["channel"]] = event["down"]
            if before != any(states.values()):
                pedal.append(PedalChange(event["time"], any(states.values())))
        metadata["cc64_events"] = len(relevant)
    return replace(song, notes=notes, pedal=pedal, metadata=metadata)
