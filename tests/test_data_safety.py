"""数据库版本、迁移前备份与完整性保护测试。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from data_safety import DatabaseSafetyError, create_database_backup, inspect_database
from database import CURRENT_SCHEMA_VERSION, get_schema_version, init_database


def _create_legacy_database(db_path: Path) -> None:
    """模拟尚无迁移记录、缺少每日任务两列的早期数据库。"""
    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT '普通',
                planned_date TEXT NOT NULL,
                start_time TEXT,
                end_time TEXT,
                time_slot TEXT NOT NULL DEFAULT '全天',
                estimated_minutes INTEGER NOT NULL DEFAULT 30,
                actual_minutes INTEGER NOT NULL DEFAULT 0,
                acceptance_criteria TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT '待开始',
                completion_percentage INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'user',
                goal_id INTEGER,
                must_today INTEGER NOT NULL DEFAULT 0,
                postponement_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );
            """
        )
        connection.execute(
            """
            INSERT INTO tasks (
                title, category, planned_date, acceptance_criteria, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            ("旧数据不能丢", "个人事务", "2026-08-23", "迁移后仍可读取", "2026-08-23T10:00:00"),
        )


def test_new_database_records_schema_version_without_backup(tmp_path: Path) -> None:
    db_path = tmp_path / "new.db"

    init_database(db_path)

    assert get_schema_version(db_path) == CURRENT_SCHEMA_VERSION
    with sqlite3.connect(db_path) as connection:
        versions = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert versions == [(1,), (2,), (3,), (4,)]
    assert not (tmp_path / "backups").exists()


def test_legacy_database_is_backed_up_migrated_and_preserved(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.db"
    _create_legacy_database(db_path)

    init_database(db_path)

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(tasks)").fetchall()
        }
        task = connection.execute(
            "SELECT title, acceptance_criteria FROM tasks WHERE id = 1"
        ).fetchone()
        assert {"recurring_template_id", "counts_toward_capacity"} <= columns
        assert tuple(task) == ("旧数据不能丢", "迁移后仍可读取")
        assert connection.execute("SELECT COUNT(*) FROM goals").fetchone()[0] == 0
    assert get_schema_version(db_path) == CURRENT_SCHEMA_VERSION

    backups = list((tmp_path / "backups").glob("growth-pre-migration-*.db"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1
        assert not connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'"
        ).fetchone()

    init_database(db_path)
    assert len(list((tmp_path / "backups").glob("growth-pre-migration-*.db"))) == 1


def test_manual_backup_is_complete_and_readable(tmp_path: Path) -> None:
    db_path = tmp_path / "source.db"
    init_database(db_path)

    backup_path = create_database_backup(db_path, tmp_path / "manual-backups")

    health = inspect_database(backup_path)
    assert health.ok
    with sqlite3.connect(db_path) as source, sqlite3.connect(backup_path) as backup:
        assert source.execute("SELECT COUNT(*) FROM tasks").fetchone() == backup.execute(
            "SELECT COUNT(*) FROM tasks"
        ).fetchone()
        assert source.execute("SELECT COUNT(*) FROM habits").fetchone() == backup.execute(
            "SELECT COUNT(*) FROM habits"
        ).fetchone()


def test_corrupt_database_is_not_migrated_or_backed_up(tmp_path: Path) -> None:
    db_path = tmp_path / "broken.db"
    db_path.write_bytes(b"not-a-sqlite-database")

    with pytest.raises(DatabaseSafetyError):
        init_database(db_path)

    assert db_path.read_bytes() == b"not-a-sqlite-database"
    assert not (tmp_path / "backups").exists()
