"""Aplicativo Qt e coordenação entre biblioteca, execução e atualizações."""

from __future__ import annotations

import logging
from pathlib import Path
import threading
import time

from PySide6.QtCore import QObject, Property, QTimer, QUrl, Signal, Slot, Qt
from PySide6.QtGui import QDesktopServices, QFont, QIcon, QGuiApplication
from PySide6.QtWidgets import QApplication, QFileDialog, QMenu, QSystemTrayIcon

from . import __version__
from .keymap import KEY_TO_MIDI, MIDI_TO_KEY_88
from .keyboard_windows import PreviewKeyboard, WindowsKeyboard
from .music import Song, Note, PedalChange
from .preparation import prepare
from .model_pack import ModelPack
from .chroma import Chroma, KEY_POSITIONS
from .guided import guide_song, manual_song, manual_issues
from .playback import PlaybackStopped, play_song
from .storage import excerpt, normalize_settings
from . import updates

BASE = Path(__file__).parent


class Controller(QObject):
    libraryChanged = Signal()
    songChanged = Signal()
    settingsChanged = Signal()
    playbackChanged = Signal()
    updateChanged = Signal()
    featuresChanged = Signal()
    toast = Signal(str)
    completed = Signal(str, object)
    activate = Signal()

    def __init__(self, profile, preview=False):
        super().__init__()
        self.profile = profile
        self.preview = preview
        self.keyboard = PreviewKeyboard() if preview else WindowsKeyboard()
        self.window = None
        self.current = None
        self.prepared = None
        self.query = ""
        self.favorites_only = False
        self.importing = False
        self.preparing = False
        self.generation = 0
        self.closing = False
        self.cancel = threading.Event()
        self.download_cancel = threading.Event()
        self.prepare_cancel = threading.Event()
        self.model_cancel = threading.Event()
        self.soft_stop = threading.Event()
        self.model_pack = ModelPack(profile.directory)
        self.features_state = {
            "modelReady": self.model_pack.ready(),
            "modelState": "idle",
            "modelProgress": 0,
            "analysisProgress": 0,
            "chromaState": "idle",
            "summary": "",
            "guideHits": 0,
            "guideTotal": 0,
            "timing": 0,
            "manualIssues": 0,
        }
        self.guide_active = []
        self.worker = None
        self.tasks = set()
        self.offset = 0.0
        self.position = 0.0
        self.started = None
        self.active_speed = self.profile.config["speed"]
        self.origin = 0
        self.status = "idle"
        self.message = "Pronto para tocar"
        self.countdown = 0
        self.hotkeys = {}
        self.updater = {
            "state": "idle",
            "message": "Verifique se há uma nova versão.",
            "progress": 0,
            "version": "",
        }
        self.update_manifest = None
        self.update_installer = None
        self.completed.connect(self._completed)
        self.activate.connect(self.show_window)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(33)
        self.tray = None
        QGuiApplication.styleHints().colorSchemeChanged.connect(self.settingsChanged)
        self.create_tray()
        self.settingsChanged.connect(self.refresh_tray)
        self.playbackChanged.connect(self.refresh_tray)
        self.songChanged.connect(self.refresh_tray)
        if profile.items:
            self.selectSong(
                next(
                    (i.ident for i in profile.items if i.ident == profile.config["last_song"]),
                    profile.items[0].ident,
                )
            )

    @Property(str, constant=True)
    def version(self):
        return __version__

    @Property(bool, notify=settingsChanged)
    def systemLight(self):
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Light

    @Property("QVariantMap", notify=settingsChanged)
    def settings(self):
        return self.profile.config

    @Property("QVariantList", notify=libraryChanged)
    def songs(self):
        favorites = self.profile.config["favorites"]
        return [
            {
                "id": item.ident,
                "title": item.song.title,
                "duration": item.song.duration,
                "notes": len(item.song.notes),
                "favorite": item.ident in favorites,
                "origin": "Pessoal" if item.personal else "Essenciais",
                "pedal": "MIDI" if any(p.down for p in item.song.pedal) else "Auto",
                "index": i,
            }
            for i, item in enumerate(
                sorted(
                    self.profile.items,
                    key=lambda item: (item.ident not in favorites, item.song.title.casefold()),
                )
            )
            if (not self.query or self.query in item.song.title.casefold())
            and (not self.favorites_only or item.ident in favorites)
        ]

    @Property("QVariantMap", notify=songChanged)
    def song(self):
        if not self.current:
            return {
                "id": "",
                "title": "Escolha uma música",
                "duration": 0,
                "notes": 0,
                "favorite": False,
                "pedal": "Auto",
                "tracks": [],
                "adjustments": 0,
            }
        song = self.prepared or self.current.song
        track_ids = {n.track for n in self.current.song.notes}
        return {
            "id": self.current.ident,
            "title": self.current.song.title,
            "duration": song.duration,
            "notes": len(song.notes),
            "favorite": self.current.ident in self.profile.config["favorites"],
            "pedal": song.metadata.get("pedal_origin", "Auto"),
            "tracks": [
                t for t in self.current.song.metadata.get("tracks", []) if t["id"] in track_ids
            ],
            "adjustments": sum(song.metadata.get("keyboard_adjustments", {}).values()),
            "personal": self.current.personal,
            "preparing": self.preparing,
            "profile": song.metadata.get("analysis", {}).get("profile_label", ""),
            "confidence": song.metadata.get("analysis", {}).get("confidence", 0),
            "expressionOrigin": song.metadata.get("expression_origin", "Regras musicais"),
        }

    @Property("QVariantList", notify=songChanged)
    def notes(self):
        source = self.prepared or (self.current.song if self.current else None)
        return (
            [
                {
                    "start": n.start,
                    "duration": n.gate_duration or n.duration,
                    "pitch": KEY_TO_MIDI[n.key],
                }
                for n in source.notes
            ]
            if source
            else []
        )

    @Property("QVariantMap", notify=playbackChanged)
    def playback(self):
        return {
            "status": self.status,
            "message": self.message,
            "position": self.position,
            "countdown": self.countdown,
            "busy": self.status != "idle",
            "active": self.guide_active
            if self.settings["session_mode"] == "guided"
            else [KEY_TO_MIDI[k] for k in list(self.keyboard.note_labels.values())],
            "pedal": self.keyboard.sustain_enabled,
            "pedalManaged": self.keyboard.pedal_managed,
            "preview": self.preview,
            "speed": self.active_speed if self.status != "idle" else self.settings["speed"],
            "importing": self.importing,
        }

    @Property("QVariantMap", notify=featuresChanged)
    def features(self):
        return self.features_state

    @Property("QVariantMap", notify=updateChanged)
    def update(self):
        return self.updater

    def task(self, kind, function):
        def run():
            try:
                try:
                    value = function()
                except Exception as exc:
                    logging.exception("Falha em %s", kind)
                    value = exc
                if not self.closing:
                    self.completed.emit(kind, value)
            finally:
                self.tasks.discard(threading.current_thread())

        thread = threading.Thread(target=run, daemon=True, name=f"tessera-{kind}")
        self.tasks.add(thread)
        thread.start()

    @Slot(str, object)
    def _completed(self, kind, value):
        if kind == "prepare":
            generation, prepared = value
            if generation != self.generation:
                return
            self.preparing = False
            if isinstance(prepared, Exception):
                if not isinstance(prepared, InterruptedError):
                    self.toast.emit(str(prepared))
            else:
                self.prepared = prepared
                self.offset = self.position = 0
                self.features_state["manualIssues"] = manual_issues(
                    manual_song(prepared, self.settings["guide_arrangement"]),
                    self.settings["guide_rollover"],
                )
                warning = prepared.metadata.get("preparation_warning")
                if warning:
                    self.toast.emit(warning)
            self.featuresChanged.emit()
            self.songChanged.emit()
        elif kind == "prepare-progress":
            generation, progress = value
            if generation == self.generation:
                self.features_state["analysisProgress"] = progress
                self.featuresChanged.emit()
        elif kind == "model-progress":
            self.features_state["modelProgress"] = value
            self.featuresChanged.emit()
        elif kind == "model-install":
            ready = self.model_pack.ready()
            self.features_state.update(modelReady=ready, modelState="idle")
            self.featuresChanged.emit()
            if isinstance(value, Exception):
                self.toast.emit(str(value))
            elif ready:
                self.setSetting("expression_engine", "model")
                self.toast.emit("Motor local instalado. A preparação funciona offline.")
        elif kind == "chroma-test":
            self.features_state["chromaState"] = (
                "error" if isinstance(value, Exception) else "tested"
            )
            self.featuresChanged.emit()
            self.toast.emit(
                str(value)
                if isinstance(value, Exception)
                else "Confirme se todas as teclas indicadas acenderam."
            )
        elif kind == "guide-progress":
            position, stats, active = value
            self.position = self.origin + position
            self.guide_active = active
            self.features_state.update(
                guideHits=stats["hits"], guideTotal=stats["total"], timing=stats["timing_ms"]
            )
            self.featuresChanged.emit()
            self.playbackChanged.emit()
        elif kind == "guide-result":
            self.features_state["summary"] = (
                f"{value['hits']} de {value['total']} notas · desvio {value['timing_ms']:+d} ms"
            )
            self.featuresChanged.emit()
        elif kind == "import":
            self.importing = False
            self.libraryChanged.emit()
            self.playbackChanged.emit()
            if isinstance(value, Exception):
                self.toast.emit(str(value))
            else:
                identifiers, errors = value
                if identifiers:
                    self.query = ""
                    self.favorites_only = False
                    self.selectSong(identifiers[-1])
                    self.libraryChanged.emit()
                self.toast.emit(
                    f"{len(identifiers)} música(s) importada(s)."
                    + (" " + "\n".join(errors) if errors else "")
                )
        elif kind == "check":
            if isinstance(value, Exception):
                self.updater.update(
                    state="error",
                    message="Não foi possível consultar o GitHub. Tente novamente mais tarde.",
                )
            elif value:
                self.update_manifest = value
                self.updater.update(
                    state="available",
                    message="Uma nova versão está disponível.",
                    version=value["version"],
                )
                if self.settings["auto_download"]:
                    self.downloadUpdate()
            else:
                self.updater.update(
                    state="current", message="Você está usando a versão mais recente."
                )
            self.updateChanged.emit()
        elif kind == "download":
            if isinstance(value, Exception):
                self.updater.update(state="error", message=str(value))
            else:
                self.update_installer = value
                self.updater.update(
                    state="ready", message="Download verificado. Pronto para instalar.", progress=1
                )
                self.toast.emit("Atualização pronta. Instale quando terminar de tocar.")
            self.updateChanged.emit()
        elif kind == "download-progress":
            self.updater["progress"] = value
            self.updateChanged.emit()
        elif kind == "started":
            self.started, self.origin = value
            self.status = "stopping" if self.soft_stop.is_set() else "playing"
            self.message = (
                "Acompanhe as luzes"
                if self.settings["session_mode"] == "guided"
                else "Tocando no Roblox"
            )
            self.playbackChanged.emit()
        elif kind == "session-speed":
            self.active_speed = value
            self.playbackChanged.emit()
        elif kind == "countdown":
            self.countdown = value
            self.message = f"Começa em {value} s. Selecione o piano no Roblox."
            self.playbackChanged.emit()
        elif kind == "done":
            self.started = None
            self.guide_active = []
            self.status = "idle"
            self.countdown = 0
            self.message = str(value) if value else "Execução concluída"
            if value:
                self.toast.emit(str(value))
            else:
                self.position = self.offset = 0
            self.playbackChanged.emit()

    @Slot(str)
    def setQuery(self, value):
        self.query = value.strip().casefold()
        self.libraryChanged.emit()

    @Slot(bool)
    def setFavorites(self, value):
        self.favorites_only = value
        self.libraryChanged.emit()

    @Slot(str)
    def selectSong(self, ident):
        if self.status != "idle":
            return
        self.current = next((item for item in self.profile.items if item.ident == ident), None)
        if self.current:
            if self.settings["last_song"] != ident:
                self.profile.config["track_filter"] = []
            self.profile.config["last_song"] = ident
        self.offset = self.position = 0
        self.profile.config.update(loop_start=0, loop_end=0, loop_enabled=False)
        self.prepare()

    def prepare(self):
        self.prepare_cancel.set()
        self.prepare_cancel = threading.Event()
        cancel = self.prepare_cancel
        self.generation += 1
        generation = self.generation
        self.prepared = None
        if not self.current:
            self.songChanged.emit()
            return
        source, config = self.current.song, dict(self.settings)
        self.preparing = True
        self.features_state["analysisProgress"] = 0
        self.songChanged.emit()

        def process():
            try:
                result = prepare(
                    source,
                    config,
                    self.profile.directory,
                    cancel,
                    lambda p: self.completed.emit("prepare-progress", (generation, p)),
                )
            except Exception as exc:
                result = exc
            return generation, result

        self.task("prepare", process)

    @Slot()
    def cancelPreparation(self):
        self.prepare_cancel.set()

    @Slot()
    def installModel(self):
        if (
            self.features_state["modelState"] == "installing"
            or self.preview
            or self.preparing
            or self.status != "idle"
        ):
            return
        self.model_cancel.clear()
        self.features_state.update(modelState="installing", modelProgress=0)
        self.featuresChanged.emit()
        self.task(
            "model-install",
            lambda: self.model_pack.install(
                lambda p: self.completed.emit("model-progress", p),
                self.model_cancel,
                force=self.model_pack.ready(),
            ),
        )

    @Slot()
    def cancelModel(self):
        self.model_cancel.set()

    @Slot()
    def testChroma(self):
        if self.status != "idle" or self.features_state["chromaState"] == "testing":
            return
        self.setSetting("guide_calibrated", False)
        self.features_state["chromaState"] = "testing"
        self.featuresChanged.emit()
        config = dict(self.settings)

        def test():
            with Chroma(config["guide_positions"], config["guide_brightness"]) as chroma:
                for keys, color in (
                    (list("1234567890"), (240, 170, 70)),
                    (list("qwertyuiopasdfghjklzxcvbnm"), (240, 170, 70)),
                    (["shift", "ctrl", "space"], (100, 140, 240)),
                ):
                    chroma.frame({k: color for k in keys})
                    for _ in range(60):
                        if self.closing:
                            return
                        time.sleep(0.025)

        self.task("chroma-test", test)

    @Slot(str, result="QVariantList")
    def chromaPosition(self, key):
        return self.settings["guide_positions"].get(key, KEY_POSITIONS.get(key, (0, 0)))

    @Slot(str, int, int)
    def mapChromaKey(self, key, row, column):
        if (
            self.status != "idle"
            or key not in KEY_POSITIONS
            or not 0 <= row < 6
            or not 0 <= column < 22
        ):
            return
        positions = dict(self.settings["guide_positions"])
        positions[key] = [row, column]
        self.setSetting("guide_positions", positions)
        self.setSetting("guide_calibrated", False)

    @Slot(int)
    def toggleTrack(self, track):
        if not self.current or self.status != "idle":
            return
        all_tracks = sorted({n.track for n in self.current.song.notes if n.track is not None})
        selected = list(self.settings["track_filter"] or all_tracks)
        if track in selected:
            selected.remove(track)
        else:
            selected.append(track)
        if not selected:
            self.toast.emit("Mantenha pelo menos uma faixa selecionada.")
            return
        self.setSetting("track_filter", [] if set(selected) == set(all_tracks) else selected)

    @Slot(str, "QVariant")
    def setSetting(self, key, value):
        if key not in self.profile.config or self.importing:
            return
        if self.status != "idle" and key in (
            "layout",
            "performance",
            "intensity",
            "seed",
            "pedal_mode",
            "speed",
            "mode",
            "track_filter",
            "session_mode",
            "expression_engine",
            "expression_profile",
            "guide_mode",
            "guide_arrangement",
            "guide_positions",
            "guide_lead",
            "guide_latency",
            "guide_rollover",
            "guide_brightness",
            "guide_palette",
        ):
            self.toast.emit("Interrompa a reprodução para alterar este ajuste.")
            return
        previous = dict(self.settings)
        self.profile.config = normalize_settings(dict(self.settings, **{key: value}))
        try:
            self.profile.save()
        except OSError as exc:
            self.profile.config = previous
            self.toast.emit(str(exc))
            return
        self.settingsChanged.emit()
        if key in (
            "layout",
            "performance",
            "intensity",
            "seed",
            "pedal_mode",
            "speed",
            "track_filter",
            "session_mode",
            "expression_engine",
            "expression_profile",
            "guide_mode",
            "guide_arrangement",
            "guide_positions",
            "guide_lead",
            "guide_latency",
            "guide_rollover",
            "guide_brightness",
            "guide_palette",
        ):
            self.prepare()

    @Slot(str, str, str, str, bool, bool)
    def finishSetup(self, theme, layout, style, pedal, tray, motion):
        self.profile.config = normalize_settings(
            dict(
                self.settings,
                theme=theme,
                layout=layout,
                performance=style,
                pedal_mode=pedal,
                minimize_to_tray=tray,
                reduced_motion=motion,
                onboarding_completed=True,
            )
        )
        self.profile.save()
        self.settingsChanged.emit()
        self.prepare()
        self.toast.emit("Tudo pronto. Importe uma música ou escolha uma da coleção.")

    @Slot()
    def skipSetup(self):
        self.setSetting("onboarding_completed", True)

    @Slot()
    def importDialog(self):
        paths, _ = QFileDialog.getOpenFileNames(
            None, "Importar músicas", "", "Músicas (*.mid *.midi *.piano.json *.json *.txt)"
        )
        self.importPaths(paths)

    @Slot("QVariantList")
    def importPaths(self, paths):
        if self.importing or self.status != "idle" or not paths:
            return
        paths = [QUrl(p).toLocalFile() if str(p).startswith("file:") else str(p) for p in paths]
        self.importing = True
        self.playbackChanged.emit()

        def run():
            identifiers, errors = [], []
            for path in paths:
                if self.closing:
                    break
                try:
                    identifiers.append(self.profile.import_file(path).ident)
                except Exception as exc:
                    errors.append(f"{Path(path).name}: {exc}")
            return identifiers, errors

        self.task("import", run)

    @Slot()
    @Slot(str)
    def toggleFavorite(self, ident=""):
        if (self.current or ident) and not self.importing:
            try:
                self.profile.favorite(ident or self.current.ident)
            except OSError as exc:
                self.toast.emit(str(exc))
                return
            self.libraryChanged.emit()
            self.songChanged.emit()

    @Slot(str)
    def renameSong(self, title):
        if not self.current or self.status != "idle" or self.importing:
            return
        try:
            self.current = self.profile.rename(self.current.ident, title)
            self.libraryChanged.emit()
            self.songChanged.emit()
        except (OSError, ValueError) as exc:
            self.toast.emit(str(exc))

    @Slot()
    def deleteSong(self):
        if not self.current or self.status != "idle" or self.importing:
            return
        try:
            self.profile.delete(self.current.ident)
            self.current = None
            self.selectSong(self.profile.items[0].ident if self.profile.items else "")
            self.libraryChanged.emit()
            self.toast.emit("Música removida. Use Desfazer nas configurações da biblioteca.")
        except (OSError, ValueError) as exc:
            self.toast.emit(str(exc))

    @Slot()
    def undoDelete(self):
        if self.status != "idle" or self.importing:
            return
        try:
            item = self.profile.restore_deleted()
            if item:
                self.selectSong(item.ident)
                self.libraryChanged.emit()
        except (OSError, ValueError) as exc:
            self.toast.emit(str(exc))

    @Slot(float)
    def seek(self, position):
        if self.status == "idle" and self.prepared:
            self.position = self.offset = max(0, min(position, self.prepared.duration - 0.001))
            self.playbackChanged.emit()

    @Slot(str)
    def markLoop(self, mark):
        if self.status != "idle" or not self.prepared:
            return
        if mark == "clear":
            self.setSetting("loop_enabled", False)
            return
        if mark == "a":
            self.setSetting("loop_start", self.position)
            self.setSetting("loop_enabled", False)
        elif mark == "b":
            if self.position <= self.settings["loop_start"] + 0.02:
                self.toast.emit("Mova o cursor para depois do início do trecho.")
                return
            self.setSetting("loop_end", self.position)
            self.setSetting("loop_enabled", True)

    @Slot()
    def start(self):
        if (
            self.status != "idle"
            or self.preparing
            or not self.prepared
            or self.features_state["chromaState"] == "testing"
        ):
            return
        if self.settings["session_mode"] == "guided":
            if not self.settings["guide_calibrated"] and not self.preview:
                self.toast.emit("Teste e confirme as luzes nas configurações do modo guiado.")
                return
            if self.features_state["manualIssues"]:
                self.toast.emit(
                    "Há combinações incompatíveis. Simplifique ou distribua os acordes para praticar."
                )
                return
        source = (
            manual_song(self.prepared, self.settings["guide_arrangement"])
            if self.settings["session_mode"] == "guided"
            else self.prepared
        )
        offset = self.settings["loop_start"] if self.settings["loop_enabled"] else self.offset
        end = self.settings["loop_end"] if self.settings["loop_enabled"] else None
        song = excerpt(source, offset, end)
        if not song.notes:
            self.toast.emit("O trecho escolhido não contém notas.")
            return
        self.begin(song, offset)

    @Slot(str)
    def testInstrument(self, kind):
        if self.status != "idle":
            return
        if kind == "pedal":
            song = Song(
                "Teste do pedal",
                [Note("t", 0, 3, gate_duration=0.25), Note("u", 2, 0.3)],
                pedal=[
                    PedalChange(0, True),
                    PedalChange(1.5, False),
                    PedalChange(2, True),
                    PedalChange(3, False),
                ],
            )
        else:
            song = Song(
                "Teste de alcance",
                [
                    Note(MIDI_TO_KEY_88[p], i * 0.65, 0.35, pitch=p)
                    for i, p in enumerate(
                        (21, 36, 60, 96, 108)
                        if self.settings["layout"] == "88"
                        else (36, 60, 84, 96)
                    )
                ],
            )
        self.begin(song, 0, test=True)

    def begin(self, song, offset, test=False):
        config = dict(self.settings)
        if config["loop_enabled"]:
            config["repeat"] = True
        if test:
            config.update(pedal_mode="midi", speed=100, repeat=False, session_mode="auto")
        self.keyboard.mode = config["mode"]
        self.status = "countdown"
        self.cancel = threading.Event()
        self.soft_stop = threading.Event()
        self.features_state["summary"] = ""
        self.playbackChanged.emit()

        def perform():
            failure = None
            try:
                deadline = time.perf_counter() + config["countdown"]
                last = 0
                while time.perf_counter() < deadline:
                    if self.cancel.is_set():
                        raise PlaybackStopped("Reprodução interrompida.")
                    remaining = int(deadline - time.perf_counter()) + 1
                    if remaining != last:
                        self.completed.emit("countdown", remaining)
                        last = remaining
                    self.cancel.wait(0.025)
                target = self.keyboard.foreground()
                if self.keyboard.is_own_window(target) or not self.keyboard.is_target_window(
                    target
                ):
                    raise PlaybackStopped(
                        "Selecione a janela do Roblox durante a contagem e deixe o piano aberto."
                    )
                if any(self.keyboard.down(vk) for vk in (0x10, 0x11, 0x12, 0x5B, 0x5C, 0x20)):
                    raise PlaybackStopped(
                        "Solte Espaço e as teclas modificadoras antes de começar."
                    )
                while True:
                    self.completed.emit("session-speed", config["speed"])
                    self.completed.emit("started", (time.perf_counter(), offset))
                    if config["session_mode"] == "guided":
                        with Chroma(
                            config["guide_positions"], config["guide_brightness"]
                        ) as chroma:
                            result = guide_song(
                                song,
                                config["speed"] / 100,
                                self.keyboard,
                                self.cancel,
                                target,
                                chroma,
                                config,
                                lambda p, stats, active: self.completed.emit(
                                    "guide-progress", (p, stats, active)
                                ),
                                self.soft_stop,
                            )
                        self.completed.emit("guide-result", result)
                        if (
                            config["guide_ramp"]
                            and result["hits"] >= result["total"] * 0.8
                            and config["speed"] < 100
                        ):
                            config["speed"] = min(100, config["speed"] + 5)
                    else:
                        play_song(
                            song,
                            config["speed"] / 100,
                            self.keyboard,
                            self.cancel,
                            target,
                            lambda *args: None,
                            config["pedal_mode"],
                            self.soft_stop,
                        )
                    if not config["repeat"] or test:
                        break
                    if self.cancel.wait(0.4):
                        raise PlaybackStopped("Reprodução interrompida.")
                    if self.soft_stop.is_set():
                        raise PlaybackStopped("Parada suave concluída.")
            except PlaybackStopped as exc:
                failure = str(exc)
            except Exception as exc:
                logging.exception("Falha na reprodução")
                failure = str(exc)
            finally:
                try:
                    if config["session_mode"] != "guided":
                        self.keyboard.release_all()
                except Exception as exc:
                    failure = str(exc)
                if not self.closing:
                    self.completed.emit("done", failure)

        self.worker = threading.Thread(target=perform, daemon=True, name="tessera-player")
        self.worker.start()

    @Slot()
    def stop(self):
        if self.status == "idle":
            return
        if self.status in ("countdown", "stopping"):
            self.stopNow()
            return
        self.soft_stop.set()
        self.status = "stopping"
        self.message = "Concluindo a frase… · Esc interrompe agora"
        self.playbackChanged.emit()

    @Slot()
    def stopNow(self):
        if self.status != "idle":
            self.cancel.set()
            self.status = "stopping"
            self.message = "Soltando as teclas…"
            self.playbackChanged.emit()

    def tick(self):
        if self.closing:
            if (not self.worker or not self.worker.is_alive()) and not self.tasks:
                QApplication.instance().quit()
            return
        keys = {key: self.keyboard.down(key) for key in (0x75, 0x77, 0x1B)}
        if keys[0x1B]:
            self.stopNow()
        elif keys[0x77] and not self.hotkeys.get(0x77):
            self.stop()
        elif keys[0x75] and not self.hotkeys.get(0x75):
            self.start()
        self.hotkeys = keys
        if (
            self.status in ("playing", "stopping")
            and self.started is not None
            and self.settings["session_mode"] != "guided"
        ):
            total = self.prepared.duration if self.prepared else 0
            self.position = min(
                total,
                self.origin + (time.perf_counter() - self.started) * self.settings["speed"] / 100,
            )
            self.playbackChanged.emit()

    @Slot()
    def checkUpdates(self):
        if self.updater["state"] in ("checking", "downloading"):
            return
        self.updater.update(state="checking", message="Consultando versões no GitHub…")
        self.updateChanged.emit()
        self.setSetting("last_update_check", time.time())
        self.task("check", lambda: updates.check_release(self.settings["update_channel"]))

    @Slot()
    def downloadUpdate(self):
        if not self.update_manifest or self.updater["state"] == "downloading":
            return
        self.updater.update(
            state="downloading", message="Baixando e verificando a atualização…", progress=0
        )
        self.updateChanged.emit()
        self.download_cancel.clear()
        self.task(
            "download",
            lambda: updates.download_update(
                self.update_manifest,
                self.profile.directory / "updates",
                lambda p: self.completed.emit("download-progress", p),
                self.download_cancel,
                allow_prerelease=self.settings["update_channel"] == "beta",
            ),
        )

    @Slot()
    def installUpdate(self):
        if self.status != "idle" or self.importing:
            self.toast.emit("Interrompa a reprodução antes de atualizar.")
            return
        if self.update_installer:
            try:
                updates.launch_installer(
                    self.update_installer,
                    self.profile.directory,
                    allow_prerelease=self.settings["update_channel"] == "beta",
                )
                self.quit()
            except Exception as exc:
                self.toast.emit(str(exc))

    @Slot()
    def cancelDownload(self):
        self.download_cancel.set()

    @Slot(str)
    def openLink(self, kind):
        urls = {
            "github": f"https://github.com/{updates.REPOSITORY}",
            "game": "https://www.roblox.com/games/5593470048/Visual-Pianos",
        }
        local = (
            BASE / "resources" / "REPERTOIRE_LICENSES.txt"
            if kind == "licenses"
            else self.profile.directory
        )
        QDesktopServices.openUrl(
            QUrl(urls[kind]) if kind in urls else QUrl.fromLocalFile(str(local))
        )

    def create_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(QIcon(str(BASE / "resources/icons/tessera.ico")), self)
        self.tray.setToolTip("Tessera Piano")
        menu = QMenu()
        menu.addAction("Abrir Tessera Piano", self.show_window)
        menu.addSeparator()
        self.tray_play = menu.addAction("Reproduzir · F6", self.start)
        self.tray_stop = menu.addAction("Parar · F8", self.stop)
        menu.addSeparator()
        menu.addAction("Sair", self.quit)
        self.tray_menu = menu
        menu.setFont(QFont("Segoe UI", 10))
        menu.aboutToShow.connect(self.refresh_tray)
        self.refresh_tray()
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: (
                self.show_window()
                if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick)
                else None
            )
        )
        self.tray.show()

    def refresh_tray(self):
        if not self.tray:
            return
        busy = self.status != "idle"
        self.tray_play.setEnabled(not busy and not self.preparing and self.prepared is not None)
        self.tray_stop.setEnabled(busy)
        light = self.settings["theme"] == "light" or (
            self.settings["theme"] == "system" and self.systemLight
        )
        if getattr(self, "tray_light", None) == light:
            return
        self.tray_light = light
        bg, text, line, hover, muted = (
            ("#faf8f1", "#293431", "#d2ccbf", "#e6e1d4", "#68756e")
            if light
            else ("#222c30", "#f0eee7", "#3b484c", "#344145", "#8b9c9c")
        )
        self.tray_menu.setStyleSheet(
            f"QMenu {{ background: {bg}; color: {text}; border: 1px solid {line}; padding: 6px; }}"
            "QMenu::item { padding: 10px 20px; border-radius: 6px; }"
            f"QMenu::item:selected {{ background: {hover}; }}"
            f"QMenu::item:disabled {{ color: {muted}; }}"
            f"QMenu::separator {{ height: 1px; background: {line}; margin: 5px 10px; }}"
        )

    @Slot()
    def show_window(self):
        if self.window:
            self.window.showNormal()
            self.window.raise_()
            self.window.requestActivate()

    @Slot(result=bool)
    def closeWindow(self):
        self.save_window()
        if (
            self.tray
            and self.settings["minimize_to_tray"]
            and self.settings["onboarding_completed"]
        ):
            self.window.hide()
            if not getattr(self, "tray_notified", False):
                self.tray.showMessage(
                    "Tessera Piano", "O aplicativo continua na bandeja. F8 interrompe a execução."
                )
                self.tray_notified = True
            return False
        self.quit()
        return False

    @Slot()
    def quit(self):
        self.save_window()
        self.closing = True
        self.cancel.set()
        self.download_cancel.set()
        self.prepare_cancel.set()
        self.model_cancel.set()
        if self.window:
            self.window.hide()
        if self.tray:
            self.tray.hide()

    def save_window(self):
        if self.window:
            self.profile.config.update(
                window_width=self.window.width(), window_height=self.window.height()
            )
        try:
            self.profile.save()
        except OSError:
            logging.exception("Não foi possível salvar as preferências ao fechar.")
