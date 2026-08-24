"""今日首页。"""

from __future__ import annotations

from datetime import date, datetime

import streamlit as st

from database import fetch_all
from models import CATEGORIES, PRIORITIES, TIME_SLOTS
from pages.common import minutes_text, page_header, task_card
from services.habits import calculate_streak, list_habits, save_habit_log
from services.planner import assess_capacity, build_today_advice, find_main_task
from services.reminder import collect_reminders, is_night_closing
from services.stats import category_minutes, task_summary
from services.tasks import (
    complete_task,
    create_daily_task,
    create_task,
    list_tasks,
    postpone_task,
)


def _quick_task_form() -> None:
    with st.expander("＋ 安排一个今天的任务", expanded=False):
        with st.form("today_quick_task", clear_on_submit=True):
            title = st.text_input("任务名称 *", placeholder="例如：今天去理发")
            col1, col2, col3 = st.columns(3)
            category = col1.selectbox("类型", CATEGORIES, index=CATEGORIES.index("个人事务"))
            priority = col2.selectbox("优先级", PRIORITIES, index=2)
            time_slot = col3.selectbox("时间段", TIME_SLOTS, index=3)
            col4, col5, col6 = st.columns(3)
            start_time = col4.time_input("开始时间", value=None)
            end_time = col5.time_input("结束时间", value=None)
            estimated = col6.number_input("预计分钟", min_value=0, value=30, step=5)
            criteria = st.text_area("验收标准", placeholder="做到什么才算真正完成？")
            notes = st.text_area("备注")
            must_today = st.checkbox("必须今天完成")
            repeat_daily = st.checkbox("每天重复（从今天开始）")
            exclude_capacity = st.checkbox("不计入白天计划容量（适合睡眠等任务）")
            submitted = st.form_submit_button("加入今日计划", type="primary")
        if submitted:
            try:
                task_data = {
                    "title": title,
                    "category": category,
                    "priority": priority,
                    "planned_date": date.today().isoformat(),
                    "start_time": start_time.strftime("%H:%M") if start_time else None,
                    "end_time": end_time.strftime("%H:%M") if end_time else None,
                    "time_slot": time_slot,
                    "estimated_minutes": estimated,
                    "acceptance_criteria": criteria,
                    "notes": notes,
                    "must_today": must_today,
                    "source": "user",
                    "counts_toward_capacity": not exclude_capacity,
                }
                if repeat_daily:
                    create_daily_task(task_data)
                    st.success("已创建每日任务，并加入今天的计划。")
                else:
                    create_task(task_data)
                    st.success("已加入今日全部任务。")
                st.rerun()
            except ValueError as error:
                st.error(str(error))


def _task_actions(task: dict, context: str) -> None:
    col1, col2, col3 = st.columns([1, 1, 4])
    if task["status"] != "已完成" and col1.button(
        "完成", key=f"today_done_{context}_{task['id']}"
    ):
        complete_task(task["id"])
        st.rerun()
    if task["status"] not in {"已完成", "已放弃"} and col2.button(
        "移到明天", key=f"today_move_{context}_{task['id']}"
    ):
        count = postpone_task(task["id"])
        if count >= 3:
            st.warning("该任务已经连续延期 3 次，请检查是否过大、不重要或需要拆分。")
        else:
            st.toast("已移到明天")
        st.rerun()


def _habit_strip(today_text: str) -> None:
    st.subheader("每日习惯")
    habit_items = list_habits(today_text)
    columns = st.columns(len(habit_items))
    for column, habit in zip(columns, habit_items):
        streak = calculate_streak(habit["id"])
        with column:
            checked = st.checkbox(
                habit["name"], value=bool(habit["completed"]), key=f"home_habit_{habit['id']}"
            )
            st.caption(f"🔥 {streak} 天 · 目标 {habit['target_minutes']} 分钟")
            if checked != bool(habit["completed"]):
                save_habit_log(
                    habit["id"], today_text, checked,
                    habit["target_minutes"] if checked else 0,
                )
                st.rerun()


def render() -> None:
    now = datetime.now()
    today_text = date.today().isoformat()
    page_header("TODAY", f"{date.today():%Y年%m月%d日} · 今天最重要的事情，只有一件。")

    for reminder in collect_reminders(now):
        getattr(st, reminder["level"])(reminder["message"])
    if is_night_closing(now):
        st.error("夜间收尾状态：不再推荐新的高强度任务。优先睡眠，未完成任务请明天重新安排。")

    tasks = list_tasks(today_text)
    summary = task_summary(1)
    main_task = find_main_task(tasks)
    if main_task:
        st.markdown(
            f'<div class="priority-box"><span class="eyebrow">今天最重要的一件事</span><br>'
            f'<strong style="font-size:1.35rem">{main_task["title"]}</strong><br>'
            f'<span class="small-muted">验收：{main_task["acceptance_criteria"] or "请补充明确验收标准"}</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("今天还没有任务。先安排一个真正重要的行动。")

    metrics = st.columns(5)
    metrics[0].metric("今日完成", f"{summary['completed']} / {summary['total']}")
    metrics[1].metric("完成率", f"{summary['completion_rate']}%")
    metrics[2].metric("计划投入", minutes_text(summary["planned_minutes"]))
    metrics[3].metric("实际投入", minutes_text(summary["actual_minutes"]))
    metrics[4].metric("项目实战", minutes_text(category_minutes("项目实战")))

    capacity = assess_capacity(tasks)
    if capacity["overloaded"]:
        names = "、".join(item["title"] for item in capacity["move_candidates"])
        st.warning(
            f"今日任务量已经超过建议可执行范围（共 {minutes_text(capacity['total_minutes'])}）。"
            f"建议重新排序或移动：{names}。"
        )

    _quick_task_form()

    system_tasks = [task for task in tasks if task["source"] == "system"]
    user_tasks = [task for task in tasks if task["source"] == "user"]
    source_tabs = st.tabs([
        f"今日全部任务 · {len(tasks)}", f"系统计划 · {len(system_tasks)}", f"我自己安排 · {len(user_tasks)}"
    ])
    groups = [tasks, system_tasks, user_tasks]
    for tab_index, (tab, group) in enumerate(zip(source_tabs, groups)):
        with tab:
            if not group:
                st.caption("暂无任务")
            for slot in ["上午", "下午", "晚上", "全天"]:
                slot_tasks = [task for task in group if task["time_slot"] == slot]
                if not slot_tasks:
                    continue
                st.markdown(f"### {slot}")
                for task in slot_tasks:
                    task_card(task)
                    _task_actions(task, str(tab_index))

    st.subheader("今日建议 · 为什么这样安排")
    advice = build_today_advice()
    if advice:
        for item in advice:
            st.markdown(f"**{item['slot']}｜{item['task']}**  \\n+{item['reason']}")
    else:
        st.caption("当前没有待执行的今日任务。")

    _habit_strip(today_text)

    overdue = fetch_all(
        """
        SELECT id, title, start_time, end_time, postponement_count
        FROM tasks
        WHERE planned_date = ? AND status NOT IN ('已完成', '已放弃')
          AND end_time IS NOT NULL AND end_time < ?
        ORDER BY end_time
        LIMIT 100
        """,
        (today_text, now.strftime("%H:%M")),
    )
    if overdue:
        st.warning(f"今日有 {len(overdue)} 个计划任务已超时未完成，请在任务页处理。")
