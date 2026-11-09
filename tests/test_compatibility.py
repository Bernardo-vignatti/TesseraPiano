from pathlib import Path
import struct
import tempfile
import threading
import unittest
from unittest.mock import patch


from tessera_piano import music as m
from tessera_piano import playback
from tessera_piano.midi import read_midi
from tessera_piano.keymap import MIDI_TO_KEY, MIDI_TO_KEY_88, key_binding, physical_key
from tessera_piano.keyboard_windows import WindowsKeyboard
from tessera_piano.score_text import parse_score
from tessera_piano.names import filename_title, clean_title
from tessera_piano.storage import Profile, excerpt


def vl(n):
    output = [n & 127]
    n >>= 7
    while n:
        output.insert(0, (n & 127) | 128)
        n >>= 7
    return bytes(output)


def smf(track):
    return (
        b"MThd"
        + struct.pack(">IHHH", 6, 0, 1, 480)
        + b"MTrk"
        + struct.pack(">I", len(track))
        + track
    )


class NewMusicTests(unittest.TestCase):
    def read(self, data, layout="61", filename="Música.mid.mid"):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / filename
            path.write_bytes(data)
            return read_midi(path, layout)

    def test_exact_88_photo_map_and_registers(self):
        self.assertEqual(set(MIDI_TO_KEY_88), set(range(21, 109)))
        self.assertEqual(
            [MIDI_TO_KEY_88[n] for n in range(21, 36)], ["ctrl+" + k for k in "1234567890qwert"]
        )
        self.assertEqual(
            [MIDI_TO_KEY_88[n] for n in range(97, 109)], ["ctrl+" + k for k in "yuiopasdfghj"]
        )
        self.assertEqual({p: MIDI_TO_KEY_88[p] for p in range(36, 97)}, MIDI_TO_KEY)
        self.assertEqual(sum(p % 12 in (0, 2, 4, 5, 7, 9, 11) for p in MIDI_TO_KEY_88), 52)
        self.assertEqual(key_binding("ctrl+5"), ("5", (0xA2,)))
        self.assertEqual(key_binding("Q"), ("q", (0xA0,)))
        self.assertEqual(physical_key("ctrl+1"), physical_key("1"))

    def test_midi_retains_original_pitch_for_layout_switch(self):
        track = (
            b"\x00\x90\x15\x50\x00\x90\x6c\x50"
            + vl(480)
            + b"\x80\x15\x00\x00\x80\x6c\x00\x00\xff\x2f\x00"
        )
        song = self.read(smf(track))
        self.assertEqual(sorted(n.pitch for n in song.notes), [21, 108])
        self.assertEqual(song.metadata["octave_adjusted_notes"], 2)
        reloaded = m.parse_song(song.to_text())
        expanded = m.apply_layout(reloaded, "88")
        self.assertEqual({n.key for n in expanded.notes}, {"ctrl+1", "ctrl+j"})
        self.assertEqual(expanded.metadata["octave_adjusted_notes"], 0)

    def test_json_validates_extended_notes_and_pedal(self):
        song = m.Song(
            "x",
            [m.Note("ctrl+1", 0, 2, pitch=21, gate_duration=0.3)],
            pedal=[m.PedalChange(0, True), m.PedalChange(2, False)],
        )
        loaded = m.parse_song(song.to_text())
        self.assertEqual(loaded.notes[0].pitch, 21)
        self.assertEqual(loaded.notes[0].gate_duration, 0.3)
        self.assertEqual(loaded.pedal, song.pedal)
        for note in [
            m.Note("ctrl+!", 0, 1),
            m.Note("t", 0, 1, pitch=200),
            m.Note("t", 0, 1, gate_duration=2),
        ]:
            with self.assertRaises(ValueError):
                m.parse_song(m.Song("x", [note]).to_text())

    def test_cc64_keeps_gate_and_sound_end_separate(self):
        track = (
            b"\x00\xb0\x40\x7f\x00\x90\x3c\x50"
            + vl(480)
            + b"\x80\x3c\x00"
            + vl(480)
            + b"\xb0\x40\x00\x00\xff\x2f\x00"
        )
        song = self.read(smf(track))
        self.assertEqual(song.notes[0].duration, 1)
        self.assertEqual(song.notes[0].gate_duration, 0.5)
        self.assertEqual(song.pedal, [m.PedalChange(0, True), m.PedalChange(1, False)])

    def test_midi_name_uses_filename_instead_of_instrument(self):
        name = b"Elec. Piano (Classic)"
        track = (
            b"\x00\xff\x03"
            + vl(len(name))
            + name
            + b"\x00\x90\x3c\x50"
            + vl(480)
            + b"\x80\x3c\x00\x00\xff\x2f\x00"
        )
        song = self.read(smf(track), filename="Minha_Canção.mid.mid")
        self.assertEqual(song.title, "Minha Canção")
        self.assertEqual(song.metadata["midi_track_names"], ["Elec. Piano (Classic)"])

    def test_native_preparation_uses_gate_instead_of_pedal_tail(self):
        song = m.Song(
            "x", [m.Note("1", 0, 3, gate_duration=0.2), m.Note("ctrl+1", 1, 0.5, gate_duration=0.3)]
        )
        native, info = m.prepare_keyboard(song, "midi")
        self.assertEqual(info["shortened_for_retrigger"], 0)
        self.assertEqual(native.notes[0].duration, 3)
        _, old = m.prepare_keyboard(song, "ignore")
        self.assertEqual(old["shortened_for_retrigger"], 1)

    def test_seek_restores_pedal_and_trims_physical_hold(self):
        song = m.Song(
            "x",
            [m.Note("t", 0, 4, pitch=60, gate_duration=0.2)],
            pedal=[m.PedalChange(0, True), m.PedalChange(4, False)],
        )
        result = excerpt(song, 1)
        self.assertEqual(result.pedal, [m.PedalChange(0, True), m.PedalChange(3, False)])
        self.assertEqual(result.notes[0].pitch, 60)
        self.assertLessEqual(result.notes[0].gate_duration, 0.002)

    def test_native_scheduler_delivers_cc64_at_exact_times(self):
        clock = [10.0]
        events = []

        class Keyboard:
            def foreground(self):
                return 123

            def set_sustain(self, value):
                events.append((round(clock[0] - 10, 3), "pedal", value))

            def press_note(self, key):
                events.append((round(clock[0] - 10, 3), "down", key))

            def release_note(self, key):
                events.append((round(clock[0] - 10, 3), "up", key))

            def release_all(self):
                events.append((round(clock[0] - 10, 3), "cleanup", None))

        def wait(deadline, *args):
            clock[0] = deadline

        song = m.Song(
            "x",
            [m.Note("t", 0, 2, gate_duration=0.25)],
            pedal=[m.PedalChange(0, True), m.PedalChange(2, False)],
        )
        with (
            patch.object(playback.time, "perf_counter", side_effect=lambda: clock[0]),
            patch.object(playback, "wait_deadline", side_effect=wait),
        ):
            playback.play_song(
                song, 1, Keyboard(), threading.Event(), 123, lambda *args: None, "midi"
            )
        self.assertEqual(
            events,
            [
                (0, "pedal", False),
                (0, "pedal", True),
                (0, "down", "t"),
                (0.25, "up", "t"),
                (2, "pedal", False),
                (2, "cleanup", None),
            ],
        )

    def test_legacy_file_can_play_without_cc64(self):
        class Keyboard:
            events = []

            def foreground(self):
                return 123

            def set_sustain(self, value):
                self.events.append(("pedal", value))

            def press_note(self, key):
                self.events.append(("down", key))

            def release_note(self, key):
                self.events.append(("up", key))

            def release_all(self):
                self.events.append(("cleanup", None))

        kb = Keyboard()
        with patch.object(playback, "wait_deadline"):
            playback.play_song(
                m.Song("x", [m.Note("t", 0, 0.2)]),
                1,
                kb,
                threading.Event(),
                123,
                lambda *a: None,
                "midi",
            )
        self.assertEqual(
            kb.events, [("pedal", False), ("down", "t"), ("up", "t"), ("cleanup", None)]
        )

    def test_old_folded_files_report_limited_recovery(self):
        song = m.Song("x", [m.Note("1", 0, 1)], {"octave_adjusted_notes": 4})
        self.assertTrue(m.apply_layout(song, "88").metadata["legacy_pitch_recovery_unavailable"])


