"""仅在应用运行时生效的应用内提醒。"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from database import DB_PATH, get_setting
from services.tasks import list_tasks


def _combine_today(time_text: str) -> datetime:
    hour, minute = [int(value) for value in time_text.split(":")]
    return datetime.combine(date.today(), datetime.min.time()).replace(hour=hour, minute=minute)


def collect_reminders(
    now: datetime | None = None,
    db_path: Path | str = DB_PATH,
) -> list[dict[str, str]]:
    current = now or datetime.now()
    reminders: list[dict[str, str]] = []
    if get_setting("reminders_enabled", "1", db_path) == "1":
        lead = int(get_setting("reminder_lead_minutes", "10", db_path))
        tasks = list_tasks(current.date().isoformat(), db_path=db_path)
        for task in tasks:
            if task["status"] in {"已完成", "已放弃"}:
                continue
            if task["start_time"]:
                start = _combine_today(task["start_time"])
                minutes_until = (start - current).total_seconds() / 60
                if 0 <= minutes_until <= lead:
                    reminders.append({"level": "info", "message": f"{task['title']} 将在 {round(minutes_until)} 分钟后开始。"})
            if task["end_time"] and current > _combine_today(task["end_time"]):
                reminders.append({"level": "warning", "message": f"{task['title']} 已超过计划结束时间，仍未完成。"})

    review_time = _combine_today(get_setting("review_time", "21:15", db_path))
    if current >= review_time:
        reminders.append({"level": "info", "message": "别忘了完成今日复盘，把经验转成明天的调整。"})

    if get_setting("sleep_reminder_enabled", "1", db_path) == "1":
        sleep = _combine_today(get_setting("sleep_time", "23:00", db_path))
        prepare = int(get_setting("sleep_prepare_minutes", "30", db_path))
        wash = sleep - timedelta(minutes=10)
        prepare_time = sleep - timedelta(minutes=prepare)
        if current >= sleep:
            reminders.append({"level": "error", "message": "今天到这里，去睡觉。未完成任务明天重新安排。"})
        elif current >= wash:
            reminders.append({"level": "warning", "message": "请停止高强度学习和工作，准备洗漱。"})
        elif current >= prepare_time:
            reminders.append({"level": "info", "message": "距离睡觉时间不远了，请开始结束当天任务。"})
    return reminders


def is_night_closing(now: datetime | None = None, db_path: Path | str = DB_PATH) -> bool:
    if get_setting("sleep_reminder_enabled", "1", db_path) != "1":
        return False
    current = now or datetime.now()
    return current >= _combine_today(get_setting("sleep_time", "23:00", db_path))
