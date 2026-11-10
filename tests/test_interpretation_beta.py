import base64
import hashlib
from io import BytesIO
import threading
from unittest.mock import patch
import zipfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import pytest

from tessera_piano.analysis import TempoMap, analyze, pedal_quality
from tessera_piano.chroma import Chroma, KEY_POSITIONS
from tessera_piano.guided import manual_song, manual_issues, lights, guide_song
from tessera_piano.keymap import MIDI_TO_KEY_88
from tessera_piano.model_pack import ModelPack, apply_render, verify_pack, PACK_VERSION
from tessera_piano.music import Note, Song, PedalChange
from tessera_piano import playback, updates
from tessera_piano.preparation import prepare
from tessera_piano.storage import normalize_settings, excerpt


def passage():
    return Song(
        "Teste",
        [Note("t", 0, 0.3, pitch=60), Note("u", 0.5, 0.3, pitch=64), Note("o", 1, 0.3, pitch=67)],
        {"tempo_map": [{"time": 0, "tempo": 500000}, {"time": 0.5, "tempo": 1000000}]},
    )


def test_tempo_map_uses_all_segments_and_excerpt_keeps_active_tempo():
    song = passage()
    tempo = TempoMap(song)
    assert tempo.length(0.25) == 0.5 and tempo.length(0.75) == 1
    assert tempo.beat(1.5) == 2
    assert TempoMap(excerpt(song, 0.7)).length(0) == 1


def test_analysis_harmony_inversion_and_preserves_source():
    song = Song("Acorde", [Note(MIDI_TO_KEY_88[p], 0, 1, pitch=p) for p in (64, 67, 72)])
    before = song.to_text()
    result = analyze(song)
    assert result["harmony"][0]["chord"] == "C/E"
    assert result["harmony"][0]["confidence"] == 1
    assert song.to_text() == before


@pytest.mark.parametrize(
    "pedal,metadata,quality",
    [
        ([], {}, "missing"),
        ([], {"cc64_events": 2}, "explicit_off"),
        ([PedalChange(0, True)], {}, "suspect"),
        ([PedalChange(0, True), PedalChange(1, False)], {}, "valid"),
        ([], {"channel_pedal": [{"time": 0, "down": False}]}, "resets"),
    ],
)
def test_pedal_quality_distinguishes_intent(pedal, metadata, quality):
    assert pedal_quality(Song("x", [Note("t", 0, 1)], metadata, pedal)) == quality


def test_preparation_is_cached_without_mutating_original(tmp_path):
    song = passage()
    before = song.to_text()
    config = normalize_settings({})
    first = prepare(song, config, tmp_path, threading.Event())
    with patch("tessera_piano.preparation.analyze", side_effect=AssertionError("cache miss")):
        second = prepare(song, config, tmp_path, threading.Event())
    assert first.to_dict() == second.to_dict()
    assert song.to_text() == before
    config["expression_profile"] = "rhythmic"
    third = prepare(song, config, tmp_path, threading.Event())
    assert third.metadata["preparation_cache"] != first.metadata["preparation_cache"]


def test_preparation_cancel_and_model_fallback_are_explicit(tmp_path):
    cancelled = threading.Event()
    cancelled.set()
    with pytest.raises(InterruptedError):
        prepare(passage(), normalize_settings({}), tmp_path, cancelled)
    result = prepare(
        passage(), normalize_settings({"expression_engine": "model"}), tmp_path, threading.Event()
    )
    assert result.metadata["expression_origin"] == "Regras musicais"
    assert result.metadata["preparation_warning"]
    assert not list((tmp_path / "analysis-cache").glob("*.json"))


def test_model_adapter_preserves_note_identity_and_overall_tempo():
    song = passage()
    data = {
        "notes": [
            {"pitch": n.pitch, "start": 1 + n.start * 2, "gate": 0.6, "velocity": 75}
            for n in song.notes
        ],
        "pedal": [{"time": 1.1, "value": 100}, {"time": 1.3, "value": 65}, {"time": 2, "value": 0}],
    }
    result = apply_render(song, song.notes, data, 1)
    assert [n.start for n in result.notes] == [0, 0.5, 1]
    assert [n.key for n in result.notes] == [n.key for n in song.notes]
    assert all(n.gate_duration == 0.3 for n in result.notes)
    assert len(result.metadata["model_pedal"]) == 2
    data["notes"][1]["pitch"] = 42
    with pytest.raises(ValueError, match="sequência"):
        apply_render(song, song.notes, data, 1)


def signed_pack(data):
    key = Ed25519PrivateKey.generate()
    manifest = {
        "schema": 1,
        "pack": PACK_VERSION,
        "asset": {
            "url": f"https://github.com/{updates.REPOSITORY}/releases/download/v4.2.0-beta.1/pack.zip",
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        },
    }
    manifest["signature"] = base64.b64encode(
        key.sign(updates.canonical_manifest(manifest))
    ).decode()
    public = base64.b64encode(
        key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    ).decode()
    return manifest, public


