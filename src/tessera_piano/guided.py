"""Orientação de entrada física; este módulo nunca injeta teclas no sistema."""

from bisect import bisect_right
from dataclasses import replace
from itertools import groupby
from statistics import median
import time

from .analysis import pitch
from .keymap import key_binding, physical_key, KEY_TO_MIDI
from .music import Song, PedalChange
from .playback import PlaybackStopped, wait_deadline


def groups(song):
    return [
        list(g)
        for _, g in groupby(
            sorted(song.notes, key=lambda n: n.start), key=lambda n: round(n.start, 2)
        )
    ]


def manual_song(song, arrangement="full", rollover=10):
    if song.metadata.get("manual_arrangement") == arrangement:
        return song
    if arrangement == "distributed":
        output, boundaries = [], []
        shift, previous_end = 0, -0.06
        for group in groups(song):
            moment = group[0].start
            shift = max(shift, previous_end + 0.06 - moment)
            parts = []
            for note in sorted(group, key=pitch):
                binding = key_binding(note.key)
                part = next(
                    (
                        p
                        for p in parts
                        if len(p) < max(1, rollover - 2)
                        and key_binding(p[0].key)[1] == binding[1]
                        and all(physical_key(n.key) != binding[0] for n in p)
                    ),
                    None,
                )
                if part is None:
                    parts.append([note])
                else:
                    part.append(note)
            boundaries.append((moment, moment + shift))
            for i, part in enumerate(parts):
                start = moment + shift + i * 0.2
                for note in part:
                    gate = max(0.02, min(0.14, note.gate_duration or note.duration))
                    output.append(replace(note, start=start, duration=gate, gate_duration=gate))
                previous_end = start + 0.14
        starts = [b[0] for b in boundaries]

        def warp(moment):
            i = max(0, bisect_right(starts, moment) - 1)
            if i + 1 == len(starts) or starts[i + 1] == starts[i]:
                return max(0, boundaries[i][1] + moment - starts[i])
            ratio = (moment - starts[i]) / (starts[i + 1] - starts[i])
            return max(0, boundaries[i][1] + ratio * (boundaries[i + 1][1] - boundaries[i][1]))

        metadata = dict(
            song.metadata,
            manual_arrangement=arrangement,
            total_duration=max(previous_end, warp(song.duration)),
        )
        metadata["tempo_map"] = [
            dict(e, time=warp(e["time"])) for e in song.metadata.get("tempo_map", [])
        ]
        return Song(
            song.title,
            sorted(output, key=lambda n: n.start),
            metadata,
            [PedalChange(warp(p.time), p.down) for p in song.pedal],
        )
    if arrangement != "melody":
        return song
    chosen = [max(g, key=pitch) for g in groups(song)]
    output = []
    for i, note in enumerate(chosen):
        space = chosen[i + 1].start - note.start if i + 1 < len(chosen) else 0.5
        gate = max(0.001, min(note.gate_duration or note.duration, max(0.001, space - 0.06)))
        output.append(replace(note, duration=gate, gate_duration=gate))
    return Song(
        song.title, output, dict(song.metadata, manual_arrangement=arrangement), list(song.pedal)
    )


def manual_issues(song, rollover=10):
    issues = 0
    active = []
    for group in groups(song):
        moment = group[0].start
        active = [n for n in active if n.start + (n.gate_duration or n.duration) > moment + 0.025]
        notes = active + group
        bindings = [key_binding(n.key) for n in notes]
        bases = {b for b, _ in bindings}
        modifiers = {m for _, m in bindings}
        count = len(bases) + max((len(m) for m in modifiers), default=0) + 1
        if len(modifiers) > 1 or len(bases) < len(bindings) or count > rollover:
            issues += 1
        active.extend(group)
    return issues


def lights(active, upcoming, pedal, phase, palette="amber"):
    now, future = (
        ((245, 189, 103), (45, 68, 100)) if palette == "amber" else ((92, 211, 204), (91, 49, 120))
    )
    result = {}
    for notes, color in ((upcoming, future), (active, now)):
        for note in notes:
            base, mods = key_binding(note.key)
            result[base] = color
            for modifier in mods:
                result["shift" if modifier == 0xA0 else "ctrl"] = color
    if active:
        pulse = 1 if phase < 0.12 else 0.65
        for note in active:
            result[physical_key(note.key)] = tuple(int(c * pulse) for c in now)
    if pedal is False:
        result["space"] = (160, 100, 185)
    return result


