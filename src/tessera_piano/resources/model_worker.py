"""Executado pelo Python isolado do pacote Pianist Transformer, nunca pela UI."""

import json
import ctypes
import os
from pathlib import Path
import sys
import time

os.environ.update(
    HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", DO_NOT_TRACK="1"
)
root, source, output = map(Path, sys.argv[1:4])
sys.path.insert(0, str(root / "engine"))

import torch  # noqa: E402 — ambiente offline e caminho isolado definidos antes
from miditoolkit import MidiFile, Note, Instrument, TempoChange  # noqa: E402
from src.model.pianoformer import PianoT5Gemma  # noqa: E402
from src.model.generate import batch_performance_render  # noqa: E402


def main():
    request = json.loads(source.read_text(encoding="utf-8"))
    torch.set_num_threads(min(4, os.cpu_count() or 1))
    torch.manual_seed(request["seed"])
    started = time.perf_counter()
    model = PianoT5Gemma.from_pretrained(
        str(root / "engine/weights"), local_files_only=True, torch_dtype=torch.float32
    ).eval()
    midi = MidiFile(ticks_per_beat=1000)
    midi.tempo_changes = [TempoChange(120, 0)]
    # A representação do modelo usa milissegundos. As identidades de origem ficam separadas.
    instrument = Instrument(program=0)
    notes = request["notes"]
    unique = {}
    identities = []
    for note in notes:
        key = (round(note["start"] * 1000), note["pitch"])
        identities.append(key)
        if key not in unique or note["gate"] > unique[key]["gate"]:
            unique[key] = note
    order = sorted(unique)
    instrument.notes = [
        Note(
            velocity=unique[key]["velocity"],
            pitch=key[1],
            start=key[0] * 2,
            end=key[0] * 2 + max(2, round(unique[key]["gate"] * 2000)),
        )
        for key in order
    ]
    midi.instruments = [instrument]
    midi.max_tick = max(n.end for n in instrument.notes) + 1

    def progress(value):
        print(json.dumps({"progress": round(value, 3)}), flush=True)

    with torch.inference_mode():
        result, _ = batch_performance_render(
            model, [midi], device="cpu", progress_callback=progress
        )
    generated = result[0].instruments[0].notes
    if len(generated) != len(order) or any(n.pitch != key[1] for n, key in zip(generated, order)):
        raise ValueError("O modelo não preservou as notas de entrada.")
    times = result[0].get_tick_to_time_mapping()
    pedal = result[0].instruments[0].control_changes

    class Memory(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong)] + [
            (name, ctypes.c_size_t)
            for name in (
                "peak",
                "working",
                "quota_peak",
                "quota",
                "pool_peak",
                "pool",
                "pagefile",
                "pagefile_peak",
            )
        ]

    counters = Memory()
    counters.cb = ctypes.sizeof(counters)
    current = ctypes.WinDLL("kernel32").GetCurrentProcess
    current.restype = ctypes.c_void_p
    memory_info = ctypes.WinDLL("psapi").GetProcessMemoryInfo
    memory_info.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
    memory_info(current(), ctypes.byref(counters), counters.cb)
    generated_rows = {
        key: {
            "pitch": n.pitch,
            "start": float(times[n.start]),
            "gate": max(0.005, float(times[n.end] - times[n.start])),
            "velocity": n.velocity,
        }
        for key, n in zip(order, generated)
    }
    payload = {
        "notes": [generated_rows[key] for key in identities],
        "pedal": [
            {"time": float(times[p.time]), "value": p.value} for p in pedal if p.number == 64
        ],
        "seconds": round(time.perf_counter() - started, 3),
        "peak_mb": round(counters.peak / 1024**2),
    }
    output.write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    main()