def test_pack_rejects_tampering():
    manifest, public = signed_pack(b"test")
    assert verify_pack(manifest, public) == manifest
    manifest["asset"]["url"] = "https://example.org/test"
    with pytest.raises(ValueError):
        verify_pack(manifest, public)


def test_pack_extraction_rejects_escape_even_when_signed(tmp_path):
    data = BytesIO()
    with zipfile.ZipFile(data, "w") as zipped:
        zipped.writestr("../outside.txt", "bad")
    manifest, public = signed_pack(data.getvalue())
    verify_pack(manifest, public)
    with (
        patch("tessera_piano.model_pack.read_json", return_value=manifest),
        patch("tessera_piano.model_pack.verify_pack", return_value=manifest),
        patch("urllib.request.urlopen", return_value=BytesIO(data.getvalue())),
    ):
        with pytest.raises(ValueError, match="Caminho"):
            ModelPack(tmp_path).install(lambda p: None, threading.Event())
    assert not (tmp_path / "outside.txt").exists()
    assert not ModelPack(tmp_path).ready()


def test_manual_conflicts_require_explicit_simplification():
    song = Song("x", [Note("q", 0, 0.5), Note("Q", 0, 0.5), Note("t", 1, 0.5)])
    before = song.to_text()
    assert manual_issues(song) > 0
    melody = manual_song(song, "melody")
    assert len(melody.notes) == 2 and manual_issues(melody) == 0
    assert song.to_text() == before
    distributed = manual_song(song, "distributed")
    assert len(distributed.notes) == len(song.notes)
    assert manual_issues(distributed) == 0
    assert manual_song(distributed, "distributed") is distributed


def test_distributed_arrangement_respects_rollover_without_dropping_notes():
    song = Song("Acorde amplo", [Note(k, 0, 1) for k in "1234567890qwerty"])
    distributed = manual_song(song, "distributed", rollover=6)
    assert len(distributed.notes) == len(song.notes)
    assert manual_issues(distributed, rollover=6) == 0


def test_chroma_maps_all_88_bindings_and_modifiers():
    from tessera_piano.keymap import key_binding

    for key in MIDI_TO_KEY_88.values():
        assert key_binding(key)[0] in KEY_POSITIONS
    result = lights([Note("Q", 0, 1)], [Note("q", 1, 1)], False, 0)
    assert result["q"] == (245, 189, 103)
    assert "shift" in result and "space" in result
    assert "ctrl" in lights([Note("ctrl+t", 0, 1)], [], None, 0)
    client = Chroma()
    grid = client.parameters({"q": (255, 0, 0)}, "CHROMA_CUSTOM_KEY")
    assert grid["key"][2][2] & 0x01000000


class ClockCancel:
    def __init__(self):
        self.now = 0
        self.cancel_at = 10

    def is_set(self):
        return self.now >= self.cancel_at

    def wait(self, duration):
        self.now += duration
        return self.is_set()


def test_soft_stop_finishes_short_tail_and_focus_loss_overrides_it(monkeypatch):
    clock = ClockCancel()
    monkeypatch.setattr(playback.time, "perf_counter", lambda: clock.now)

    class Soft:
        def is_set(self):
            return clock.now >= 0.025

    class Keyboard:
        calls = []
        held = set()

        def foreground(self):
            return 123

        def press_note(self, key):
            self.calls.append((clock.now, "on", key))
            self.held.add(key)

        def release_note(self, key):
            self.calls.append((clock.now, "off", key))
            self.held.discard(key)

        def release_all(self):
            self.held.clear()

        def set_sustain(self, enabled):
            self.calls.append((clock.now, "pedal", enabled))

    kb = Keyboard()
    song = Song("x", [Note("t", 0, 2), Note("u", 0.2, 0.2), Note("o", 3, 0.3)])
    with pytest.raises(playback.PlaybackStopped, match="suave"):
        playback.play_song(song, 1, kb, clock, 123, lambda *a: None, "auto", Soft())
    assert not kb.held and 0.2 < clock.now < 1.5
    assert [e[2] for e in kb.calls if e[1] == "on"] == ["t", "u"]
    assert not any(e[2] == "o" for e in kb.calls)
    clock.now = 0
    kb.foreground = lambda: 124 if clock.now > 0.04 else 123
    with pytest.raises(playback.PlaybackStopped, match="janela"):
        playback.play_song(song, 1, kb, clock, 123, lambda *a: None, "auto", Soft())
    assert not kb.held and clock.now < 0.1


@pytest.mark.parametrize("mode", ["follow", "practice"])
def test_guided_modes_observe_inputs_without_synthetic_output(monkeypatch, mode):
    clock = ClockCancel()
    monkeypatch.setattr(playback.time, "perf_counter", lambda: clock.now)

    class ReadOnlyKeyboard:
        def foreground(self):
            return 123

        def down(self, vk):
            return (vk == ord("T") and 0.02 <= clock.now <= 0.07) or (
                vk == ord("U") and 0.18 <= clock.now <= 0.28
            )

    class Lamps:
        def __init__(self):
            self.frames = []

        def frame(self, colors):
            self.frames.append(colors)

    song = Song("x", [Note("t", 0, 0.08), Note("u", 0.2, 0.08)])
    config = normalize_settings({"guide_mode": mode})
    lamps = Lamps()
    result = guide_song(song, 1, ReadOnlyKeyboard(), clock, 123, lamps, config, lambda *a: None)
    assert result["hits"] == 2 and result["misses"] == 0
    assert lamps.frames and clock.now < 1


