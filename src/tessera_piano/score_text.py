"""Leitura do formato de partituras de teclado em texto."""

from __future__ import annotations
from dataclasses import dataclass
import math
import re
from .keymap import BLACK_BASE, VALID_KEYS_61 as VALID_KEYS

DEMO = """# Ode à Alegria — trecho de exemplo, uma nota por tempo.
# Espaços e quebras de linha organizam a partitura.
t t y u u y t r e e r t t:1.5 r:0.5 r:2
t t y u u y t r e e r t r:1.5 e:0.5 e:2
r r t e r t:0.5 y:0.5 t e r t:0.5 y:0.5 t r e r -
t t y u u y t r e e r t r:1.5 e:0.5 e:2
"""


@dataclass(frozen=True)
class Step:
    keys: str
    beats: float = 1.0


def parse_score(text: str) -> list[Step]:
    """Cada tecla ou [acorde] é um tempo; - é pausa; :N muda duração."""
    text = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
    steps: list[Step] = []
    i = 0
    while i < len(text):
        char = text[i]
        if char.isspace() or char == "|":
            i += 1
            continue
        if char == "[":
            end = text.find("]", i + 1)
            if end == -1:
                raise ValueError("Acorde aberto: falta ] na partitura.")
            keys = "".join(text[i + 1 : end].split())
            if not keys:
                raise ValueError("Há um acorde vazio [].")
            i = end + 1
        elif char == "-":
            keys = ""
            i += 1
        elif char in VALID_KEYS:
            keys = char
            i += 1
        else:
            raise ValueError(f"Símbolo inválido na partitura: {char!r}. Veja a ajuda.")
        invalid = set(keys) - VALID_KEYS
        if invalid:
            raise ValueError(f"Teclas ausentes na foto: {', '.join(sorted(invalid))}")
        bases = [BLACK_BASE.get(key, key) for key in keys]
        if len(set(bases)) != len(bases):
            raise ValueError(
                f"Acorde [{keys}] repete uma tecla física. Separe as notas "
                "(por exemplo, q Q em vez de [qQ])."
            )
        beats = 1.0
        if i < len(text) and text[i] == ":":
            match = re.match(r":([0-9]+(?:\.[0-9]+)?|\.[0-9]+)", text[i:])
            if not match:
                raise ValueError("Após : informe a duração, como t:2 ou t:0.5.")
            beats = float(match.group(1))
            if not math.isfinite(beats) or not 0.05 <= beats <= 128:
                raise ValueError("A duração deve estar entre 0.05 e 128 tempos.")
            i += len(match.group(0))
        steps.append(Step(keys, beats))
    if not steps:
        raise ValueError("A partitura está vazia.")
    return steps