def guide_song(song, speed, keyboard, cancel, target, chroma, config, progress, soft_stop=None):
    practice = config["guide_mode"] == "practice"
    sequence = groups(song)
    sequence_times = [g[0].start for g in sequence]
    ordered = sorted(song.notes, key=lambda n: n.start)
    visual_cursor, visual_active = 0, []
    started = time.perf_counter()
    index, hits, misses = 0, 0, 0
    expected = sequence[0]
    previous = set()
    recent_presses = []
    confirmed = set()
    errors = []
    accepted = False
    reached = None
    next_frame = 0
    pedal_times = [p.time for p in song.pedal]
    bindings = {n.key: key_binding(n.key) for n in song.notes}
    virtual = {ord(base.upper()) for base, _ in bindings.values()}
    while index < len(sequence):
        wait_deadline(time.perf_counter(), cancel, keyboard, target)
        if soft_stop is not None and soft_stop.is_set():
            for value in (0.7, 0.4, 0.15, 0):
                chroma.frame(
                    {
                        k: tuple(int(c * value) for c in rgb)
                        for k, rgb in lights(expected, [], None, 0, config["guide_palette"]).items()
                    }
                )
                wait_deadline(time.perf_counter() + 0.08, cancel, keyboard, target)
            raise PlaybackStopped("Orientação encerrada suavemente.")
        now = time.perf_counter()
        position = expected[0].start if practice else max(0, (now - started) * speed)
        if not practice:
            while index + 1 < len(sequence) and position >= sequence[index + 1][0].start:
                hits += len(confirmed)
                misses += len(expected) - len(confirmed)
                index += 1
                expected = sequence[index]
                confirmed = set()
        down = {vk for vk in virtual if keyboard.down(vk)}
        modifiers = tuple(
            vk for vk, generic in ((0xA0, 0x10), (0xA2, 0x11)) if keyboard.down(generic)
        )
        pressed = down - previous
        previous = down
        recent_presses = [p for p in recent_presses if now - p[0] <= 0.23]
        recent_presses.extend((now, vk, modifiers) for vk in pressed)
        for note in expected:
            base, mods = bindings[note.key]
            if note.key in confirmed:
                continue
            for press in list(recent_presses):
                error = (press[0] - started) - note.start / speed
                if (
                    press[1] == ord(base.upper())
                    and press[2] == mods
                    and (practice or abs(error) <= 0.22)
                ):
                    confirmed.add(note.key)
                    recent_presses.remove(press)
                    if not practice:
                        errors.append(error)
                    break
        pedal_i = bisect_right(pedal_times, expected[0].start) - 1
        pedal_correct = pedal_i < 0 or bool(keyboard.down(0x20)) == (not song.pedal[pedal_i].down)
        all_correct = len(confirmed) == len(expected) and pedal_correct
        if practice:
            if all_correct and not accepted:
                hits += len(expected)
                accepted = True
                reached = now
            # Depois do acorde, respeitar a duração antes de pedir o próximo ataque.
            advance = accepted and now - reached >= max(
                0.08, max(n.gate_duration or n.duration for n in expected) / speed
            )
        else:
            limit = max(n.start + (n.gate_duration or n.duration) for n in expected)
            advance = index == len(sequence) - 1 and position >= max(
                expected[0].start + 0.22 * speed, limit
            )
            if advance:
                hits += len(confirmed)
                misses += len(expected) - len(confirmed)
        if now >= next_frame:
            if practice:
                light_position = position
                active, following, phase = expected, [], 0
            else:
                light_position = position + config.get("guide_latency", 0) / 1000 * speed
                visual_index = max(0, bisect_right(sequence_times, light_position) - 1)
                while (
                    visual_cursor < len(ordered) and ordered[visual_cursor].start <= light_position
                ):
                    visual_active.append(ordered[visual_cursor])
                    visual_cursor += 1
                visual_active = [
                    n
                    for n in visual_active
                    if n.start + (n.gate_duration or n.duration) > light_position
                ]
                active = visual_active
                following = sequence[visual_index + 1] if visual_index + 1 < len(sequence) else []
                if following and (
                    following[0].start - light_position > config["guide_lead"] / 1000 * speed
                ):
                    following = []
                phase = (light_position - sequence[visual_index][0].start) / speed
            pedal_i = bisect_right(pedal_times, light_position) - 1
            pedal = song.pedal[pedal_i].down if pedal_i >= 0 else None
            chroma.frame(lights(active, following, pedal, phase, config["guide_palette"]))
            progress(
                position,
                {
                    "hits": hits + (len(confirmed) if not practice and not advance else 0),
                    "misses": misses,
                    "total": len(song.notes),
                    "timing_ms": round(median(errors) * 1000) if errors else 0,
                },
                [KEY_TO_MIDI[n.key] for n in active],
            )
            next_frame = now + 0.033
        if advance:
            index += 1
            if index < len(sequence):
                expected = sequence[index]
                confirmed = set()
                accepted = False
                reached = None
        cancel.wait(0.005)
    return {
        "hits": hits,
        "misses": misses,
        "total": len(song.notes),
        "timing_ms": round(median(errors) * 1000) if errors else 0,
    }