def test_loop_clips_notes_pedal_and_time():
    song = passage()
    song.pedal = [PedalChange(0, True), PedalChange(1.2, False)]
    part = excerpt(song, 0.2, 0.7)
    assert part.duration == pytest.approx(0.5)
    assert all(n.start + n.duration <= 0.5 for n in part.notes)
    assert part.pedal[-1].time == pytest.approx(0.5)
    assert part.pedal[-1].down is False


def test_practice_keeps_the_requested_key_lit_while_waiting(monkeypatch):
    clock = ClockCancel()
    clock.cancel_at = 0.15
    monkeypatch.setattr(playback.time, "perf_counter", lambda: clock.now)

    class Keyboard:
        def foreground(self):
            return 123

        def down(self, vk):
            return False

    class Lamps:
        def frame(self, colors):
            frames.append(colors)

    frames = []
    song = Song(
        "Prática",
        [Note("Q", 0, 0.08), Note("t", 0.2, 0.08)],
        pedal=[PedalChange(0, False), PedalChange(0.1, True)],
    )
    config = normalize_settings({"guide_mode": "practice", "guide_latency": 300})
    with pytest.raises(playback.PlaybackStopped):
        guide_song(song, 1, Keyboard(), clock, 123, Lamps(), config, lambda *a: None)
    assert len(frames) > 1
    expected = {"q": (245, 189, 103), "shift": (245, 189, 103), "space": (160, 100, 185)}
    assert all(frame == expected for frame in frames)


def test_beta_manifest_requires_explicit_channel():
    key = Ed25519PrivateKey.generate()
    manifest = {
        "schema": 1,
        "version": "4.2.0-beta.1",
        "windows-x64": {
            "url": f"https://github.com/{updates.REPOSITORY}/releases/download/v4.2.0-beta.1/setup.exe",
            "size": 4,
            "sha256": hashlib.sha256(b"test").hexdigest(),
        },
    }
    manifest["signature"] = base64.b64encode(
        key.sign(updates.canonical_manifest(manifest))
    ).decode()
    public = base64.b64encode(
        key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    ).decode()
    with pytest.raises(ValueError):
        updates.verify_manifest(manifest, public)
    assert updates.verify_manifest(manifest, public, allow_prerelease=True) == manifest


def test_preferences_reject_invalid_light_positions_and_preserve_calibration():
    settings = normalize_settings(
        {
            "guide_positions": {"q": [2, 2], "t": [-1, 8], "invalid": [1, 1]},
            "guide_calibrated": True,
            "session_mode": "guided",
        }
    )
    assert settings["guide_positions"] == {"q": [2, 2]}
    assert settings["guide_calibrated"] and settings["session_mode"] == "guided"


def test_chroma_negotiates_supported_effect_and_returns_session():
    class SDK(Chroma):
        def __init__(self):
            super().__init__()
            self.calls = []
            self.colored = threading.Event()
            self.color_writes = 0

        def request(self, method, url, body=None):
            self.calls.append((method, url, body))
            if method == "POST":
                return {"uri": "http://localhost:54321/chromasdk"}
            if body and body.get("effect") == "CHROMA_CUSTOM_KEY":
                raise OSError("unsupported")
            if body and body.get("param", {}).get("key", [[0]])[2][2] & 255:
                self.color_writes += 1
                if self.color_writes >= 2:
                    self.colored.set()
            return {}

    sdk = SDK()
    with sdk:
        assert sdk.effect == "CHROMA_CUSTOM2"
        sdk.frame({"q": (255, 0, 0)})
        assert sdk.colored.wait(3)
    assert sdk.calls[-1][0] == "DELETE"
    assert not sdk.thread.is_alive()


def test_chroma_rejects_nonlocal_session_before_sending_effects():
    calls = []

    def request(method, url, body=None):
        calls.append(method)
        return {"uri": "http://example.org/chromasdk"}

    client = Chroma()
    client.request = request
    with pytest.raises(OSError):
        client.start()
    assert calls == ["POST"]


def test_pack_rejects_transport_corruption_without_replacing_installation(tmp_path):
    manifest, public = signed_pack(b"test")
    verify_pack(manifest, public)
    with (
        patch("tessera_piano.model_pack.read_json", return_value=manifest),
        patch("tessera_piano.model_pack.verify_pack", return_value=manifest),
        patch("urllib.request.urlopen", return_value=BytesIO(b"evil")),
    ):
        with pytest.raises(ValueError, match="assinatura"):
            ModelPack(tmp_path).install(lambda p: None, threading.Event())
    assert not ModelPack(tmp_path).ready()
