from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ICON = ASSETS / "app.ico"
DIST = ROOT / "dist"
BUILD = ROOT / "build"


def configure_tcl() -> None:
    base = Path(sys.base_prefix)
    tcl = base / "tcl" / "tcl8.6"
    tk = base / "tcl" / "tk8.6"
    if tcl.exists():
        os.environ.setdefault("TCL_LIBRARY", str(tcl))
    if tk.exists():
        os.environ.setdefault("TK_LIBRARY", str(tk))


def main() -> None:
    configure_tcl()
    if not ICON.exists():
        raise SystemExit(f"缺少应用图标: {ICON}")
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        "NaiWaDesktopPet",
        "--icon",
        str(ICON),
        "--collect-submodules",
        "pystray",
        "--add-data",
        f"{ASSETS}{os.pathsep}assets",
        "--distpath",
        str(DIST),
        "--workpath",
        str(BUILD / "work"),
        "--specpath",
        str(BUILD),
        str(ROOT / "main.py"),
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    exe = DIST / "NaiWaDesktopPet.exe"
    if not exe.exists():
        raise SystemExit("PyInstaller 未生成 NaiWaDesktopPet.exe")
    print(f"Built {exe} ({exe.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
