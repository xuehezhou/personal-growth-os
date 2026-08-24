"""阅读进度与阅读日志。"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from database import DB_PATH, execute, fetch_one, get_connection


def add_reading_log(
    book_id: int,
    minutes: int,
    pages_read: int,
    learned: str,
    changed_view: str,
    real_world_link: str,
    application: str,
    db_path: Path | str = DB_PATH,
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
                date.today().isoformat(),
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
            SET current_page = ?, today_minutes = today_minutes + ?,
                total_minutes = total_minutes + ?
            WHERE id = ?
            """,
            (new_page, minutes, minutes, book_id),
        )

