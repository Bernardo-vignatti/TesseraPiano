from dataclasses import asdict
from pathlib import Path

import pytest

from tessera_piano.keymap import physical_key
from tessera_piano.music import Note, PedalChange, Song, held_duration, parse_song
from tessera_piano.performance import interpret
from tessera_piano.storage import Profile, normalize_settings


def passage():
    return Song(
        "Frases",
        [
            Note(key, i * 0.5, 0.42, pitch=pitch, gate_duration=0.32)
            for i, (key, pitch) in enumerate(zip("tyuotyuo", (60, 62, 64, 72, 60, 62, 64, 72)))
        ],
        {"total_duration": 4, "tempo_map": [{"time": 0, "tempo": 500000}]},
    )


def test_original_is_unchanged_and_variations_are_repeatable():
    source = passage()
    before = source.to_text()
    first = interpret(source, seed=10)
    assert source.to_text() == before
    assert [asdict(n) for n in first.notes] == [asdict(n) for n in interpret(source, seed=10).notes]
    assert any(a.start != b.start for a, b in zip(first.notes, source.notes))
    assert [asdict(n) for n in first.notes] != [asdict(n) for n in interpret(source, seed=11).notes]


def test_original_mode_retains_timing_for_playable_notes():
    source = passage()
    output = interpret(source, style="original", pedal_mode="midi")
    assert [(n.start, n.gate_duration) for n in source.notes] == [
        (n.start, n.gate_duration) for n in output.notes
    ]


@pytest.mark.parametrize("mode", ["auto", "midi", "on", "off", "ignore"])
def test_pedal_policies(mode):
    output = interpret(passage(), pedal_mode=mode)
    assert any(p.down for p in output.pedal) == (mode in ("auto", "on"))
    if output.pedal:
        assert output.pedal[-1].down is False


def test_explicit_midi_pedal_and_explicit_off_are_preserved():
    source = passage()
    source.pedal = [PedalChange(0, True), PedalChange(2, False)]
    output = interpret(source, style="original")
    assert output.pedal == source.pedal
    source.pedal = []
    source.metadata["cc64_events"] = 2
    assert interpret(source).pedal == []


def test_total_duration_includes_end_of_track():
    source = Song("Cauda", [Note("t", 0, 0.5)], {"total_duration": 2})
    assert source.duration == 2
    assert parse_song(source.to_text()).duration == 2


def test_new_note_fields_survive_roundtrip():
    note = Note("t", 0, 1, 90, 60, 0.5, 2, 3)
    restored = parse_song(Song("x", [note]).to_text()).notes[0]
    assert asdict(restored) == asdict(note)


def test_preferences_validate_every_type_and_keep_legacy_choice():
    result = normalize_settings(
        {
            "speed": None,
            "countdown": "x",
            "theme": {},
            "repeat": "false",
            "favorites": "bad",
            "pedal_mode": "ignore",
        }
    )
    assert result["speed"] == 100
    assert result["countdown"] == 5
    assert result["theme"] == "dark"
    assert result["repeat"] is False
    assert result["favorites"] == []
    assert result["pedal_mode"] == "ignore"


def test_migration_backs_up_preferences_and_preserves_library(tmp_path):
    (tmp_path / "preferencias.json").write_text(
        '{"layout":"88","pedal_mode":"ignore","favorites":["old"]}', encoding="utf-8"
    )
    profile = Profile("src/tessera_piano/resources/music", tmp_path)
    assert profile.config["layout"] == "88"
    assert profile.config["favorites"] == ["old"]
    assert profile.config["pedal_mode"] == "ignore"
    assert (tmp_path / "backups/preferencias-v3.json").exists()


@pytest.mark.parametrize("style", ["original", "natural", "expressive"])
@pytest.mark.parametrize("speed", [0.25, 1, 1.5])
def test_repertoire_has_no_overlapping_physical_keys(style, speed):
    for path in Path("src/tessera_piano/resources/music").glob("*.json"):
        source = parse_song(path.read_text(encoding="utf-8"))
        output = interpret(source, style=style, speed=speed)
        previous = {}
        for note in output.notes:
            key = physical_key(note.key)
            assert note.start >= 0 and note.duration >= 0.001
            assert 0 < note.gate_duration <= note.duration
            if key in previous:
                assert previous[key] < note.start, (path.name, key, previous[key], note.start)
            previous[key] = note.start + held_duration(note, "auto")
        assert output.duration >= max(n.start + n.duration for n in output.notes)
