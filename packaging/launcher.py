"""Ponto de entrada usado pelo empacotamento Windows."""

import logging
import sys

if __name__ == "__main__":
    try:
        from tessera_piano.app import main

        main()
    except Exception as exc:
        logging.exception("Falha na inicialização")
        if "--health-check" in sys.argv:
            import json
            from pathlib import Path

            report = Path(sys.argv[sys.argv.index("--health-check") + 1])
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps({"ok": False, "error": repr(exc)}), encoding="utf-8")
            raise SystemExit(1)
        from PySide6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance() or QApplication([])
        QMessageBox.critical(
            None,
            "Tessera Piano",
            "Não foi possível abrir o aplicativo. Consulte tessera.log na pasta de dados do Tessera Piano.",
        )
        raise
