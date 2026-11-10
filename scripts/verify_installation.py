"""Ensaios isolados de instalação, atualização e recuperação, sem registro no sistema."""

import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import winreg

from tessera_piano import __version__
from tessera_piano.controller import BASE
from tessera_piano.music import Song, Note


def execute(command, timeout=180):
    subprocess.run(
        [str(part) for part in command],
        timeout=timeout,
        check=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def health(executable, report):
    execute([executable, "--health-check", report], 40)
    return json.loads(report.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--installer", type=Path, required=True)
    args = parser.parse_args()

    def registration():
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Uninstall\TesseraPiano",
            ) as key:
                return {
                    winreg.EnumValue(key, i)[0]: winreg.EnumValue(key, i)[1]
                    for i in range(winreg.QueryInfoKey(key)[1])
                }
        except FileNotFoundError:
            return None

    registration_before = registration()
    workspace = Path(".local").resolve()
    workspace.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="installation-", dir=workspace) as folder:
        root = Path(folder)
        installation = root / "app"
        profile = root / "profile"
        profile.mkdir()
        preferences = profile / "preferencias.json"
        preferences.write_text(
            '{"layout":"88","favorites":["preserved"],"theme":"light"}', encoding="utf-8"
        )
        original = preferences.read_bytes()
        music = profile / "musicas" / "preservada.piano.json"
        music.parent.mkdir()
        music.write_text(Song("Preservada", [Note("t", 0, 1)]).to_text(), encoding="utf-8")
        original_music = music.read_bytes()
        execute(
            [
                args.baseline.resolve(),
                "/VERYSILENT",
                "/SUPPRESSMSGBOXES",
                "/NORESTART",
                "/NOICONS",
                "/TASKS=",
                "/ISOLATEDTEST=1",
                f"/DIR={installation}",
                f"/LOG={root / 'baseline.log'}",
            ]
        )
        executable = installation / "TesseraPiano.exe"
        baseline = health(executable, root / "health-before.json")
        assert baseline["ok"] and baseline["version"] != __version__
        helper = BASE / "resources/apply_update.ps1"

        def apply(expected):
            execute(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-WindowStyle",
                    "Hidden",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    helper,
                    "-Installer",
                    args.installer.resolve(),
                    "-AppProcessId",
                    2147483000,
                    "-InstallDirectory",
                    installation,
                    "-ProfileDirectory",
                    profile,
                    "-ExpectedVersion",
                    expected,
                    "-IsolatedTest",
                    "-NoRestart",
                ]
            )

        # Um relatório com versão inesperada precisa restaurar o executável anterior.
        apply("99.0.0")
        restored = health(executable, root / "health-restored.json")
        assert restored["version"] == baseline["version"], restored
        assert preferences.read_bytes() == original
        assert music.read_bytes() == original_music
        assert registration() == registration_before
        apply(__version__)
        updated = health(executable, root / "health-after.json")
        assert updated["ok"] and updated["version"] == __version__, updated
        assert preferences.read_bytes() == original
        assert music.read_bytes() == original_music
        resources = installation / "_internal/tessera_piano/resources"
        assert not (resources / "sources").exists()
        assert not (resources / "icons/tessera-master.png").exists()
        result = {
            "baseline": baseline["version"],
            "updated": updated["version"],
            "installation": True,
            "rollback": True,
            "preferences_preserved": True,
            "music_preserved": True,
            "obsolete_resources_removed": True,
        }
        (workspace / "installation-report.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        print(json.dumps(result))


if __name__ == "__main__":
    main()
