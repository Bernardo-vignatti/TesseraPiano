"""Renderiza o estudo QML isolado, sem iniciar o aplicativo ou enviar teclas."""

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"))

from PySide6.QtCore import QObject, QPointF, QUrl, Qt, QEvent, qInstallMessageHandler
from PySide6.QtGui import QFontDatabase
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--interactive", action="store_true", help="Abre apenas o protótipo visual."
    )
    args = parser.parse_args()
    if args.interactive:
        os.environ.pop("QT_QPA_PLATFORM", None)
    messages = []
    qInstallMessageHandler(lambda kind, context, message: messages.append(message))
    app = QApplication([])
    QQuickStyle.setStyle("Basic")
    fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    for name in ("segoeui.ttf", "segoeuib.ttf", "segoeuisl.ttf", "segmdl2.ttf", "georgia.ttf"):
        if (fonts / name).exists():
            QFontDatabase.addApplicationFont(str(fonts / name))
    data = json.loads(
        (ROOT / "src/tessera_piano/resources/music/00_Entre_Orbitas.piano.json").read_text(
            encoding="utf-8"
        )
    )
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty(
        "previewNotes", [note for note in data["notes"] if note["start"] < 32]
    )
    engine.load(QUrl.fromLocalFile(str(HERE / "Preview.qml")))
    if not engine.rootObjects():
        raise RuntimeError("\n".join(messages))
    window = engine.rootObjects()[0]
    if args.interactive:
        app.exec()
        return
    QTest.qWait(700)
    assert window.grabWindow().save(str(HERE / "preview.png"))
    select = window.findChild(QObject, "styleSelect")
    point = select.mapToScene(QPointF(select.width() / 2, select.height() / 2)).toPoint()
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
    QTest.qWait(200)
    menu = window.findChild(QObject, "interpretationPopup")
    assert menu.property("opened")
    assert window.grabWindow().save(str(HERE / "preview-menu.png"))
    QTest.keyClick(window, Qt.Key_Escape)
    QTest.qWait(150)
    assert not menu.property("opened")
    play = window.findChild(QObject, "previewPlay")
    point = play.mapToScene(QPointF(play.width() / 2, play.height() / 2)).toPoint()
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
    assert window.property("playing")
    QTest.qWait(100)
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
    assert not window.property("playing")
    errors = [
        m for m in messages if any(s in m for s in ("Error", "Cannot", "binding loop", "Unable to"))
    ]
    if errors:
        raise AssertionError("\n".join(errors))
    window.close()
    engine.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    print(
        json.dumps(
            {
                "rendered": ["preview.png", "preview-menu.png"],
                "menu": "passed",
                "transport": "passed",
                "qml_messages": messages,
            }
        )
    )


if __name__ == "__main__":
    main()
