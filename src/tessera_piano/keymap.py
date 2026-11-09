"""Mapas de 61 e 88 notas das imagens do piano (sublinhado = Ctrl)."""

WHITE_KEYS = "1234567890qwertyuiopasdfghjklzxcvbnm"
BLACK_BASE = dict(zip("!@$%^*(QWETYIOPSDGHJLZCVB", "1245689qwetyiopsdghjlzcvb"))
VALID_KEYS_61 = set(WHITE_KEYS) | set(BLACK_BASE)
MIDI_TO_KEY = {}
i = 0
for pitch in range(36, 97):
    if pitch % 12 in (0, 2, 4, 5, 7, 9, 11):
        base = WHITE_KEYS[i]
        i += 1
        MIDI_TO_KEY[pitch] = base
    else:
        MIDI_TO_KEY[pitch] = next(k for k, value in BLACK_BASE.items() if value == base)
MIDI_TO_KEY_88 = {
    **dict(zip(range(21, 36), ("ctrl+" + k for k in "1234567890qwert"))),
    **MIDI_TO_KEY,
    **dict(zip(range(97, 109), ("ctrl+" + k for k in "yuiopasdfghj"))),
}
KEY_TO_MIDI = {key: pitch for pitch, key in MIDI_TO_KEY_88.items()}
VALID_KEYS = set(KEY_TO_MIDI)


def layout_keys(layout="61"):
    if str(layout) not in ("61", "88"):
        raise ValueError("Escolha o piano de 61 ou 88 teclas.")
    return MIDI_TO_KEY_88 if str(layout) == "88" else MIDI_TO_KEY


def key_binding(key):
    if key not in VALID_KEYS:
        raise ValueError("Tecla desconhecida: " + str(key))
    if key.startswith("ctrl+"):
        return key[5:], (0xA2,)  # VK_LCONTROL
    return BLACK_BASE.get(key, key), ((0xA0,) if key in BLACK_BASE else ())


def physical_key(key):
    return key_binding(key)[0]


def fit_pitch(pitch, layout="61"):
    """Mantém a classe de altura; ajusta oitavas apenas fora do mapa escolhido."""
    keys = layout_keys(layout)
    low, high = min(keys), max(keys)
    while pitch < low:
        pitch += 12
    while pitch > high:
        pitch -= 12
    return pitch
