"""SQLite 数据访问层：Schema、默认数据与参数化 CRUD。"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterator, Sequence

from data_safety import DatabaseSafetyError, create_database_backup, inspect_database


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(
    os.environ.get("GROWTH_OS_DB_PATH", str(BASE_DIR / "data" / "growth.db"))
).resolve()


class DatabaseMigrationError(RuntimeError):
    """数据库版本异常或迁移定义不一致。"""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    checksum: str
    apply: Callable[[sqlite3.Connection], None]


def _migration_checksum(identity: str) -> str:
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


@contextmanager
def get_connection(db_path: Path | str = DB_PATH) -> Iterator[sqlite3.Connection]:
    """提供自动提交/回滚的 SQLite 连接。"""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_database(db_path: Path | str = DB_PATH) -> None:
    """创建新库或迁移旧库；只有真正的新库才写入初始化数据。"""
    path = Path(db_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new_database = not path.exists() or path.stat().st_size == 0

    if not is_new_database:
        health = inspect_database(path)
        if not health.ok:
            raise DatabaseSafetyError("数据库完整性检查未通过，已停止自动迁移。")
        pending = pending_migration_versions(path)
        if pending:
            current = get_schema_version(path)
            create_database_backup(
                path,
                label=f"pre-migration-v{current}-to-v{CURRENT_SCHEMA_VERSION}",
            )

    with get_connection(path) as connection:
        _create_schema(connection)
        _apply_migrations(connection)
        if is_new_database:
            _seed_defaults(connection)

    health = inspect_database(path)
    if not health.ok:
        raise DatabaseSafetyError("数据库初始化后完整性检查未通过。")


def _create_schema(connection: sqlite3.Connection) -> None:
    """幂等保证当前版本所需的表和索引存在。"""
    connection.executescript(
        """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                checksum TEXT NOT NULL,
                applied_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS directions (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                long_term_vision TEXT NOT NULL DEFAULT '',
                primary_conflict TEXT NOT NULL DEFAULT '',
                secondary_conflicts TEXT NOT NULL DEFAULT '',
                current_priority TEXT NOT NULL DEFAULT '',
                not_doing TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER REFERENCES goals(id) ON DELETE SET NULL,
                level TEXT NOT NULL CHECK (level IN ('long_term', 'stage', 'weekly')),
                name TEXT NOT NULL,
                why TEXT NOT NULL DEFAULT '',
                start_date TEXT,
                target_date TEXT,
                progress INTEGER NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
                success_criteria TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT '进行中',
                is_current INTEGER NOT NULL DEFAULT 0 CHECK (is_current IN (0, 1)),
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT '普通',
                planned_date TEXT NOT NULL,
                start_time TEXT,
                end_time TEXT,
                time_slot TEXT NOT NULL DEFAULT '全天',
                estimated_minutes INTEGER NOT NULL DEFAULT 30 CHECK (estimated_minutes >= 0),
                actual_minutes INTEGER NOT NULL DEFAULT 0 CHECK (actual_minutes >= 0),
                acceptance_criteria TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT '待开始',
                completion_percentage INTEGER NOT NULL DEFAULT 0 CHECK (completion_percentage BETWEEN 0 AND 100),
                notes TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'user' CHECK (source IN ('system', 'user')),
                goal_id INTEGER REFERENCES goals(id) ON DELETE SET NULL,
                must_today INTEGER NOT NULL DEFAULT 0 CHECK (must_today IN (0, 1)),
                postponement_count INTEGER NOT NULL DEFAULT 0,
                recurring_template_id INTEGER REFERENCES recurring_task_templates(id) ON DELETE SET NULL,
                counts_toward_capacity INTEGER NOT NULL DEFAULT 1 CHECK (counts_toward_capacity IN (0, 1)),
                created_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_planned_date ON tasks(planned_date);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_category ON tasks(category);

            CREATE TABLE IF NOT EXISTS recurring_task_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT '普通',
                start_time TEXT,
                end_time TEXT,
                time_slot TEXT NOT NULL DEFAULT '全天',
                estimated_minutes INTEGER NOT NULL DEFAULT 30 CHECK (estimated_minutes >= 0),
                acceptance_criteria TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                goal_id INTEGER REFERENCES goals(id) ON DELETE SET NULL,
                must_today INTEGER NOT NULL DEFAULT 1 CHECK (must_today IN (0, 1)),
                counts_toward_capacity INTEGER NOT NULL DEFAULT 1 CHECK (counts_toward_capacity IN (0, 1)),
                active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                target_minutes INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS habit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
                log_date TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),
                minutes INTEGER NOT NULL DEFAULT 0 CHECK (minutes >= 0),
                notes TEXT NOT NULL DEFAULT '',
                UNIQUE(habit_id, log_date)
            );

            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                list_type TEXT NOT NULL CHECK (list_type IN ('核心书单', '扩展书单')),
                stage TEXT NOT NULL,
                category TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                purpose TEXT NOT NULL,
                estimated_weeks INTEGER NOT NULL DEFAULT 4,
                total_pages INTEGER NOT NULL DEFAULT 0,
                current_page INTEGER NOT NULL DEFAULT 0,
                start_date TEXT,
                target_date TEXT,
                status TEXT NOT NULL DEFAULT '待读',
                today_minutes INTEGER NOT NULL DEFAULT 0,
                total_minutes INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                is_light_reading INTEGER NOT NULL DEFAULT 0 CHECK (is_light_reading IN (0, 1))
            );

            CREATE TABLE IF NOT EXISTS reading_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
                log_date TEXT NOT NULL,
                minutes INTEGER NOT NULL CHECK (minutes > 0),
                pages_read INTEGER NOT NULL DEFAULT 0 CHECK (pages_read >= 0),
                learned TEXT NOT NULL DEFAULT '',
                changed_view TEXT NOT NULL DEFAULT '',
                real_world_link TEXT NOT NULL DEFAULT '',
                application TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS daily_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                review_date TEXT NOT NULL UNIQUE,
                events TEXT NOT NULL DEFAULT '',
                main_task_done TEXT NOT NULL DEFAULT '',
                biggest_gain TEXT NOT NULL DEFAULT '',
                learning_improvement TEXT NOT NULL DEFAULT '',
                life_improvement TEXT NOT NULL DEFAULT '',
                work_problem TEXT NOT NULL DEFAULT '',
                life_state TEXT NOT NULL DEFAULT '',
                growth_thought TEXT NOT NULL DEFAULT '',
                time_waste TEXT NOT NULL DEFAULT '',
                tomorrow_main_task TEXT NOT NULL DEFAULT '',
                reduce_items TEXT NOT NULL DEFAULT '',
                keep_items TEXT NOT NULL DEFAULT '',
                problem_to_solve TEXT NOT NULL DEFAULT '',
                free_text TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );
        """
    )


def _migration_001_baseline(connection: sqlite3.Connection) -> None:
    """记录现有 V1 基线；实际表由 _create_schema 幂等保证。"""


def _migration_002_task_recurrence(connection: sqlite3.Connection) -> None:
    """兼容早期任务表，只新增每日任务关联和容量口径。"""
    columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(tasks)").fetchall()
    }
    if "recurring_template_id" not in columns:
        connection.execute(
            "ALTER TABLE tasks ADD COLUMN recurring_template_id INTEGER REFERENCES recurring_task_templates(id) ON DELETE SET NULL"
        )
    if "counts_toward_capacity" not in columns:
        connection.execute(
            "ALTER TABLE tasks ADD COLUMN counts_toward_capacity INTEGER NOT NULL DEFAULT 1 CHECK (counts_toward_capacity IN (0, 1))"
        )
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_recurring_date
        ON tasks(recurring_template_id, planned_date)
        WHERE recurring_template_id IS NOT NULL
        """
    )


