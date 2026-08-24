"""SQLite 健康检查与一致性备份。

该模块不依赖应用业务层，因此数据库初始化和设置页面都可以安全复用。
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


class DatabaseSafetyError(RuntimeError):
    """数据库不适合继续迁移或备份时抛出。"""


@dataclass(frozen=True)
class DatabaseHealth:
    path: Path
    size_bytes: int
    integrity: str
    foreign_key_issues: tuple[tuple[object, ...], ...]
    tables: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return self.integrity == "ok" and not self.foreign_key_issues


def _readonly_uri(path: Path) -> str:
    return f"{path.resolve().as_uri()}?mode=ro"


def inspect_database(db_path: Path | str) -> DatabaseHealth:
    """只读检查 SQLite 完整性、外键和当前表。"""
    path = Path(db_path).resolve()
    if not path.is_file() or path.stat().st_size <= 0:
        raise DatabaseSafetyError(f"数据库不存在或为空：{path}")
    try:
        with sqlite3.connect(_readonly_uri(path), uri=True) as connection:
            integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
            foreign_key_issues = tuple(
                tuple(row) for row in connection.execute("PRAGMA foreign_key_check").fetchall()
            )
            tables = tuple(
                row[0]
                for row in connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                    """
                ).fetchall()
            )
    except sqlite3.Error as error:
        raise DatabaseSafetyError(f"无法读取数据库：{path}") from error
    return DatabaseHealth(
        path=path,
        size_bytes=path.stat().st_size,
        integrity=integrity,
        foreign_key_issues=foreign_key_issues,
        tables=tables,
    )


def default_backup_directory(db_path: Path | str) -> Path:
    path = Path(db_path).resolve()
    if path.parent.name.lower() == "data":
        return path.parent.parent / "backups"
    return path.parent / "backups"


def create_database_backup(
    db_path: Path | str,
    backup_dir: Path | str | None = None,
    *,
    label: str = "manual",
    now: datetime | None = None,
) -> Path:
    """使用 SQLite Backup API 创建可在应用运行时保持一致的备份。"""
    source_path = Path(db_path).resolve()
    source_health = inspect_database(source_path)
    if not source_health.ok:
        raise DatabaseSafetyError(
            "源数据库完整性检查未通过，已停止备份；请先保留现场并排查。"
        )

    destination_dir = (
        Path(backup_dir).resolve()
        if backup_dir is not None
        else default_backup_directory(source_path)
    )
    destination_dir.mkdir(parents=True, exist_ok=True)
    safe_label = re.sub(r"[^A-Za-z0-9_-]+", "-", label).strip("-") or "backup"
    timestamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S-%f")
    destination_path = destination_dir / f"growth-{safe_label}-{timestamp}.db"

    try:
        with sqlite3.connect(_readonly_uri(source_path), uri=True) as source:
            with sqlite3.connect(destination_path) as destination:
                source.backup(destination)
    except sqlite3.Error as error:
        raise DatabaseSafetyError(f"数据库备份失败：{destination_path}") from error

    backup_health = inspect_database(destination_path)
    if not backup_health.ok:
        raise DatabaseSafetyError(
            f"备份已生成但完整性检查未通过，请勿用于恢复：{destination_path}"
        )
    return destination_path
