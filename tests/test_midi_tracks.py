import mido

from tessera_piano.midi import read_midi, select_tracks
from tessera_piano.performance import interpret


def test_tracks_and_channel_specific_pedal(tmp_path):
    source = mido.MidiFile(type=1, ticks_per_beat=480)
    left = mido.MidiTrack()
    right = mido.MidiTrack()
    source.tracks.extend([left, right])
    left.extend(
        [
            mido.MetaMessage("track_name", name="Esquerda"),
            mido.Message("control_change", channel=0, control=64, value=127),
            mido.Message("note_on", channel=0, note=48, velocity=80),
            mido.Message("note_off", channel=0, note=48, velocity=0, time=480),
            mido.Message("control_change", channel=0, control=64, value=0, time=480),
        ]
    )
    right.extend(
        [
            mido.MetaMessage("track_name", name="Direita"),
            mido.Message("note_on", channel=1, note=72, velocity=90),
            mido.Message("note_off", channel=1, note=72, velocity=0, time=480),
        ]
    )
    path = tmp_path / "vozes.mid"
    source.save(path)
    song = read_midi(path)
    assert {n.track for n in song.notes} == {0, 1}
    assert {n.channel for n in song.notes} == {0, 1}
    isolated = select_tracks(song, [1])
    assert all(n.channel == 1 for n in isolated.notes)
    assert isolated.pedal == []
    assert isolated.metadata["cc64_events"] == 0
    assert interpret(isolated).metadata["pedal_origin"] == "Gerado"


def test_all_notes_off_keeps_pedal_until_release(tmp_path):
    source = mido.MidiFile()
    track = mido.MidiTrack()
    source.tracks.append(track)
    track.extend(
        [
            mido.Message("control_change", control=64, value=127),
            mido.Message("note_on", note=60, velocity=80),
            mido.Message("control_change", control=123, value=0, time=480),
            mido.Message("control_change", control=64, value=0, time=480),
        ]
    )
    path = tmp_path / "pedal.mid"
    source.save(path)
    song = read_midi(path)
    assert song.notes[0].gate_duration == 0.5
    assert song.notes[0].duration == 1


def test_initial_cc64_reset_does_not_disable_automatic_pedal(tmp_path):
    source = mido.MidiFile()
    track = mido.MidiTrack()
    source.tracks.append(track)
    track.extend(
        [
            mido.Message("control_change", control=64, value=0),
            mido.Message("note_on", note=60, velocity=80),
            mido.Message("note_off", note=60, velocity=0, time=480),
        ]
    )
    path = tmp_path / "reset.mid"
    source.save(path)
    song = read_midi(path)
    assert song.metadata["cc64_events"] == 1
    assert interpret(song, pedal_mode="auto").metadata["pedal_origin"] == "Gerado"
    assert interpret(song, pedal_mode="midi").pedal == []
