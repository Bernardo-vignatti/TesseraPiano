"""Agendamento monotônico e cancelável, independente da interface."""

import math
import time
from .music import held_duration
from .keymap import physical_key


class PlaybackStopped(Exception):
    pass


def wait_deadline(deadline, cancel, keyboard, target):
    while True:
        if cancel.is_set():
            raise PlaybackStopped("Reprodução interrompida.")
        if keyboard.foreground() != target:
            raise PlaybackStopped("A janela ativa mudou; reprodução interrompida.")
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            return
        cancel.wait(min(0.005, remaining))


def play_song(song, speed, keyboard, cancel, target, progress, pedal_mode="ignore"):
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
            wait_deadline(started + moment / speed, cancel, keyboard, target)
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
        wait_deadline(started + tail / speed, cancel, keyboard, target)
        progress(tail, tail, 0)
    finally:
        keyboard.release_all()
