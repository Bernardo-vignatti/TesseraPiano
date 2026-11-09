"""Aplicativo Qt e coordenação entre biblioteca, execução e atualizações."""

from __future__ import annotations

import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import tempfile
import time

from PySide6.QtCore import QTimer, QUrl, QEvent
from PySide6.QtGui import QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from . import __version__
from .storage import Profile

from .controller import Controller, BASE


def main():
    parser = argparse.ArgumentParser(description="Tessera Piano")
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--health-check", type=Path)
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args()
    temporary = None
    if args.health_check:
        import os

        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        temporary = tempfile.TemporaryDirectory()
        args.profile = Path(temporary.name)
        args.preview = True
    app = QApplication(sys.argv[:1])
    from PySide6.QtQuickControls2 import QQuickStyle

    QQuickStyle.setStyle("Basic")
    app.setApplicationName("Tessera Piano")
    app.setOrganizationName("Vignatti")
    app.setApplicationVersion(__version__)
    app.setWindowIcon(QIcon(str(BASE / "resources/icons/tessera.ico")))
    app.setQuitOnLastWindowClosed(False)
    profile = Profile(BASE / "resources/music", args.profile)
    logdir = profile.directory / "logs"
    logdir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            RotatingFileHandler(
                logdir / "tessera.log", maxBytes=500000, backupCount=2, encoding="utf-8"
            )
        ],
        format="%(asctime)s %(levelname)s %(message)s",
    )
    server = None
    if not args.preview and not args.health_check:
        socket = QLocalSocket()
        socket.connectToServer("Vignatti.TesseraPiano.4")
        if socket.waitForConnected(300):
            socket.write(b"activate")
            socket.waitForBytesWritten(300)
            return
        QLocalServer.removeServer("Vignatti.TesseraPiano.4")
        server = QLocalServer()
        server.listen("Vignatti.TesseraPiano.4")
    controller = Controller(profile, args.preview)
    engine = QQmlApplicationEngine()
    engine.warnings.connect(
        lambda errors: logging.warning("QML: %s", "\n".join(e.toString() for e in errors))
    )
    engine.rootContext().setContextProperty("backend", controller)
    engine.load(QUrl.fromLocalFile(str(BASE / "ui/Main.qml")))
    if not engine.rootObjects():
        raise RuntimeError("Não foi possível carregar a interface. Consulte o log do aplicativo.")
    controller.window = engine.rootObjects()[0]
    if server:

        def activate():
            connection = server.nextPendingConnection()
            if connection:
                connection.disconnectFromServer()
            controller.show_window()

        server.newConnection.connect(activate)
    if args.health_check:

        def report():
            args.health_check.parent.mkdir(parents=True, exist_ok=True)
            args.health_check.write_text(
                json.dumps({"ok": True, "version": __version__, "songs": len(profile.items)}),
                encoding="utf-8",
            )
            controller.quit()

        QTimer.singleShot(700, report)
    elif args.screenshot:

        def screenshot():
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            controller.window.grabWindow().save(str(args.screenshot))
            controller.quit()

        QTimer.singleShot(1800, screenshot)
    elif (
        profile.config["check_updates"]
        and time.time() - profile.config["last_update_check"] > 86400
    ):
        QTimer.singleShot(5000, controller.checkUpdates)
    app.exec()
    controller.closing = True
    controller.timer.stop()
    controller.window.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    engine.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    logging.shutdown()
    if temporary:
        temporary.cleanup()
