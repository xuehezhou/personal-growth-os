"""页面共享的小型展示组件。"""

from __future__ import annotations

from typing import Any

import streamlit as st


def page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def task_card(task: dict[str, Any]) -> None:
    done_class = " done" if task["status"] == "已完成" else ""
    if task.get("recurring_template_id"):
        source = "每日任务"
    else:
        source = "系统计划" if task["source"] == "system" else "自主安排"
    time_range = "未设时间"
    if task.get("start_time"):
        time_range = task["start_time"]
        if task.get("end_time"):
            time_range += f"–{task['end_time']}"
    criteria = task.get("acceptance_criteria") or "尚未设置验收标准"
    st.markdown(
        f"""
        <div class="task-card{done_class}">
          <strong>{task['title']}</strong>
          <div class="task-meta">{time_range} · {task['category']} · {task['priority']} · {source}</div>
          <div class="task-meta">验收：{criteria}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def minutes_text(minutes: int | float) -> str:
    total = int(minutes)
    hours, remainder = divmod(total, 60)
    if hours and remainder:
        return f"{hours}小时{remainder}分钟"
    if hours:
        return f"{hours}小时"
    return f"{remainder}分钟"