class KeyboardTests(unittest.TestCase):
    def keyboard(self):
        kb = object.__new__(WindowsKeyboard)
        kb.owned = set()
        kb.note_labels = {}
        kb.pedal_managed = False
        kb.sustain_enabled = True
        kb.cleanup_target = 123
        kb.foreground = lambda: 123
        kb.events = []

        def send(vk, release=False):
            kb.events.append((vk, release))
            if release:
                kb.owned.discard(vk)
            else:
                kb.owned.add(vk)

        kb.send = send
        return kb

    def test_ctrl_note_releases_modifier_for_down_and_up(self):
        kb = self.keyboard()
        kb.press_note("ctrl+5")
        kb.release_note("ctrl+5")
        self.assertEqual(
            kb.events,
            [
                (0xA2, False),
                (ord("5"), False),
                (0xA2, True),
                (0xA2, False),
                (ord("5"), True),
                (0xA2, True),
            ],
        )
        self.assertFalse(kb.owned)

    def test_inverted_space_control_and_panic_cleanup(self):
        kb = self.keyboard()
        kb.set_sustain(False)
        kb.set_sustain(False)
        kb.set_sustain(True)
        self.assertEqual(kb.events, [(32, False), (32, True)])
        with patch("tessera_piano.keyboard_windows.time.sleep"):
            kb.release_all()
        self.assertFalse(kb.owned)
        self.assertFalse(kb.pedal_managed)
        self.assertEqual(kb.events[-2:], [(32, False), (32, True)])

    def test_focus_loss_only_releases_keys_without_new_space_press(self):
        kb = self.keyboard()
        kb.set_sustain(False)
        kb.press_note("ctrl+1")
        kb.events.clear()
        kb.foreground = lambda: 999
        kb.release_all()
        self.assertTrue(all(release for vk, release in kb.events))
        self.assertFalse(kb.owned)
        self.assertFalse(kb.note_labels)