def _migration_003_study_diary(connection: sqlite3.Connection) -> None:
    """增加一天一页日记、方向快照和低摩擦灵感箱。"""
    direction_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(directions)").fetchall()
    }
    if "current_stage" not in direction_columns:
        connection.execute(
            "ALTER TABLE directions ADD COLUMN current_stage TEXT NOT NULL DEFAULT ''"
        )
    if "current_goal" not in direction_columns:
        connection.execute(
            "ALTER TABLE directions ADD COLUMN current_goal TEXT NOT NULL DEFAULT ''"
        )

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS daily_journals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journal_date TEXT NOT NULL UNIQUE,
            mood TEXT NOT NULL DEFAULT '',
            focus TEXT NOT NULL DEFAULT '',
            secondary_focus_1 TEXT NOT NULL DEFAULT '',
            secondary_focus_2 TEXT NOT NULL DEFAULT '',
            day_story TEXT NOT NULL DEFAULT '',
            learning_notes TEXT NOT NULL DEFAULT '',
            technical_gain TEXT NOT NULL DEFAULT '',
            life_notes TEXT NOT NULL DEFAULT '',
            growth_thoughts TEXT NOT NULL DEFAULT '',
            reading_note TEXT NOT NULL DEFAULT '',
            exercise_minutes INTEGER NOT NULL DEFAULT 0 CHECK (exercise_minutes >= 0),
            exercise_content TEXT NOT NULL DEFAULT '',
            review_best TEXT NOT NULL DEFAULT '',
            review_problem TEXT NOT NULL DEFAULT '',
            review_gain TEXT NOT NULL DEFAULT '',
            improvement_learning TEXT NOT NULL DEFAULT '',
            improvement_life TEXT NOT NULL DEFAULT '',
            improvement_self TEXT NOT NULL DEFAULT '',
            tomorrow_focus TEXT NOT NULL DEFAULT '',
            self_message TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS goal_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT NOT NULL UNIQUE,
            long_term_vision TEXT NOT NULL DEFAULT '',
            current_stage TEXT NOT NULL DEFAULT '',
            current_goal TEXT NOT NULL DEFAULT '',
            primary_conflict TEXT NOT NULL DEFAULT '',
            secondary_conflicts TEXT NOT NULL DEFAULT '',
            current_priority TEXT NOT NULL DEFAULT '',
            not_doing TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS quick_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_date TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_daily_journals_date
            ON daily_journals(journal_date);
        CREATE INDEX IF NOT EXISTS idx_quick_notes_date
            ON quick_notes(note_date, created_at);

        INSERT OR IGNORE INTO daily_journals (
            journal_date, day_story, learning_notes, life_notes, growth_thoughts,
            review_problem, review_gain, improvement_learning, improvement_life,
            tomorrow_focus, self_message, created_at, updated_at
        )
        SELECT review_date, events, work_problem, life_state, growth_thought,
               problem_to_solve, biggest_gain, learning_improvement, life_improvement,
               tomorrow_main_task, free_text, updated_at, updated_at
        FROM daily_reviews;
        """
    )


def _migration_004_remove_legacy_direction_demo(
    connection: sqlite3.Connection,
) -> None:
    """只清空完全匹配旧版内置示例的方向，不触碰用户改写过的内容。"""
    connection.execute(
        """
        UPDATE directions
        SET long_term_vision = '', primary_conflict = '',
            secondary_conflicts = '', current_priority = '', not_doing = '',
            updated_at = ?
        WHERE id = 1
          AND long_term_vision = ?
          AND primary_conflict = ?
          AND secondary_conflicts = ?
          AND current_priority = ?
          AND not_doing = ?
        """,
        (
            datetime.now().isoformat(timespec="seconds"),
            "成为具备企业级 AI 项目交付能力的人；建立健康、稳定、可持续的生活方式。",
            "想做大项目，但工程基础和真实项目经验不足。",
            "Git 不熟；部署经验不足；商业知识不足；作息不稳定。",
            "通过一个可运行项目补齐企业级项目实战能力。",
            "暂时不同时学习过多新框架，不开启第二个大项目。",
        ),
    )


MIGRATIONS = (
    Migration(
        1,
        "baseline_v1_schema",
        _migration_checksum("001:baseline_v1_schema"),
        _migration_001_baseline,
    ),
    Migration(
        2,
        "task_recurrence_and_capacity",
        _migration_checksum("002:add-task-recurrence-capacity-columns-and-unique-index"),
        _migration_002_task_recurrence,
    ),
    Migration(
        3,
        "study_diary_daily_pages",
        _migration_checksum("003:add-daily-journals-goal-snapshots-quick-notes"),
        _migration_003_study_diary,
    ),
    Migration(
        4,
        "remove_legacy_direction_demo",
        _migration_checksum("004:clear-only-exact-legacy-direction-demo"),
        _migration_004_remove_legacy_direction_demo,
    ),
)
CURRENT_SCHEMA_VERSION = MIGRATIONS[-1].version


def _read_migration_rows(db_path: Path | str) -> list[tuple[int, str, str]]:
    path = Path(db_path).resolve()
    if not path.exists() or path.stat().st_size == 0:
        return []
    try:
        with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) as connection:
            table_exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'"
            ).fetchone()
            if not table_exists:
                return []
            return [
                (int(row[0]), str(row[1]), str(row[2]))
                for row in connection.execute(
                    "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
                ).fetchall()
            ]
    except sqlite3.Error as error:
        raise DatabaseMigrationError(f"无法读取数据库版本：{path}") from error


def get_schema_version(db_path: Path | str = DB_PATH) -> int:
    rows = _read_migration_rows(db_path)
    return max((row[0] for row in rows), default=0)


def pending_migration_versions(db_path: Path | str = DB_PATH) -> list[int]:
    applied = {row[0] for row in _read_migration_rows(db_path)}
    return [migration.version for migration in MIGRATIONS if migration.version not in applied]


def _apply_migrations(connection: sqlite3.Connection) -> None:
    rows = {
        int(row["version"]): (str(row["name"]), str(row["checksum"]))
        for row in connection.execute(
            "SELECT version, name, checksum FROM schema_migrations"
        ).fetchall()
    }
    if rows and max(rows) > CURRENT_SCHEMA_VERSION:
        raise DatabaseMigrationError(
            "数据库版本高于当前程序支持版本，请使用更新的程序打开。"
        )

    for migration in MIGRATIONS:
        recorded = rows.get(migration.version)
        if recorded:
            if recorded != (migration.name, migration.checksum):
                raise DatabaseMigrationError(
                    f"迁移记录 {migration.version} 与程序定义不一致，已停止启动。"
                )
            continue
        migration.apply(connection)
        connection.execute(
            """
            INSERT INTO schema_migrations (version, name, checksum, applied_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                migration.version,
                migration.name,
                migration.checksum,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )


