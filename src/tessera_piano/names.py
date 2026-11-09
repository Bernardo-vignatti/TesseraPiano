"""Nomes legíveis; títulos MIDI de faixa podem conter instrumento ou bytes legados."""

import re
import unicodedata


def clean_title(value):
    value = str(value)
    # Corrige apenas sequências que decodificam integralmente, sem perder letras.
    if any(mark in value for mark in ("Ã", "Â", "â€", "ðŸ")):
        for encoding in ("latin-1", "cp1252"):
            try:
                repaired = value.encode(encoding).decode("utf-8")
                if repaired != value:
                    value = repaired
                    break
            except (UnicodeError, LookupError):
                pass
    value = unicodedata.normalize("NFC", value)
    value = re.sub(r"\s+", " ", value)
    value = "".join(c for c in value if not unicodedata.category(c).startswith("C"))
    return re.sub(r"\s+", " ", value).strip()[:180]


def filename_title(filename):
    name = str(filename).replace("\\", "/").rsplit("/", 1)[-1]
    pattern = r"(?i)(?:\.(?:midi?|json|piano))+$"
    name = re.sub(pattern, "", name)
    return clean_title(name.replace("_", " ")) or "Música sem título"
