from pathlib import Path
import struct
import tempfile
import threading
import unittest
from unittest.mock import patch


from tessera_piano import music as m
from tessera_piano import playback
from tessera_piano.midi import read_midi
from tessera_piano.keymap import physical_key


def varlen(n):
    output = [n & 127]
    n >>= 7
    while n:
        output.insert(0, (n & 127) | 128)
        n >>= 7
    return bytes(output)


def midi(*tracks, fmt=0, division=480):
    return (
        b"MThd"
        + struct.pack(">IHHH", 6, fmt, len(tracks), division)
        + b"".join(b"MTrk" + struct.pack(">I", len(track)) + track for track in tracks)
    )


class MusicTests(unittest.TestCase):
    def read(self, data):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.mid"
            path.write_bytes(data)
            return read_midi(path)

    def test_json_overlap_roundtrip(self):
        song = m.Song("Sobreposição", [m.Note("e", 0, 4), m.Note("t", 1, 0.25)])
        result = m.parse_song(song.to_text())
        self.assertEqual(song.notes, result.notes)
        self.assertEqual(result.duration, 4)

    def test_json_validation(self):
        for note in [
            m.Note("?", 0, 1),
            m.Note("t", -1, 1),
            m.Note("t", 0, 0),
            m.Note("t", float("nan"), 1),
        ]:
            with self.assertRaises(ValueError):
                m.parse_song(m.Song("x", [note]).to_text())
        for value in ["infinity", float("inf"), -3]:
            with self.assertRaises(ValueError):
                m.parse_song(m.Song("x", [m.Note("t", 0, 1)], {"total_duration": value}).to_text())

    def test_legacy_timing_preserved(self):
        class Step:
            def __init__(self, keys, beats):
                self.keys, self.beats = keys, beats

        song = m.from_steps([Step("adg", 2), Step("", 1), Step("t", 1)], 120, 0.8)
        self.assertEqual(
            song.notes,
            [m.Note("a", 0, 0.8), m.Note("d", 0, 0.8), m.Note("g", 0, 0.8), m.Note("t", 1.5, 0.4)],
        )
        self.assertEqual(song.metadata["total_duration"], 2)

    def test_physical_conflict_adaptation(self):
        song = m.Song("x", [m.Note("q", 0, 3), m.Note("Q", 0, 2), m.Note("t", 0, 4)])
        prepared, info = m.prepare_keyboard(song)
        self.assertEqual(song.notes[0].duration, 3)
        q = next(n for n in prepared.notes if n.key == "q")
        sharp = next(n for n in prepared.notes if n.key == "Q")
        self.assertLess(q.start + q.duration, sharp.start)
        self.assertEqual(next(n for n in prepared.notes if n.key == "t").duration, 4)
        self.assertEqual(info["rolled_shared_key"], 1)

    def test_midi_tempo_map(self):
        track = (
            b"\x00\xff\x51\x03\x07\xa1\x20"
            + b"\x00\x90\x3c\x5a"
            + varlen(480)
            + b"\xff\x51\x03\x0f\x42\x40"
            + varlen(480)
            + b"\x80\x3c\x00"
            + b"\x00\xff\x2f\x00"
        )
        song = self.read(midi(track))
        self.assertEqual(song.notes, [m.Note("t", 0, 1.5, 90)])
        self.assertEqual(song.metadata["tempo_events"], 2)

    def test_midi_running_status(self):
        track = (
            b"\x00\x90\x3c\x50"
            + varlen(240)
            + b"\x40\x60"
            + varlen(240)
            + b"\x3c\x00"
            + varlen(240)
            + b"\x40\x00\x00\xff\x2f\x00"
        )
        song = self.read(midi(track))
        self.assertEqual(song.notes, [m.Note("t", 0, 0.5, 80), m.Note("u", 0.25, 0.5, 96)])

    def test_midi_sustain_independent_notes(self):
        track = (
            b"\x00\xb0\x40\x7f\x00\x90\x3c\x50"
            + varlen(240)
            + b"\x90\x40\x60"
            + varlen(240)
            + b"\x80\x3c\x00"
            + varlen(240)
            + b"\x80\x40\x00"
            + varlen(240)
            + b"\xb0\x40\x00\x00\xff\x2f\x00"
        )
        song = self.read(midi(track))
        self.assertEqual(song.notes, [m.Note("t", 0, 1, 80), m.Note("u", 0.25, 0.75, 96)])

    def test_midi_type1_tracks_and_range(self):
        tempo = b"\x00\xff\x51\x03\x0f\x42\x40" + varlen(480) + b"\xff\x2f\x00"
        notes = b"\x00\x90\x18\x50" + varlen(480) + b"\x80\x18\x00\x00\xff\x2f\x00"
        song = self.read(midi(tempo, notes, fmt=1))
        self.assertEqual(song.notes, [m.Note("1", 0, 1, 80)])
        self.assertEqual(song.metadata["octave_adjusted_notes"], 1)

    def test_midi_rejects_corrupt_and_unsupported(self):
        for blob in [
            b"bad",
            midi(b"\x00\xff\x2f\x00", fmt=2),
            midi(b"\x00\xff\x2f\x00", division=0xE728),
            midi(b"\x00\x90\x3c"),
        ]:
            with self.assertRaises(ValueError):
                self.read(blob)

    def run_player(self, song, hook=None, prepare=True):
        now = [10.0]
        cancel = threading.Event()

        class Keyboard:
            def __init__(self):
                self.held = set()
                self.events = []

            def foreground(self):
                return 123

            def press_note(self, key):
                self.held.add(key)
                self.events.append((round(now[0] - 10, 5), "on", key, set(self.held)))
                if hook:
                    hook(self, cancel)

            def release_note(self, key):
                self.held.discard(key)
                self.events.append((round(now[0] - 10, 5), "off", key, set(self.held)))

            def release_all(self):
                self.held.clear()

        kb = Keyboard()

        def wait(deadline, event, keyboard, target, soft_stop=None):
            if cancel.is_set():
                raise playback.PlaybackStopped()
            now[0] = deadline

        if prepare:
            song, _ = m.prepare_keyboard(song)
        with (
            patch.object(playback.time, "perf_counter", side_effect=lambda: now[0]),
            patch.object(playback, "wait_deadline", side_effect=wait),
        ):
            try:
                playback.play_song(song, 1, kb, cancel, 123, lambda *args: None)
            except playback.PlaybackStopped:
                pass
        return kb

    def test_bass_stays_held_while_melody_releases(self):
        kb = self.run_player(
            m.Song("test", [m.Note("e", 0, 4), m.Note("t", 0.5, 0.2), m.Note("y", 1, 0.2)])
        )
        t_off = next(e for e in kb.events if e[1:3] == ("off", "t"))
        self.assertIn("e", t_off[3])
        self.assertEqual(next(e[0] for e in kb.events if e[1:3] == ("off", "e")), 4)
        self.assertFalse(kb.held)

    def test_stale_noteoff_does_not_cut_new_shared_key(self):
        kb = self.run_player(m.Song("x", [m.Note("q", 0, 2), m.Note("Q", 0.5, 3)]), prepare=False)
        self.assertEqual(
            [e[:3] for e in kb.events],
            [(0, "on", "q"), (0.5, "off", "q"), (0.5, "on", "Q"), (3.5, "off", "Q")],
        )

    def test_cancel_releases_held_polyphony(self):
        kb = self.run_player(
            m.Song("x", [m.Note("e", 0, 50), m.Note("t", 1, 3)]), hook=lambda kb, event: event.set()
        )
        self.assertFalse(kb.held)
        self.assertEqual(len(kb.events), 1)

    def test_focus_change_stops_before_attack(self):
        class Keyboard:
            cleaned = False

            def foreground(self):
                return 999

            def press_note(self, key):
                self.fail("Must not send a note")

            def release_all(self):
                self.cleaned = True

        kb = Keyboard()
        with self.assertRaises(playback.PlaybackStopped):
            playback.play_song(
                m.Song("x", [m.Note("t", 0, 4)]), 1, kb, threading.Event(), 123, lambda *args: None
            )
        self.assertTrue(kb.cleaned)

    def test_every_bundled_piece_has_safe_keyboard_timeline(self):
        files = list(Path("src/tessera_piano/resources/music").glob("*.piano.json"))
        self.assertEqual(len(files), 9)
        for path in files:
            with self.subTest(path=path.name):
                song = m.parse_song(path.read_text(encoding="utf-8"))
                prepared, _ = m.prepare_keyboard(song)
                previous = {}
                for note in prepared.notes:
                    base = physical_key(note.key)
                    if base in previous:
                        self.assertLess(previous[base], note.start)
                    previous[base] = note.start + note.duration
                self.assertTrue(any(n.duration > 0.6 for n in song.notes))


if __name__ == "__main__":
    unittest.main()