def _seed_defaults(connection: sqlite3.Connection) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    settings = {
        "reminders_enabled": "1",
        "reminder_lead_minutes": "10",
        "sleep_reminder_enabled": "1",
        "sleep_time": "23:00",
        "sleep_prepare_minutes": "30",
        "review_time": "21:15",
    }
    connection.executemany(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", settings.items()
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO directions (
            id, long_term_vision, primary_conflict, secondary_conflicts,
            current_priority, not_doing, updated_at
        ) VALUES (1, ?, ?, ?, ?, ?, ?)
        """,
        ("", "", "", "", "", now),
    )
    _seed_habits(connection, now)
    _seed_books(connection)


def _seed_goals(connection: sqlite3.Connection, now: str) -> None:
    if connection.execute("SELECT id FROM goals LIMIT 1").fetchone():
        return
    cursor = connection.execute(
        """
        INSERT INTO goals (level, name, why, progress, success_criteria, status, is_current, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "stage",
            "掌握完整 AI 项目开发流程",
            "形成从需求、编码、测试到部署的闭环能力。",
            15,
            "独立完成并部署一个可演示、可维护的 AI 应用。",
            "进行中",
            1,
            now,
        ),
    )
    stage_id = cursor.lastrowid
    connection.execute(
        """
        INSERT INTO goals (parent_id, level, name, why, progress, success_criteria, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (stage_id, "weekly", "完成数据库、Git、Docker 与部署练习", "补齐交付链路", 0, "完成四项可验收练习", "进行中", now),
    )


def _seed_habits(connection: sqlite3.Connection, now: str) -> None:
    habits = [
        ("睡眠 8 小时", "生活", 480, now),
        ("阅读", "阅读", 30, now),
        ("锻炼", "锻炼", 30, now),
        ("技术学习", "AI技术", 60, now),
        ("项目实战", "项目实战", 60, now),
        ("今日复盘", "成长思考", 0, now),
    ]
    connection.executemany(
        "INSERT OR IGNORE INTO habits (name, category, target_minutes, created_at) VALUES (?, ?, ?, ?)",
        habits,
    )


def _seed_recurring_tasks(connection: sqlite3.Connection, now: str) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO recurring_task_templates (
            title, description, category, priority, start_time, end_time,
            time_slot, estimated_minutes, acceptance_criteria, notes,
            must_today, counts_toward_capacity, active, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, 1, ?)
        """,
        (
            "保持 8 小时睡眠",
            "每天保证充足睡眠，优先保护第二天的精力和判断力。",
            "生活",
            "重要",
            "23:00",
            None,
            "晚上",
            480,
            "实际睡眠达到 8 小时，并在第二天记录结果。",
            "这是每日任务，同时也可以在习惯模块记录连续完成天数。",
            now,
        ),
    )


