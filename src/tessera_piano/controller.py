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
from .music import Song, Note, PedalChange, apply_layout
from .performance import interpret
from .midi import select_tracks
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
        self.worker = None
        self.offset = 0.0
        self.position = 0.0
        self.started = None
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
            "active": [KEY_TO_MIDI[k] for k in list(self.keyboard.note_labels.values())],
            "pedal": self.keyboard.sustain_enabled,
            "pedalManaged": self.keyboard.pedal_managed,
            "preview": self.preview,
            "importing": self.importing,
        }

    @Property("QVariantMap", notify=updateChanged)
    def update(self):
        return self.updater

    def task(self, kind, function):
        def run():
            try:
                value = function()
            except Exception as exc:
                logging.exception("Falha em %s", kind)
                value = exc
            if not self.closing:
                self.completed.emit(kind, value)

        threading.Thread(target=run, daemon=True, name=f"tessera-{kind}").start()

    @Slot(str, object)
    def _completed(self, kind, value):
        if kind == "prepare":
            if isinstance(value, Exception):
                self.preparing = False
                self.toast.emit(str(value))
            else:
                generation, prepared = value
                if generation != self.generation:
                    return
                self.prepared = prepared
                self.preparing = False
                self.offset = self.position = 0
            self.songChanged.emit()
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
            self.status = "playing"
            self.message = "Tocando no Roblox"
            self.playbackChanged.emit()
        elif kind == "countdown":
            self.countdown = value
            self.message = f"Começa em {value} s. Selecione o piano no Roblox."
            self.playbackChanged.emit()
        elif kind == "done":
            self.started = None
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
        self.prepare()

    def prepare(self):
        self.generation += 1
        generation = self.generation
        self.prepared = None
        if not self.current:
            self.songChanged.emit()
            return
        source = self.current.song
        config = dict(self.settings)
        self.preparing = True
        self.songChanged.emit()

        def process():
            song = apply_layout(source, config["layout"])
            song = select_tracks(song, config["track_filter"])
            return generation, interpret(
                song,
                config["performance"],
                config["intensity"] / 100,
                config["seed"],
                config["pedal_mode"],
                config["speed"] / 100,
            )

        self.task("prepare", process)

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

    @Slot()
    def start(self):
        if self.status != "idle" or self.preparing or not self.prepared:
            return
        song = excerpt(self.prepared, self.offset)
        self.begin(song, self.offset)

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
        if test:
            config.update(pedal_mode="midi", speed=100, repeat=False)
        self.keyboard.mode = config["mode"]
        self.status = "countdown"
        self.cancel = threading.Event()
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
                    self.completed.emit("started", (time.perf_counter(), offset))
                    play_song(
                        song,
                        config["speed"] / 100,
                        self.keyboard,
                        self.cancel,
                        target,
                        lambda *args: None,
                        config["pedal_mode"],
                    )
                    if not config["repeat"] or test:
                        break
                    if self.cancel.wait(0.4):
                        raise PlaybackStopped("Reprodução interrompida.")
            except PlaybackStopped as exc:
                failure = str(exc)
            except Exception as exc:
                logging.exception("Falha na reprodução")
                failure = str(exc)
            finally:
                try:
                    self.keyboard.release_all()
                except Exception as exc:
                    failure = str(exc)
                if not self.closing:
                    self.completed.emit("done", failure)

        self.worker = threading.Thread(target=perform, daemon=True, name="tessera-player")
        self.worker.start()

    @Slot()
    def stop(self):
        if self.status != "idle":
            self.cancel.set()
            self.status = "stopping"
            self.message = "Soltando as teclas…"
            self.playbackChanged.emit()

    def tick(self):
        if self.closing:
            if not self.worker or not self.worker.is_alive():
                QApplication.instance().quit()
            return
        keys = {key: self.keyboard.down(key) for key in (0x75, 0x77, 0x1B)}
        if keys[0x77] or keys[0x1B]:
            self.stop()
        elif keys[0x75] and not self.hotkeys.get(0x75):
            self.start()
        self.hotkeys = keys
        if self.status == "playing" and self.started is not None:
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
        self.task("check", updates.check_release)

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
            ),
        )

    @Slot()
    def installUpdate(self):
        if self.status != "idle" or self.importing:
            self.toast.emit("Interrompa a reprodução antes de atualizar.")
            return
        if self.update_installer:
            try:
                updates.launch_installer(self.update_installer, self.profile.directory)
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
