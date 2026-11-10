"""Verifica widgets QML e a saída simulada; salva capturas para inspeção visual."""

import os
from pathlib import Path
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QSG_RENDER_LOOP", "basic")
os.environ.setdefault("QT_QPA_FONTDIR", str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"))

from PySide6.QtCore import (
    QObject,
    QPointF,
    QTimer,
    QUrl,
    Qt,
    qInstallMessageHandler,
    QEvent,
    QEventLoop,
)
from PySide6.QtGui import QFontDatabase
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from tessera_piano.app import BASE, Controller
from tessera_piano.music import Song, Note
from tessera_piano.storage import Profile


def pause(milliseconds):
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def wait_for(predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        pause(25)
    assert predicate()


def click(window, item, x=None, y=None):
    assert item is not None
    point = item.mapToScene(
        QPointF(item.width() / 2 if x is None else x, item.height() / 2 if y is None else y)
    ).toPoint()
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)


def visual_item(item, name):
    if item.objectName() == name:
        return item
    for child in item.childItems():
        match = visual_item(child, name)
        if match is not None:
            return match


def exercise(app):
    messages = []
    qInstallMessageHandler(lambda kind, ctx, message: messages.append(message))
    QQuickStyle.setStyle("Basic")
    fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    for name in ("segoeui.ttf", "segoeuib.ttf", "segmdl2.ttf", "georgia.ttf"):
        if (fonts / name).exists():
            QFontDatabase.addApplicationFont(str(fonts / name))
    output = Path(os.environ.get("TESSERA_PREVIEW_DIRECTORY", ".local/previews"))
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        profile = Profile(BASE / "resources/music", folder)
        profile.config["reduced_motion"] = os.environ.get("TESSERA_TEST_REDUCED_MOTION") == "1"
        controller = Controller(profile, preview=True)
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("backend", controller)
        engine.load(QUrl.fromLocalFile(str(BASE / "ui/Main.qml")))
        assert engine.rootObjects(), messages
        window = engine.rootObjects()[0]
        controller.window = window
        if os.environ["QT_QPA_PLATFORM"] == "windows":
            window.raise_()
            window.requestActivate()
            assert QTest.qWaitForWindowExposed(window, 3000)
        window.grabWindow()
        pause(400)
        wizard = window.findChild(QObject, "setupWizard")
        assert wizard, messages
        try:
            wait_for(lambda: wizard.property("opened"))
        except AssertionError:
            raise AssertionError(
                {
                    "messages": messages,
                    "wizard": {
                        key: wizard.property(key)
                        for key in ("visible", "opened", "opacity", "scale")
                    },
                    "exposed": window.isExposed(),
                    "dpr": window.devicePixelRatio(),
                }
            ) from None
        assert window.grabWindow().save(str(output / "first-open.png"))
        button = window.findChild(QObject, "setupNext")
        for step in range(5):
            assert wizard.property("step") == step
            if step > 0:
                window.grabWindow().save(str(output / f"setup-{step}.png"))
            point = button.mapToScene(QPointF(button.width() / 2, button.height() / 2)).toPoint()
            QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
            pause(220)
        assert profile.config["onboarding_completed"]
        assert not wizard.property("opened")
        window.findChild(QObject, "notification").close()
        for theme in ("dark", "light"):
            controller.setSetting("theme", theme)
            for page, label in ((0, "library"), (1, "player"), (2, "settings"), (3, "help")):
                window.setProperty("page", page)
                pause(230)
                wait_for(lambda: window.findChild(QObject, "pages").property("opacity") > 0.999)
                pause(150)
                assert window.grabWindow().save(str(output / f"{label}-{theme}.png"))
        source = Path(folder) / "Importação.piano.json"
        source.write_text(
            Song(
                "Importação",
                [Note("t", 0, 0.2, track=0), Note("u", 0.4, 0.2, track=1)],
                metadata={"tracks": [{"id": 0, "name": "Esquerda"}, {"id": 1, "name": "Direita"}]},
            ).to_text(),
            encoding="utf-8",
        )
        controller.importPaths([str(source)])
        deadline = time.monotonic() + 5
        while controller.importing or controller.preparing:
            pause(30)
            assert time.monotonic() < deadline
        assert controller.current.personal
        controller.setSetting("theme", "dark")
        window.setProperty("page", 1)
        pause(250)
        wait_for(lambda: window.findChild(QObject, "pages").property("opacity") > 0.999)
        choice = visual_item(window.contentItem(), "performanceChoice")
        click(window, choice)
        choice_popup = choice.findChild(QObject, "performanceChoicePopup")
        wait_for(lambda: choice_popup.property("opened"))
        wait_for(lambda: visual_item(window.contentItem(), "performanceChoiceOption0") is not None)
        click(window, visual_item(window.contentItem(), "performanceChoiceOption0"))
        assert controller.settings["performance"] == "original"
        wait_for(lambda: not choice_popup.property("visible"))
        click(window, choice)
        wait_for(lambda: choice_popup.property("opened"))
        QTest.keyClick(window, Qt.Key_Down)
        QTest.keyClick(window, Qt.Key_Return)
        wait_for(lambda: not choice_popup.property("visible"))
        assert controller.settings["performance"] == "natural"
        wait_for(lambda: not controller.preparing)
        options = window.findChild(QObject, "songOptions")
        menu = window.findChild(QObject, "songMenu")
        rename = window.findChild(QObject, "renameDialog")
        click(window, options)
        wait_for(lambda: menu.property("opened"))
        window.grabWindow().save(str(output / "song-menu.png"))
        QTest.keyClick(window, Qt.Key_Down)
        QTest.keyClick(window, Qt.Key_Return)
        wait_for(lambda: rename.property("opened"))
        field = window.findChild(QObject, "renameField")
        assert field.property("activeFocus")
        field.setProperty("text", "Nome escolhido")
        window.grabWindow().save(str(output / "rename.png"))
        QTest.keyClick(window, Qt.Key_Return)
        wait_for(lambda: not rename.property("visible"))
        assert controller.song["title"] == "Nome escolhido"
        controller.toggleFavorite()
        assert controller.song["favorite"]
        click(window, window.findChild(QObject, "tracksButton"))
        tracks = window.findChild(QObject, "tracksPopup")
        wait_for(lambda: tracks.property("opened"))
        wait_for(lambda: visual_item(window.contentItem(), "track-1") is not None)
        first_track = visual_item(window.contentItem(), "track-0")
        second_track = visual_item(window.contentItem(), "track-1")
        window.grabWindow().save(str(output / "tracks.png"))
        click(window, first_track)
        assert controller.settings["track_filter"] == [1]
        click(window, second_track)
        assert controller.settings["track_filter"] == [1]
        assert second_track.property("checked")
        click(window, first_track)
        assert controller.settings["track_filter"] == []
        QTest.keyClick(window, Qt.Key_Escape)
        wait_for(lambda: not tracks.property("visible"))
        window.findChild(QObject, "notification").close()
        ident = controller.current.ident
        click(window, options)
        wait_for(lambda: menu.property("opened"))
        click(window, window.findChild(QObject, "deleteAction"))
        deletion = window.findChild(QObject, "deleteDialog")
        wait_for(lambda: deletion.property("opened"))
        window.grabWindow().save(str(output / "delete.png"))
        QTest.keyClick(window, Qt.Key_Escape)
        wait_for(lambda: not deletion.property("visible"))
        assert controller.current.ident == ident
        click(window, options)
        wait_for(lambda: menu.property("opened"))
        click(window, window.findChild(QObject, "deleteAction"))
        wait_for(lambda: deletion.property("opened"))
        click(window, window.findChild(QObject, "deleteAccept"))
        wait_for(lambda: not deletion.property("visible"))
        controller.undoDelete()
        assert controller.current.ident == ident
        while controller.preparing:
            pause(30)
        controller.setSetting("countdown", 1)
        controller.start()
        pause(1150)
        assert controller.status == "playing"
        if controller.tray:
            assert not controller.tray_play.isEnabled()
            assert controller.tray_stop.isEnabled()
        read_key = controller.keyboard.down
        controller.keyboard.down = lambda vk: vk == 0x77
        controller.tick()
        assert controller.status == "stopping" and controller.soft_stop.is_set()
        controller.tick()  # Manter F8 pressionado não vira um segundo pedido.
        assert not controller.cancel.is_set()
        controller.keyboard.down = read_key
        controller.tick()
        wait_for(lambda: controller.status == "idle", timeout=2)
        assert not controller.keyboard.note_labels
        if controller.tray:
            assert controller.tray_play.isEnabled()
            assert not controller.tray_stop.isEnabled()
            controller.tray_menu.resize(controller.tray_menu.sizeHint())
            controller.tray_menu.grab().save(str(output / "tray.png"))
        window.findChild(QObject, "notification").close()
        window.setProperty("page", 2)
        pause(400)
        speed = window.findChild(QObject, "speedSpin")
        click(window, speed, speed.width() - 16, speed.height() / 2)
        assert controller.settings["speed"] == 105
        controller.setSetting("speed", 100)
        window.setProperty("page", 1)
        pause(250)
        session = visual_item(window.contentItem(), "sessionChoice")
        click(window, session)
        session_popup = session.findChild(QObject, "sessionChoicePopup")
        wait_for(lambda: session_popup.property("opened"))
        QTest.keyClick(window, Qt.Key_Down)
        QTest.keyClick(window, Qt.Key_Return)
        wait_for(lambda: not session_popup.property("visible"))
        assert controller.settings["session_mode"] == "guided"
        wait_for(lambda: not controller.preparing)
        guide = visual_item(window.contentItem(), "guideModeChoice")
        click(window, guide)
        guide_popup = guide.findChild(QObject, "guideModeChoicePopup")
        wait_for(lambda: guide_popup.property("opened"))
        QTest.keyClick(window, Qt.Key_Down)
        QTest.keyClick(window, Qt.Key_Return)
        wait_for(lambda: not guide_popup.property("visible"))
        assert controller.settings["guide_mode"] == "practice"
        wait_for(lambda: not controller.preparing)
        controller.seek(0.1)
        controller.markLoop("a")
        controller.seek(0.5)
        controller.markLoop("b")
        assert controller.settings["loop_enabled"]
        assert window.grabWindow().save(str(output / "guided-dark.png"))
        controller.markLoop("clear")
        controller.setSetting("session_mode", "auto")
        wait_for(lambda: not controller.preparing)
        window.setProperty("page", 2)
        pause(250)
        flickable = window.findChild(QObject, "settingsScroll").property("contentItem")
        flickable.setProperty("contentY", 950)
        pause(150)
        assert window.grabWindow().save(str(output / "chroma-settings.png"))
        flickable.setProperty("contentY", 0)
        controller.setSetting("reduced_motion", True)
        assert controller.settings["reduced_motion"]
        for width, height in ((1040, 720), (1600, 1000)):
            window.resize(width, height)
            window.setProperty("page", 1)
            pause(100)
            window.grabWindow().save(str(output / f"player-{width}.png"))
            if width == 1040:
                click(window, window.findChild(QObject, "interpretationButton"))
                panel = window.findChild(QObject, "performancePopup")
                wait_for(lambda: panel.property("opened"))
                window.grabWindow().save(str(output / "performance-compact.png"))
                QTest.keyClick(window, Qt.Key_Escape)
                wait_for(lambda: not panel.property("visible"))
        errors = [
            m
            for m in messages
            if any(
                word in m
                for word in (
                    "TypeError",
                    "ReferenceError",
                    "failed to load",
                    "Binding loop",
                    "binding loop",
                    "Cannot assign",
                )
            )
        ]
        assert not errors, "\n".join(errors)
        controller.closing = True
        controller.timer.stop()
        if controller.tray:
            controller.tray.hide()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.DeferredDelete)
        engine.deleteLater()
        app.sendPostedEvents(None, QEvent.DeferredDelete)
    print(
        "PASS: assistente, temas, seletores, menus, diálogos, faixas, bandeja, reprodução e janela compacta."
    )


def run():
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    errors = []

    def start():
        try:
            exercise(app)
        except Exception as exc:
            errors.append(exc)
        finally:
            app.quit()

    QTimer.singleShot(0, start)
    app.exec()
    if errors:
        raise errors[0]


if __name__ == "__main__":
    run()
