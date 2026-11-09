import ctypes
from pathlib import Path
import unittest


from tessera_piano import keyboard_windows as p
from tessera_piano.score_text import parse_score, Step, DEMO
from tessera_piano.keymap import VALID_KEYS_61


class FakeKeyboard:
    def __init__(self, fail=False):
        self.pressed = set()
        self.target = 123
        self.calls = []
        self.fail = fail

    def foreground(self):
        return self.target

    def press_chord(self, keys):
        self.pressed.update(keys)
        self.calls.append(keys)
        if self.fail:
            raise OSError("simulated failure")

    def release_all(self):
        self.pressed.clear()


class PianoTests(unittest.TestCase):
    def test_exact_map(self):
        expected = {
            "!": "1",
            "@": "2",
            "$": "4",
            "%": "5",
            "^": "6",
            "*": "8",
            "(": "9",
            "Q": "q",
            "W": "w",
            "E": "e",
            "T": "t",
            "Y": "y",
            "I": "i",
            "O": "o",
            "P": "p",
            "S": "s",
            "D": "d",
            "G": "g",
            "H": "h",
            "J": "j",
            "L": "l",
            "Z": "z",
            "C": "c",
            "V": "v",
            "B": "b",
        }
        self.assertEqual(p.BLACK_BASE, expected)
        self.assertEqual(len(VALID_KEYS_61), 61)

    def test_score_semantics(self):
        self.assertEqual(
            parse_score("t y|[adg]:2 -:0.5 Q # comment\n!"),
            [Step("t"), Step("y"), Step("adg", 2), Step("", 0.5), Step("Q"), Step("!")],
        )
        self.assertEqual(parse_score("tyu"), parse_score("t y u"))
        self.assertEqual(parse_score("a:1e3"), [Step("a"), Step("e"), Step("3")])

    def test_bad_scores_rejected(self):
        for value in (
            "",
            "# a",
            "[",
            "[]",
            "[qQ]",
            "[1!]",
            "[aa]",
            "a:0",
            "a:999",
            "a:NaN",
            "a:inf",
            "a:-2",
            "a:",
            '"',
            "[a?]",
            "a]",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_score(value)

    def test_examples_parse(self):
        self.assertEqual(len(parse_score(DEMO)), 62)
        self.assertTrue(parse_score(Path("tests/fixtures/chords.txt").read_text()))

    def test_input_structure_abi(self):
        self.assertEqual(ctypes.sizeof(p.INPUT), 40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)

    def test_shift_chord_sequence(self):
        kb = object.__new__(p.WindowsKeyboard)
        calls = []
        kb.send = lambda vk, release=False: calls.append((vk, release))
        kb.press_chord("aQ!")
        self.assertEqual(
            calls,
            [(ord("A"), False), (0xA0, False), (ord("Q"), False), (ord("1"), False), (0xA0, True)],
        )

    def test_send_and_ownership(self):
        class FakeAPI:
            def MapVirtualKeyW(self, vk, kind):
                self.mapping = (vk, kind)
                return 0x1E

            def SendInput(self, count, ptr, size):
                item = ctypes.cast(ptr, ctypes.POINTER(p.INPUT)).contents
                self.item = (item.type, item.ki.wVk, item.ki.wScan, item.ki.dwFlags, size)
                return 1

        for mode, vk, flags in [("scan", 0, 8), ("virtual", 65, 0)]:
            with self.subTest(mode=mode):
                kb = object.__new__(p.WindowsKeyboard)
                kb.owned, kb.held_codes, kb.mode = set(), {}, mode
                kb.api = FakeAPI()
                kb.send(65)
                self.assertEqual(kb.api.mapping, (65, 4))
                self.assertIn(65, kb.owned)
                self.assertEqual(kb.api.item, (1, vk, 0x1E, flags, ctypes.sizeof(p.INPUT)))
                # Mudança de layout/modo durante a nota não altera sua liberação.
                kb.mode = "virtual" if mode == "scan" else "scan"
                kb.api.MapVirtualKeyW = lambda *args: 0x2A
                kb.send(65, True)
                self.assertFalse(kb.owned)
                self.assertFalse(kb.held_codes)
                self.assertEqual(kb.api.item, (1, vk, 0x1E, flags | 2, ctypes.sizeof(p.INPUT)))

    def test_unmapped_key_rejected_without_ownership(self):
        kb = object.__new__(p.WindowsKeyboard)
        kb.owned, kb.held_codes, kb.mode = set(), {}, "scan"

        class FakeAPI:
            def MapVirtualKeyW(self, vk, kind):
                return 0

        kb.api = FakeAPI()
        with self.assertRaises(OSError):
            kb.send(65)
        self.assertFalse(kb.owned)
        self.assertFalse(kb.held_codes)

    def test_scan_shift_and_failed_input_cleanup(self):
        kb = object.__new__(p.WindowsKeyboard)
        kb.owned, kb.held_codes, kb.mode = set(), {}, "scan"

        class FakeAPI:
            failing = True
            events = []

            def MapVirtualKeyW(self, vk, kind):
                return 0x2A  # Left Shift

            def SendInput(self, count, ptr, size):
                item = ctypes.cast(ptr, ctypes.POINTER(p.INPUT)).contents
                self.events.append((item.ki.wVk, item.ki.wScan, item.ki.dwFlags))
                return 0 if self.failing else 1

        kb.api = FakeAPI()
        with self.assertRaises(OSError):
            kb.send(0xA0)
        self.assertEqual(kb.owned, {0xA0})
        kb.api.failing = False
        kb.release_all()
        self.assertFalse(kb.owned)
        self.assertEqual(kb.api.events, [(0, 0x2A, 8), (0, 0x2A, 10)])

    def test_release_attempts_all_after_failure(self):
        kb = object.__new__(p.WindowsKeyboard)
        kb.owned = {49, 65, 160}
        calls = []

        def send(vk, release):
            calls.append(vk)
            if vk == 49:
                raise OSError("failure")
            kb.owned.discard(vk)

        kb.send = send
        with self.assertRaises(OSError):
            kb.release_all()
        self.assertEqual(calls, [49, 65, 160])
        self.assertEqual(kb.owned, {49})


if __name__ == "__main__":
    unittest.main()