def _seed_books(connection: sqlite3.Connection) -> None:
    books = [
        ("原子习惯", "核心书单", "第一阶段：习惯与执行", "习惯与执行", 1, "建立长期执行系统", 4),
        ("深度工作", "核心书单", "第一阶段：习惯与执行", "习惯与执行", 2, "提高专注与学习效率", 4),
        ("优秀到不能被忽视", "核心书单", "第二阶段：职业成长与表达", "职业成长", 3, "理解职业资本与长期竞争力", 5),
        ("金字塔原理", "核心书单", "第二阶段：职业成长与表达", "表达", 4, "训练表达、逻辑和结构化思考", 6),
        ("穷查理宝典", "核心书单", "第三阶段：思维与决策", "思维与决策", 5, "建立多元思维模型", 8),
        ("思考，快与慢", "核心书单", "第三阶段：思维与决策", "思维与决策", 6, "理解认知偏差与决策错误", 8),
        ("影响力", "核心书单", "第三阶段：思维与决策", "心理与沟通", 7, "理解说服、心理和决策机制", 5),
        ("精益创业", "核心书单", "第四阶段：创业与商业", "商业", 8, "学习产品验证和低成本试错", 4),
        ("从0到1", "核心书单", "第四阶段：创业与商业", "商业", 9, "理解创业、差异化和创新", 4),
        ("创新者的窘境", "核心书单", "第四阶段：创业与商业", "商业", 10, "理解商业竞争与技术变革", 6),
        ("金钱心理学", "核心书单", "第五阶段：财富与资本", "金融", 11, "建立财富观、风险观和长期主义", 4),
        ("巴菲特致股东的信", "核心书单", "第五阶段：财富与资本", "金融", 12, "理解资本配置、企业价值和长期投资", 8),
        ("鞋狗", "扩展书单", "扩展阅读", "商业", 13, "理解公司从0到1成长过程", 5),
        ("商业模式新生代", "扩展书单", "扩展阅读", "商业", 14, "理解商业模式、客户、收入和成本", 5),
        ("一本书读懂财报", "扩展书单", "扩展阅读", "金融", 15, "建立财务报表基础", 5),
        ("滚雪球", "扩展书单", "扩展阅读", "金融", 16, "理解长期成长、信用和资本积累", 10),
        ("史蒂夫·乔布斯传", "扩展书单", "扩展阅读", "产品与领导力", 17, "理解产品、组织、决策和领导力", 10),
    ]
    connection.executemany(
        """
        INSERT OR IGNORE INTO books (
            title, list_type, stage, category, sequence, purpose, estimated_weeks
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        books,
    )


def _seed_demo_tasks(connection: sqlite3.Connection, now: str) -> None:
    today = date.today().isoformat()
    goal_row = connection.execute(
        "SELECT id FROM goals WHERE is_current = 1 ORDER BY id LIMIT 1"
    ).fetchone()
    goal_id = goal_row["id"] if goal_row else None
    tasks = [
        ("Personal Growth OS 核心功能", "项目实战", "主任务", "09:00", "10:30", "上午", 90, "完成一个可运行功能并通过测试", goal_id),
        ("AI 项目开发练习", "AI技术", "重要", "10:45", "11:45", "上午", 60, "提交可运行代码并记录一个关键收获", goal_id),
        ("项目实战 / Debug", "Debug", "重要", "14:00", "16:00", "下午", 120, "定位根因并验证修复，不只绕过报错", goal_id),
        ("Git / Docker / 部署", "部署", "普通", "16:15", "17:00", "下午", 45, "完成一次可复现的部署练习", goal_id),
        ("锻炼", "锻炼", "普通", "17:30", "18:30", "下午", 60, "连续运动至少 30 分钟", None),
        ("阅读", "阅读", "普通", "20:00", "20:40", "晚上", 40, "记录至少一个能应用的观点", None),
        ("商业 / 金融学习", "商业", "普通", "20:45", "21:15", "晚上", 30, "用三句话总结一个概念", None),
        ("今日复盘", "成长思考", "普通", "21:15", "21:30", "晚上", 15, "完成每日复盘九个问题中的关键项", None),
    ]
    connection.executemany(
        """
        INSERT INTO tasks (
            title, category, priority, planned_date, start_time, end_time,
            time_slot, estimated_minutes, acceptance_criteria, source,
            goal_id, must_today, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'system', ?, 1, ?)
        """,
        [(*task[:3], today, *task[3:], now) for task in tasks],
    )


def fetch_all(
    sql: str,
    params: Sequence[Any] = (),
    db_path: Path | str = DB_PATH,
) -> list[dict[str, Any]]:
    with get_connection(db_path) as connection:
        rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]


def fetch_one(
    sql: str,
    params: Sequence[Any] = (),
    db_path: Path | str = DB_PATH,
) -> dict[str, Any] | None:
    with get_connection(db_path) as connection:
        row = connection.execute(sql, params).fetchone()
        return dict(row) if row else None


def execute(
    sql: str,
    params: Sequence[Any] = (),
    db_path: Path | str = DB_PATH,
) -> int:
    with get_connection(db_path) as connection:
        cursor = connection.execute(sql, params)
        return int(cursor.lastrowid or cursor.rowcount)


def execute_many(
    sql: str,
    params: Sequence[Sequence[Any]],
    db_path: Path | str = DB_PATH,
) -> None:
    with get_connection(db_path) as connection:
        connection.executemany(sql, params)


def get_setting(key: str, default: str = "", db_path: Path | str = DB_PATH) -> str:
    row = fetch_one(
        "SELECT value FROM settings WHERE key = ? LIMIT 1", (key,), db_path
    )
    return str(row["value"]) if row else default


def save_setting(key: str, value: str, db_path: Path | str = DB_PATH) -> None:
    execute(
        """
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
        db_path,
    )


def tomorrow_iso() -> str:
    return (date.today() + timedelta(days=1)).isoformat()
