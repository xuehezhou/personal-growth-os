"""不依赖大模型的可解释规则计划器。"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from database import DB_PATH, fetch_one
from models import PlanCapacity
from services.tasks import list_tasks


HIGH_INTENSITY_CATEGORIES = {
    "AI技术", "项目实战", "Debug", "部署", "数据库", "RAG", "Agent"
}
LEARNING_PROJECT_CATEGORIES = HIGH_INTENSITY_CATEGORIES | {
    "Git/GitHub", "商业", "金融", "阅读", "表达", "英语"
}


def assess_capacity(
    tasks: list[dict[str, Any]], capacity: PlanCapacity = PlanCapacity()
) -> dict[str, Any]:
    active = [
        task
        for task in tasks
        if task["status"] not in {"已完成", "已放弃"}
        and bool(task.get("counts_toward_capacity", 1))
    ]
    deep = sum(
        int(task["estimated_minutes"])
        for task in active
        if task["category"] in HIGH_INTENSITY_CATEGORIES
    )
    learning = sum(
        int(task["estimated_minutes"])
        for task in active
        if task["category"] in LEARNING_PROJECT_CATEGORIES
    )
    total = sum(int(task["estimated_minutes"]) for task in active)
    overloaded = (
        deep > capacity.deep_work_minutes
        or learning > capacity.learning_project_minutes
        or total > capacity.total_minutes
    )
    candidates = sorted(
        active,
        key=lambda item: (
            item["must_today"],
            {"主任务": 4, "重要": 3, "普通": 2, "低": 1}.get(item["priority"], 0),
        ),
    )
    return {
        "overloaded": overloaded,
        "deep_minutes": deep,
        "learning_minutes": learning,
        "total_minutes": total,
        "move_candidates": candidates[:3],
    }


def build_today_advice(db_path: Path | str = DB_PATH) -> list[dict[str, str]]:
    today = date.today().isoformat()
    tasks = list_tasks(today, db_path=db_path)
    pending = [task for task in tasks if task["status"] not in {"已完成", "已放弃"}]
    current_priority = fetch_one(
        "SELECT current_priority FROM directions WHERE id = 1 LIMIT 1", (), db_path
    )
    priority_text = current_priority["current_priority"] if current_priority else "当前目标"

    advice: list[dict[str, str]] = []
    slots = ["上午", "下午", "晚上"]
    for slot in slots:
        slot_tasks = [task for task in pending if task["time_slot"] == slot]
        if not slot_tasks:
            continue
        task = slot_tasks[0]
        if task["postponement_count"]:
            reason = f"该任务已延期 {task['postponement_count']} 次，需要优先关闭循环。"
        elif task.get("goal_id"):
            reason = f"它属于当前目标，并支持“{priority_text}”。"
        elif slot == "上午":
            reason = "上午认知状态更好，优先处理高强度任务。"
        elif slot == "晚上":
            reason = "晚上保留给阅读、复盘等轻认知任务。"
        else:
            reason = "下午适合实操、调试与整理输出。"
        advice.append({"slot": slot, "task": task["title"], "reason": reason})

    if not any(item["slot"] == "上午" for item in advice):
        advice.append(
            {
                "slot": "上午",
                "task": priority_text,
                "reason": "上午优先推进当前最需要解决的问题，避免目标被零散任务挤掉。",
            }
        )
    if not any(item["slot"] == "晚上" for item in advice):
        current_book = fetch_one(
            "SELECT title FROM books WHERE status = '当前阅读' ORDER BY is_light_reading, sequence LIMIT 1",
            (),
            db_path,
        )
        book_title = current_book["title"] if current_book else "当前阶段核心书单"
        advice.append(
            {
                "slot": "晚上",
                "task": f"阅读《{book_title}》30 分钟",
                "reason": "晚上安排轻认知输入，同时维持阅读习惯。",
            }
        )
    if not any(task["category"] == "锻炼" for task in pending):
        advice.append(
            {
                "slot": "锻炼",
                "task": "锻炼 30–60 分钟",
                "reason": "计划必须给健康留出时间，不能只堆叠学习任务。",
            }
        )
    return advice


def find_main_task(tasks: list[dict[str, Any]]) -> dict[str, Any] | None:
    active = [task for task in tasks if task["status"] not in {"已放弃"}]
    if not active:
        return None
    explicit = [task for task in active if task["priority"] == "主任务"]
    return explicit[0] if explicit else active[0]