class LibraryTests(unittest.TestCase):
    def personal(self, folder):
        source = Path(folder) / "Original.json"
        source.write_text(m.Song("Original", [m.Note("t", 0, 1)]).to_text())
        profile = Profile("src/tessera_piano/resources/music", Path(folder) / "profile")
        item = profile.import_file(source, parse_score)
        return source, profile, item

    def test_clean_names_and_repeated_extensions(self):
        self.assertEqual(filename_title("Canção_de_Teste.MID.mid"), "Canção de Teste")
        self.assertEqual(clean_title("ComposiÃ§Ã£o\tOriginal"), "Composição Original")

    def test_personal_delete_preserves_original_and_undo_survives_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            source, p, item = self.personal(folder)
            p.favorite(item.ident)
            p.delete(item.ident)
            self.assertTrue(source.exists())
            self.assertFalse(item.path.exists())
            p = Profile("src/tessera_piano/resources/music", Path(folder) / "profile")
            restored = p.restore_deleted()
            self.assertEqual(restored.ident, item.ident)
            self.assertTrue(restored.path.exists())
            self.assertIn(item.ident, p.config["favorites"])

    def test_bundle_delete_is_persistent_and_reversible(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Profile("src/tessera_piano/resources/music", folder)
            item = p.items[0]
            original = item.path.read_bytes()
            p.delete(item.ident)
            p = Profile("src/tessera_piano/resources/music", folder)
            self.assertEqual(len(p.items), 8)
            self.assertEqual(item.path.read_bytes(), original)
            self.assertEqual(p.restore_deleted().ident, item.ident)
            self.assertEqual(len(p.items), 9)

    def test_rename_persists_for_existing_import(self):
        with tempfile.TemporaryDirectory() as folder:
            source, p, item = self.personal(folder)
            p.rename(item.ident, "Nome correto")
            p = Profile("src/tessera_piano/resources/music", Path(folder) / "profile")
            self.assertEqual(
                next(i.song.title for i in p.items if i.ident == item.ident), "Nome correto"
            )

    def test_failed_preference_write_rolls_back_delete(self):
        with tempfile.TemporaryDirectory() as folder:
            source, p, item = self.personal(folder)
            with patch.object(p, "save", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    p.delete(item.ident)
            self.assertTrue(item.path.exists())
            self.assertFalse(p.config["deleted_songs"])

    def test_old_midi_display_name_migrates_from_source_filename(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Profile("src/tessera_piano/resources/music", folder)
            old = m.Song(
                "Elec. Piano (Classic)",
                [m.Note("t", 0, 1)],
                {"midi_format": 0, "source_file": "Minha_Música.mid.mid"},
            )
            (p.music_directory / "old.piano.json").write_text(old.to_text(), encoding="utf-8")
            p.refresh()
            item = next(i for i in p.items if i.personal)
            self.assertEqual(item.song.title, "Minha Música")


if __name__ == "__main__":
    unittest.main()
