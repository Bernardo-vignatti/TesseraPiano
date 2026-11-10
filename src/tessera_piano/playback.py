"""Agendamento monotônico e cancelável, independente da interface."""

import math
import time
from .music import held_duration
from .keymap import physical_key
from .analysis import TempoMap


class PlaybackStopped(Exception):
    pass


class SoftStopRequested(Exception):
    pass


def wait_deadline(deadline, cancel, keyboard, target, soft_stop=None):
    while True:
        if cancel.is_set():
            raise PlaybackStopped("Reprodução interrompida.")
        if keyboard.foreground() != target:
            raise PlaybackStopped("A janela ativa mudou; reprodução interrompida.")
        if soft_stop is not None and soft_stop.is_set():
            raise SoftStopRequested()
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            return
        cancel.wait(min(0.005, remaining))


def finish_phrase(song, moment, speed, events, active, keyboard, cancel, target, pedal_mode):
    """Saída curta com desaceleração, sem inventar notas ou ignorar uma emergência."""
    beat = TempoMap(song).length(moment)
    upcoming = sorted(
        {
            n.start
            for n in song.notes
            if moment <= n.start <= moment + min(0.32 * speed, beat * 0.65)
        }
    )
    cutoff = upcoming[0] + 0.025 * speed if upcoming else moment
    finish = moment + 0.8 * speed
    started = time.perf_counter()
    tail = []
    for base, (ident, key) in active.items():
        ending = next(
            (t for t, kind, i, _ in events if kind == 1 and i == ident), moment + 0.2 * speed
        )
        tail.append((min(finish, max(moment + 0.08 * speed, ending)), 1, ident, key))
    for at, kind, ident, note in events:
        if kind == 2 and moment <= at <= cutoff:
            tail.extend(
                (
                    (at, 2, ident, note.key),
                    (min(finish, at + min(0.35 * speed, note.duration)), 1, ident, note.key),
                )
            )
    last = 0
    for at, kind, ident, key in sorted(tail):
        offset = max(0, (at - moment) / speed)
        delayed = offset + 0.28 * offset * offset
        wait_deadline(started + delayed, cancel, keyboard, target)
        base = physical_key(key)
        if kind == 2:
            if base in active:
                keyboard.release_note(active.pop(base)[1])
            keyboard.press_note(key)
            active[base] = (ident, key)
        elif active.get(base, (None,))[0] == ident:
            keyboard.release_note(key)
            del active[base]
        last = max(last, delayed)
    if pedal_mode != "ignore":
        wait_deadline(started + last + 0.18, cancel, keyboard, target)
        keyboard.set_sustain(False)
        wait_deadline(started + last + 0.28, cancel, keyboard, target)
    raise PlaybackStopped("Parada suave concluída.")


def play_song(song, speed, keyboard, cancel, target, progress, pedal_mode="ignore", soft_stop=None):
    """Agendamento por nota; soltar uma tecla não interfere nas demais."""
    if not math.isfinite(speed) or speed <= 0:
        raise ValueError("Velocidade inválida.")
    if pedal_mode not in ("ignore", "midi", "off", "auto", "on"):
        raise ValueError("Modo de pedal inválido.")
    events = []
    for ident, note in enumerate(song.notes):
        events.append((note.start, 2, ident, note))
        events.append((note.start + held_duration(note, pedal_mode), 1, ident, note))
    if pedal_mode in ("midi", "auto", "on"):
        events.extend((p.time, 0, ident, p) for ident, p in enumerate(song.pedal))
    events.sort(key=lambda item: item[:3])  # Note-off antes de note-on no mesmo instante.
    active = {}
    total = song.duration
    started = time.perf_counter()
    last_progress = -1.0
    try:
        wait_deadline(started, cancel, keyboard, target)
        if pedal_mode != "ignore":
            keyboard.cleanup_target = target
            keyboard.set_sustain(False)
        for moment, kind, ident, note in events:
            try:
                wait_deadline(started + moment / speed, cancel, keyboard, target, soft_stop)
            except SoftStopRequested:
                now = max(0, (time.perf_counter() - started) * speed)
                finish_phrase(
                    song, now, speed, events, active, keyboard, cancel, target, pedal_mode
                )
            if kind == 0:
                keyboard.set_sustain(note.down)
                continue
            base = physical_key(note.key)
            if kind == 2:
                if base in active:
                    keyboard.release_note(active.pop(base)[1])
                keyboard.press_note(note.key)
                active[base] = (ident, note.key)
            elif active.get(base, (None,))[0] == ident:
                keyboard.release_note(note.key)
                del active[base]
            if moment - last_progress >= 0.05:
                progress(moment, total, len(active))
                last_progress = moment
        tail = max(total, float(song.metadata.get("total_duration", 0)))
        try:
            wait_deadline(started + tail / speed, cancel, keyboard, target, soft_stop)
        except SoftStopRequested:
            finish_phrase(
                song,
                (time.perf_counter() - started) * speed,
                speed,
                events,
                active,
                keyboard,
                cancel,
                target,
                pedal_mode,
            )
        progress(tail, tail, 0)
    finally:
        keyboard.release_all()
