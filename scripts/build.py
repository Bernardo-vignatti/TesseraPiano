"""Gera executável e instalador Windows usando o ambiente atual."""

import argparse
import importlib.metadata
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--iscc", type=Path, default=Path.home() / "AppData/Local/Programs/Inno Setup 6/ISCC.exe"
    )
    args = parser.parse_args()
    from tessera_piano import __version__

    if sys.platform != "win32":
        raise SystemExit("O instalador deve ser compilado no Windows.")
    if not args.iscc.exists():
        raise SystemExit("Inno Setup 6 não encontrado. Informe --iscc CAMINHO.")
    subprocess.run(
        [
            sys.executable,
            "-c",
            "from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtQuickControls2, QtWidgets",
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--windowed",
            "--name",
            "TesseraPiano",
            "--paths",
            str(ROOT / "src"),
            "--icon",
            str(ROOT / "src/tessera_piano/resources/icons/tessera.ico"),
            "--add-data",
            f"{ROOT / 'src/tessera_piano/ui'};tessera_piano/ui",
            "--add-data",
            f"{ROOT / 'src/tessera_piano/resources'};tessera_piano/resources",
            "--exclude-module",
            "tkinter",
            "--exclude-module",
            "PySide6.QtWebEngineCore",
            "--exclude-module",
            "PySide6.QtPdf",
            "--exclude-module",
            "PySide6.Qt3DCore",
            str(ROOT / "packaging/launcher.py"),
        ],
        cwd=ROOT,
        check=True,
    )
    distribution = ROOT / "dist/TesseraPiano"
    # Qt usa a ICU do Windows; uma DLL de outro programa no PATH pode ter ABI incompatível.
    (distribution / "_internal/icuuc.dll").unlink(missing_ok=True)
    for pattern in ("icudt*.dll", "icuin*.dll"):
        for library in (distribution / "_internal").glob(pattern):
            library.unlink()
    report = ROOT / "dist/build-health.json"
    report.unlink(missing_ok=True)
    subprocess.run(
        [str(distribution / "TesseraPiano.exe"), "--health-check", str(report)],
        timeout=40,
        check=True,
    )
    if not report.exists():
        raise SystemExit("O executável compilado não passou na verificação de inicialização.")
    for filename in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / filename, distribution / filename)
    licenses = distribution / "licenses"
    licenses.mkdir(exist_ok=True)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.exists():
        shutil.copy2(python_license, licenses / "Python.txt")
    for name in (
        "PySide6-Essentials",
        "shiboken6",
        "mido",
        "cryptography",
        "packaging",
        "cffi",
        "pycparser",
    ):
        package = importlib.metadata.distribution(name)
        for file in package.files or []:
            if "/licenses/" in str(file).replace("\\", "/"):
                target = licenses / name / Path(str(file).split("licenses/", 1)[1])
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(package.locate_file(file), target)
    shutil.copytree(ROOT / "packaging/licenses", licenses, dirs_exist_ok=True)
    subprocess.run(
        [
            str(args.iscc),
            f"/DAppVersion={__version__}",
            f"/DBuildDirectory={distribution}",
            str(ROOT / "packaging/installer.iss"),
        ],
        check=True,
        cwd=ROOT,
    )
    print(ROOT / f"dist/TesseraPiano-Setup-{__version__}-x64.exe")


if __name__ == "__main__":
    main()
