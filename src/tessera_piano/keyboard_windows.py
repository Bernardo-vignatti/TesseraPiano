"""Entradas de teclado Windows com liberação das teclas pertencentes ao app."""

import ctypes
import os
import sys
import time
from .keymap import WHITE_KEYS, BLACK_BASE, key_binding

# Tipos de largura fixa: a ABI do Windows usa DWORD/LONG de 32 bits,
# inclusive no Windows de 64 bits. INPUT inclui a união completa.
U16, U32, I32, UPTR = ctypes.c_uint16, ctypes.c_uint32, ctypes.c_int32, ctypes.c_size_t


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", U16),
        ("wScan", U16),
        ("dwFlags", U32),
        ("time", U32),
        ("dwExtraInfo", UPTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", I32),
        ("dy", I32),
        ("mouseData", U32),
        ("dwFlags", U32),
        ("time", U32),
        ("dwExtraInfo", UPTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", U32), ("wParamL", U16), ("wParamH", U16)]


class INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("data",)
    _fields_ = [("type", U32), ("data", INPUTUNION)]


class WindowsKeyboard:
    """Somente SendInput, estado de teclas e identificação da janela ativa."""

    def __init__(self, mode="scan"):
        if sys.platform != "win32":
            raise OSError("Este programa envia teclas usando o Windows.")
        self.api = ctypes.WinDLL("user32", use_last_error=True)
        self.api.SendInput.argtypes = [U32, ctypes.POINTER(INPUT), ctypes.c_int]
        self.api.SendInput.restype = U32
        self.api.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.api.GetAsyncKeyState.restype = ctypes.c_int16
        self.api.GetForegroundWindow.argtypes = []
        self.api.GetForegroundWindow.restype = ctypes.c_void_p
        self.api.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(U32)]
        self.api.GetWindowThreadProcessId.restype = U32
        self.api.MapVirtualKeyW.argtypes = [U32, U32]
        self.api.MapVirtualKeyW.restype = U32
        self.mode = mode
        # Guardar o código realmente enviado garante que a liberação use
        # o mesmo código, mesmo após mudança de layout de teclado.
        self.held_codes: dict[int, tuple[int, int, int]] = {}
        self.owned: set[int] = set()
        self.note_labels: dict[int, str] = {}
        self.pedal_managed = False
        self.sustain_enabled = True

    def down(self, vk: int) -> bool:
        return bool(self.api.GetAsyncKeyState(vk) & 0x8000)

    def foreground(self) -> int:
        return self.api.GetForegroundWindow() or 0

    def is_own_window(self, hwnd: int) -> bool:
        pid = U32()
        self.api.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value == os.getpid()

    def is_target_window(self, hwnd):
        pid = U32()
        self.api.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [U32, ctypes.c_int, U32]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.QueryFullProcessImageNameW.argtypes = [
            ctypes.c_void_p,
            U32,
            ctypes.c_wchar_p,
            ctypes.POINTER(U32),
        ]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.OpenProcess(0x1000, False, pid.value)
        if not handle:
            return False
        try:
            buffer = ctypes.create_unicode_buffer(32768)
            length = U32(len(buffer))
            return bool(
                kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(length))
                and os.path.basename(buffer.value).lower()
                in ("robloxplayerbeta.exe", "windows10universal.exe")
            )
        finally:
            kernel.CloseHandle(handle)

    def send(self, vk: int, release: bool = False):
        if release and vk in self.held_codes:
            event_vk, scan, flags = self.held_codes[vk]
        else:
            mapped = self.api.MapVirtualKeyW(vk, 4)  # MAPVK_VK_TO_VSC_EX
            if not mapped:
                raise OSError(f"Não foi possível mapear a tecla {vk} no Windows.")
            scan = mapped & 0xFF
            flags = 1 if (mapped >> 8) == 0xE0 else 0
            if self.mode == "scan":
                event_vk = 0
                flags |= 8  # KEYEVENTF_SCANCODE
            else:
                event_vk = vk
        # Registrar antes do envio permite limpeza mesmo após erro parcial.
        if not release:
            self.owned.add(vk)
            self.held_codes[vk] = (event_vk, scan, flags)
        event = INPUT(
            type=1, ki=KEYBDINPUT(wVk=event_vk, wScan=scan, dwFlags=flags | (2 if release else 0))
        )
        if self.api.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT)) != 1:
            raise OSError(
                "O Windows recusou uma entrada de teclado. Confira as permissões das janelas."
            )
        if release:
            self.owned.discard(vk)
            self.held_codes.pop(vk, None)

    def press_chord(self, keys: str):
        # Notas brancas primeiro. Shift é usado somente ao pressionar pretas.
        for key in keys:
            if key in WHITE_KEYS:
                self.send(ord(key.upper()))
        black = [key for key in keys if key in BLACK_BASE]
        if black:
            self.send(0xA0)  # VK_LSHIFT
            for key in black:
                self.send(ord(BLACK_BASE[key].upper()))
            self.send(0xA0, True)

    def press_note(self, key):
        base, modifiers = key_binding(key)
        vk = ord(base.upper())
        self.note_labels[vk] = key
        try:
            for modifier in modifiers:
                self.send(modifier)
            self.send(vk)
        finally:
            for modifier in reversed(modifiers):
                self.send(modifier, True)

    def release_note(self, key):
        base, modifiers = key_binding(key)
        vk = ord(base.upper())
        try:
            for modifier in modifiers:
                self.send(modifier)
            self.send(vk, True)
        finally:
            for modifier in reversed(modifiers):
                self.send(modifier, True)
        self.note_labels.pop(vk, None)

    def set_sustain(self, enabled):
        # No jogo: Espaço segurado = pedal DESLIGADO.
        self.pedal_managed = True
        if enabled:
            if 0x20 in self.owned:
                self.send(0x20, True)
        elif 0x20 not in self.owned:
            self.send(0x20)
        self.sustain_enabled = bool(enabled)

    def release_all(self):
        errors = []
        target = getattr(self, "cleanup_target", None)
        focused = target is None or self.foreground() == target
        for key in list(getattr(self, "note_labels", {}).values()):
            try:
                if focused:
                    self.release_note(key)
                else:
                    vk = ord(key_binding(key)[0].upper())
                    self.send(vk, True)
                    self.note_labels.pop(vk, None)
            except OSError as error:
                errors.append(str(error))
        if getattr(self, "pedal_managed", False):
            try:
                # Corta os sons ainda sustentados e devolve Espaço ao estado solto.
                if focused:
                    self.set_sustain(False)
                    time.sleep(0.025)
                    self.set_sustain(True)
                elif 0x20 in self.owned:
                    self.send(0x20, True)
                self.sustain_enabled = True
            except OSError as error:
                errors.append(str(error))
            self.pedal_managed = False
        # Tentar todas as liberações mesmo se uma delas falhar.
        for vk in sorted(self.owned):
            try:
                self.send(vk, True)
            except OSError as error:
                errors.append(str(error))
        if errors:
            raise OSError("Não foi possível liberar todas as teclas enviadas. " + errors[0])
        self.cleanup_target = None


class PreviewKeyboard:
    """Saída inerte usada pela prévia e pela verificação automatizada da interface."""

    def __init__(self):
        self.note_labels = {}
        self.mode = "scan"
        self.sustain_enabled = True
        self.pedal_managed = False

    def down(self, key):
        return False

    def foreground(self):
        return 123

    def is_own_window(self, target):
        return False

    def is_target_window(self, target):
        return True

    def press_note(self, key):
        self.note_labels[key] = key

    def release_note(self, key):
        self.note_labels.pop(key, None)

    def set_sustain(self, enabled):
        self.pedal_managed = True
        self.sustain_enabled = enabled

    def release_all(self):
        self.note_labels.clear()
        self.pedal_managed = False
        self.sustain_enabled = True
