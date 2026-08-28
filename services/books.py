"""阅读进度与阅读日志。"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

from database import DB_PATH, execute, fetch_all, fetch_one, get_connection


def add_reading_log(
    book_id: int,
    minutes: int,
    pages_read: int,
    learned: str,
    changed_view: str,
    real_world_link: str,
    application: str,
    db_path: Path | str = DB_PATH,
    log_date: date | str | None = None,
) -> None:
    if minutes <= 0:
        raise ValueError("阅读时长必须大于 0")
    book = fetch_one(
        "SELECT id, current_page, total_pages FROM books WHERE id = ? LIMIT 1",
        (book_id,),
        db_path,
    )
    if not book:
        raise ValueError("书籍不存在")
    new_page = int(book["current_page"]) + max(0, pages_read)
    if int(book["total_pages"]) > 0:
        new_page = min(new_page, int(book["total_pages"]))
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO reading_logs (
                book_id, log_date, minutes, pages_read, learned, changed_view,
                real_world_link, application, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                book_id,
                log_date.isoformat() if isinstance(log_date, date) else (log_date or date.today().isoformat()),
                minutes,
                max(0, pages_read),
                learned.strip(),
                changed_view.strip(),
                real_world_link.strip(),
                application.strip(),
                now,
            ),
        )
        connection.execute(
            """
            UPDATE books
            SET current_page = ?, total_minutes = total_minutes + ?
            WHERE id = ?
            """,
            (new_page, minutes, book_id),
        )


def list_books(db_path: Path | str = DB_PATH) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT id, title, list_type, stage, category, sequence, purpose,
               estimated_weeks, total_pages, current_page, start_date,
               target_date, status, total_minutes, notes, is_light_reading
        FROM books
        ORDER BY CASE status WHEN '当前阅读' THEN 1 WHEN '待读' THEN 2 ELSE 3 END,
                 sequence, id
        LIMIT 300
        """,
        (), db_path,
    )


def add_book(
    title: str,
    total_pages: int = 0,
    category: str = "自定义",
    db_path: Path | str = DB_PATH,
) -> int:
    clean = title.strip()
    if not clean:
        raise ValueError("书名不能为空")
    next_sequence = fetch_one(
        "SELECT COALESCE(MAX(sequence), 0) + 1 AS value FROM books",
        (), db_path,
    )["value"]
    try:
        return execute(
            """
            INSERT INTO books (
                title, list_type, stage, category, sequence, purpose,
                total_pages, status
            ) VALUES (?, '扩展书单', '我的书单', ?, ?, '', ?, '待读')
            """,
            (clean, category.strip() or "自定义", next_sequence, max(0, int(total_pages))),
            db_path,
        )
    except sqlite3.IntegrityError as error:
        raise ValueError("书单中已经有这本书") from error


def update_book(
    book_id: int,
    values: dict[str, Any],
    db_path: Path | str = DB_PATH,
) -> None:
    book = fetch_one("SELECT * FROM books WHERE id = ? LIMIT 1", (book_id,), db_path)
    if not book:
        raise ValueError("书籍不存在")
    merged = {**book, **values}
    total_pages = max(0, int(merged.get("total_pages", 0) or 0))
    current_page = max(0, int(merged.get("current_page", 0) or 0))
    if total_pages:
        current_page = min(current_page, total_pages)
    try:
        execute(
            """
            UPDATE books
            SET title = ?, total_pages = ?, current_page = ?, status = ?,
                notes = ?, is_light_reading = ?
            WHERE id = ?
            """,
            (
                str(merged["title"]).strip(), total_pages, current_page,
                merged["status"], str(merged.get("notes", "")).strip(),
                int(bool(merged.get("is_light_reading", 0))), book_id,
            ),
            db_path,
        )
    except sqlite3.IntegrityError as error:
        raise ValueError("书单中已经有这本书") from error


def delete_book(
    book_id: int,
    confirmed: bool,
    db_path: Path | str = DB_PATH,
) -> None:
    if not confirmed:
        raise ValueError("删除书籍前必须确认；相关阅读记录也会删除")
    execute("DELETE FROM books WHERE id = ?", (book_id,), db_path)


def reading_minutes_for_day(
    log_date: date | str,
    book_id: int | None = None,
    db_path: Path | str = DB_PATH,
) -> int:
    day = log_date.isoformat() if isinstance(log_date, date) else str(log_date)
    if book_id is None:
        row = fetch_one(
            "SELECT COALESCE(SUM(minutes), 0) AS value FROM reading_logs WHERE log_date = ?",
            (day,), db_path,
        )
    else:
        row = fetch_one(
            """
            SELECT COALESCE(SUM(minutes), 0) AS value
            FROM reading_logs WHERE log_date = ? AND book_id = ?
            """,
            (day, book_id), db_path,
        )
    return int(row["value"])
