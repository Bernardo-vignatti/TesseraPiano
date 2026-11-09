"""Verifica widgets QML e a saída simulada; salva capturas para inspeção visual."""

import os
from pathlib import Path
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, QPointF, QUrl, Qt, qInstallMessageHandler, QEvent
from PySide6.QtGui import QFontDatabase
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from tessera_piano.app import BASE, Controller
from tessera_piano.music import Song, Note
from tessera_piano.storage import Profile


def run():
    messages = []
    qInstallMessageHandler(lambda kind, ctx, message: messages.append(message))
    app = QApplication([])
    QQuickStyle.setStyle("Basic")
    fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    for name in ("segoeui.ttf", "segoeuib.ttf", "segmdl2.ttf"):
        if (fonts / name).exists():
            QFontDatabase.addApplicationFont(str(fonts / name))
    output = Path(os.environ.get("TESSERA_PREVIEW_DIRECTORY", ".local/previews"))
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        profile = Profile(BASE / "resources/music", folder)
        controller = Controller(profile, preview=True)
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("backend", controller)
        engine.load(QUrl.fromLocalFile(str(BASE / "ui/Main.qml")))
        assert engine.rootObjects(), messages
        window = engine.rootObjects()[0]
        controller.window = window
        QTest.qWait(400)
        wizard = window.findChild(QObject, "setupWizard")
        assert wizard and wizard.property("opened")
        assert window.grabWindow().save(str(output / "first-open.png"))
        button = window.findChild(QObject, "setupNext")
        for step in range(5):
            assert wizard.property("step") == step
            if step > 0:
                window.grabWindow().save(str(output / f"setup-{step}.png"))
            point = button.mapToScene(QPointF(button.width() / 2, button.height() / 2)).toPoint()
            QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
            QTest.qWait(220)
        assert profile.config["onboarding_completed"]
        assert not wizard.property("opened")
        window.findChild(QObject, "notification").close()
        for theme in ("dark", "light"):
            controller.setSetting("theme", theme)
            for page, label in ((0, "library"), (1, "player"), (2, "settings"), (3, "help")):
                window.setProperty("page", page)
                QTest.qWait(230)
                assert window.grabWindow().save(str(output / f"{label}-{theme}.png"))
        source = Path(folder) / "Importação.piano.json"
        source.write_text(
            Song("Importação", [Note("t", 0, 0.2), Note("u", 0.4, 0.2)]).to_text(), encoding="utf-8"
        )
        controller.importPaths([str(source)])
        deadline = time.monotonic() + 5
        while controller.importing or controller.preparing:
            QTest.qWait(30)
            assert time.monotonic() < deadline
        assert controller.current.personal
        controller.renameSong("Nome escolhido")
        assert controller.song["title"] == "Nome escolhido"
        controller.toggleFavorite()
        assert controller.song["favorite"]
        ident = controller.current.ident
        controller.deleteSong()
        controller.undoDelete()
        assert controller.current.ident == ident
        while controller.preparing:
            QTest.qWait(30)
        controller.setSetting("countdown", 1)
        controller.start()
        QTest.qWait(1150)
        assert controller.status == "playing"
        controller.stop()
        QTest.qWait(150)
        assert controller.status == "idle"
        assert not controller.keyboard.note_labels
        controller.setSetting("reduced_motion", True)
        assert controller.settings["reduced_motion"]
        for width, height in ((1040, 720), (1600, 1000)):
            window.resize(width, height)
            window.setProperty("page", 1)
            QTest.qWait(100)
            window.grabWindow().save(str(output / f"player-{width}.png"))
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
        "PASS: configuração inicial, 4 páginas, 2 temas, importação, favoritos, exclusão, reprodução, parada e 2 tamanhos."
    )


if __name__ == "__main__":
    run()
