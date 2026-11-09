from pathlib import Path
import tempfile
import unittest


from tessera_piano.storage import Profile, excerpt, atomic_text
from tessera_piano.music import Note, Song, parse_song
from tessera_piano.score_text import parse_score


class TesseraTests(unittest.TestCase):
    def test_preferences_favorites_and_reload(self):
        with tempfile.TemporaryDirectory() as folder:
            profile = Profile("src/tessera_piano/resources/music", folder)
            self.assertEqual(len(profile.items), 9)
            profile.config["speed"] = 80
            ident = profile.items[0].ident
            profile.favorite(ident)
            loaded = Profile("src/tessera_piano/resources/music", folder)
            self.assertEqual(loaded.config["speed"], 80)
            self.assertIn(ident, loaded.config["favorites"])
            loaded.favorite(ident)
            self.assertFalse(loaded.config["favorites"])

    def test_corrupt_config_does_not_prevent_startup(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "preferencias.json").write_text("invalid")
            profile = Profile("src/tessera_piano/resources/music", folder)
            self.assertEqual(profile.config["speed"], 100)

    def test_import_copies_and_deduplicates_song(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "personal.piano.json"
            source.write_text(Song("Teste pessoal", [Note("t", 0, 2)]).to_text(), encoding="utf-8")
            profile = Profile("src/tessera_piano/resources/music", Path(folder) / "profile")
            first = profile.import_file(source, parse_score)
            second = profile.import_file(source, parse_score)
            self.assertEqual(first.ident, second.ident)
            source.unlink()
            self.assertEqual(
                len(Profile("src/tessera_piano/resources/music", Path(folder) / "profile").items),
                10,
            )
            self.assertEqual(
                parse_song(first.path.read_text(encoding="utf-8")).title, "Teste pessoal"
            )

    def test_invalid_import_preserves_library(self):
        with tempfile.TemporaryDirectory() as folder:
            profile = Profile("src/tessera_piano/resources/music", Path(folder) / "profile")
            source = Path(folder) / "bad.json"
            source.write_text("{bad")
            with self.assertRaises(ValueError):
                profile.import_file(source, parse_score)
            self.assertEqual(len(profile.items), 9)
            self.assertFalse(list(profile.music_directory.iterdir()))

    def test_legacy_import_respects_config(self):
        with tempfile.TemporaryDirectory() as folder:
            profile = Profile("src/tessera_piano/resources/music", Path(folder) / "profile")
            profile.config.update(txt_bpm=60, txt_gate=90)
            source = Path(folder) / "notes.txt"
            source.write_text("t:2 - y")
            item = profile.import_file(source, parse_score)
            self.assertEqual(item.song.notes, [Note("t", 0, 1.8), Note("y", 3, 0.9)])

    def test_excerpt_resumes_existing_sustained_note(self):
        song = Song("x", [Note("e", 0, 4), Note("t", 0.5, 0.2), Note("y", 2, 0.5)])
        sliced = excerpt(song, 1)
        self.assertEqual(sliced.notes, [Note("e", 0, 3), Note("y", 1, 0.5)])
        self.assertEqual(song.notes[0].duration, 4)
        self.assertEqual(sliced.metadata["total_duration"], 3)

    def test_excerpt_rejects_invalid_positions(self):
        song = Song("x", [Note("e", 0, 4)])
        for offset in [-1, 4, 5]:
            with self.assertRaises(ValueError):
                excerpt(song, offset)

    def test_atomic_write_replaces_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sub/settings.json"
            atomic_text(path, "old")
            atomic_text(path, "new")
            self.assertEqual(path.read_text(encoding="utf-8"), "new")
            self.assertEqual(len(list(path.parent.iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
