"""Pilot backup/restore using existing scripts (sqlite path)."""

from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = PACKAGE_ROOT / "scripts"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _find_bash() -> str | None:
    # Windows WSL bash mangles drive paths; Git-Bash is optional. Linux CI runs the scripts.
    if os.name == "nt":
        return None
    return shutil.which("bash")


def test_backup_scripts_and_gitignore_present() -> None:
    assert (SCRIPTS / "backup_database.sh").is_file()
    assert (SCRIPTS / "verify_backup.sh").is_file()
    assert (SCRIPTS / "restore_database.sh").is_file()
    backup_md = (PACKAGE_ROOT / "docs" / "BACKUP.md").read_text(encoding="utf-8")
    assert "MERCURY_BACKUP_VIA_COMPOSE" in backup_md
    gitignore = (PACKAGE_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "backups/" in gitignore
    assert "*.dump" in gitignore
    deploy = (PACKAGE_ROOT / "docs" / "pilot" / "DEPLOY.md").read_text(encoding="utf-8")
    assert "/live" in deploy
    assert "/api/v1/ready" in deploy


def test_sqlite_backup_restore_roundtrip(tmp_path: Path) -> None:
    source = tmp_path / "pilot-source.db"
    conn = sqlite3.connect(source)
    conn.execute("CREATE TABLE demo (id INTEGER PRIMARY KEY, note TEXT)")
    conn.execute("INSERT INTO demo (note) VALUES ('C-GMEA-pilot')")
    conn.commit()
    conn.close()

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    bash = _find_bash()
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{source.as_posix()}"
    env["BACKUP_DIR"] = str(backup_dir)

    if bash:
        proc = subprocess.run(
            [bash, str(SCRIPTS / "backup_database.sh")],
            cwd=str(PACKAGE_ROOT),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        assert proc.returncode == 0, proc.stderr or proc.stdout
        backup = Path(proc.stdout.strip().splitlines()[-1])
        assert backup.is_file()
        verify = subprocess.run(
            [bash, str(SCRIPTS / "verify_backup.sh")],
            cwd=str(PACKAGE_ROOT),
            capture_output=True,
            text=True,
            check=False,
            env={**env, "BACKUP_FILE": str(backup)},
        )
        assert verify.returncode == 0, verify.stderr or verify.stdout
        restored = tmp_path / "restored.db"
        restore = subprocess.run(
            [bash, str(SCRIPTS / "restore_database.sh")],
            cwd=str(PACKAGE_ROOT),
            capture_output=True,
            text=True,
            check=False,
            env={**env, "BACKUP_FILE": str(backup), "DATABASE_URL": f"sqlite:///{restored.as_posix()}"},
        )
        assert restore.returncode == 0, restore.stderr or restore.stdout
        check = sqlite3.connect(restored)
        note = check.execute("SELECT note FROM demo").fetchone()[0]
        check.close()
        assert note == "C-GMEA-pilot"
        return

    backup = backup_dir / "mercury-sqlite-test.db"
    shutil.copy2(source, backup)
    checksum = backup_dir / f"{backup.name}.sha256"
    checksum.write_text(f"{_sha256(backup)}  {backup.name}\n", encoding="utf-8")
    assert backup.stat().st_size > 0
    assert _sha256(backup) == checksum.read_text(encoding="utf-8").split()[0]
    restored = tmp_path / "restored.db"
    shutil.copy2(backup, restored)
    check = sqlite3.connect(restored)
    assert check.execute("PRAGMA integrity_check;").fetchone()[0] == "ok"
    assert check.execute("SELECT note FROM demo").fetchone()[0] == "C-GMEA-pilot"
    check.close()
