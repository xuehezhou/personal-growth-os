"""任务 CRUD 页面。"""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from database import fetch_all
from models import CATEGORIES, PRIORITIES, TASK_STATUSES, TIME_SLOTS
from pages.common import page_header, task_card
from services.planner import assess_capacity
from services.tasks import (
    abandon_task,
    complete_task,
    create_daily_task,
    create_task,
    delete_task,
    get_task,
    list_tasks,
    list_recurring_tasks,
    postpone_task,
    stop_recurring_task,
    update_task,
)


def _goal_options() -> tuple[list[int | None], dict[int | None, str]]:
    goals = fetch_all(
        "SELECT id, name FROM goals WHERE status = '进行中' ORDER BY is_current DESC, id LIMIT 100"
    )
    ids: list[int | None] = [None] + [goal["id"] for goal in goals]
    labels = {None: "不属于当前目标", **{goal["id"]: goal["name"] for goal in goals}}
    return ids, labels


def _create_form() -> None:
    with st.expander("＋ 创建任务", expanded=False):
        goal_ids, goal_labels = _goal_options()
        with st.form("create_task_form", clear_on_submit=True):
            title = st.text_input("任务名称 *")
            description = st.text_area("描述")
            col1, col2, col3 = st.columns(3)
            category = col1.selectbox("类型", CATEGORIES)
            priority = col2.selectbox("优先级", PRIORITIES, index=2)
            planned_date = col3.date_input("日期", date.today())
            col4, col5, col6 = st.columns(3)
            start_time = col4.time_input("开始时间", value=None)
            end_time = col5.time_input("结束时间", value=None)
            time_slot = col6.selectbox("时间段", TIME_SLOTS)
            col7, col8 = st.columns(2)
            estimated = col7.number_input("预计时长（分钟）", min_value=0, value=30, step=5)
            goal_id = col8.selectbox("所属目标", goal_ids, format_func=goal_labels.get)
            criteria = st.text_area("验收标准", placeholder="达到什么结果才算完成？")
            notes = st.text_area("备注")
            must_today = st.checkbox("必须在所选日期完成")
            repeat_daily = st.checkbox("每天重复（从今天开始）")
            exclude_capacity = st.checkbox("不计入白天计划容量（适合睡眠等任务）")
            submitted = st.form_submit_button("创建任务", type="primary")
        if submitted:
            try:
                task_data = {
                    "title": title,
                    "description": description,
                    "category": category,
                    "priority": priority,
                    "planned_date": planned_date.isoformat(),
                    "start_time": start_time.strftime("%H:%M") if start_time else None,
                    "end_time": end_time.strftime("%H:%M") if end_time else None,
                    "time_slot": time_slot,
                    "estimated_minutes": estimated,
                    "acceptance_criteria": criteria,
                    "notes": notes,
                    "goal_id": goal_id,
                    "must_today": must_today,
                    "source": "user",
                    "counts_toward_capacity": not exclude_capacity,
                }
                if repeat_daily:
                    create_daily_task(task_data)
                    st.success("每日任务已创建，从今天开始自动生成。")
                else:
                    create_task(task_data)
                    st.success("任务已创建。")
                st.rerun()
            except ValueError as error:
                st.error(str(error))


def _edit_form(task_id: int) -> None:
    task = get_task(task_id)
    if not task:
        return
    goal_ids, goal_labels = _goal_options()
    if task["goal_id"] not in goal_ids:
        goal_ids.append(task["goal_id"])
        goal_labels[task["goal_id"]] = "已归档目标"
    with st.form(f"edit_task_{task_id}"):
        title = st.text_input("任务名称", value=task["title"])
        description = st.text_area("描述", value=task["description"])
        col1, col2, col3 = st.columns(3)
        category = col1.selectbox("类型", CATEGORIES, index=CATEGORIES.index(task["category"]))
        priority = col2.selectbox("优先级", PRIORITIES, index=PRIORITIES.index(task["priority"]))
        planned_date = col3.date_input("日期", value=date.fromisoformat(task["planned_date"]))
        col4, col5, col6 = st.columns(3)
        start_time = col4.text_input("开始时间（HH:MM）", value=task["start_time"] or "")
        end_time = col5.text_input("结束时间（HH:MM）", value=task["end_time"] or "")
        time_slot = col6.selectbox("时间段", TIME_SLOTS, index=TIME_SLOTS.index(task["time_slot"]))
        col7, col8, col9 = st.columns(3)
        estimated = col7.number_input("预计分钟", min_value=0, value=int(task["estimated_minutes"]))
        actual = col8.number_input("实际分钟", min_value=0, value=int(task["actual_minutes"]))
        status = col9.selectbox("状态", TASK_STATUSES, index=TASK_STATUSES.index(task["status"]))
        completion = st.slider("完成百分比", 0, 100, int(task["completion_percentage"]))
        goal_id = st.selectbox(
            "所属目标", goal_ids, index=goal_ids.index(task["goal_id"]), format_func=goal_labels.get
        )
        criteria = st.text_area("验收标准", value=task["acceptance_criteria"])
        notes = st.text_area("备注", value=task["notes"])
        must_today = st.checkbox("必须在所选日期完成", value=bool(task["must_today"]))
        counts_capacity = st.checkbox(
            "计入白天计划容量", value=bool(task["counts_toward_capacity"])
        )
        saved = st.form_submit_button("保存修改", type="primary")
    if saved:
        try:
            update_task(
                task_id,
                {
                    "title": title,
                    "description": description,
                    "category": category,
                    "priority": priority,
                    "planned_date": planned_date.isoformat(),
                    "start_time": start_time.strip() or None,
                    "end_time": end_time.strip() or None,
                    "time_slot": time_slot,
                    "estimated_minutes": estimated,
                    "actual_minutes": actual,
                    "status": status,
                    "completion_percentage": completion,
                    "goal_id": goal_id,
                    "acceptance_criteria": criteria,
                    "notes": notes,
                    "must_today": must_today,
                    "counts_toward_capacity": counts_capacity,
                },
            )
            st.success("任务已更新。")
            st.rerun()
        except ValueError as error:
            st.error(str(error))


def render() -> None:
    page_header("任务", "创建、验收、延期和调整。不要让任务无声地消失。")
    _create_form()

    recurring = list_recurring_tasks()
    with st.expander(f"每天重复的任务 · {len(recurring)}"):
        if not recurring:
            st.caption("暂无每日任务。创建任务时勾选“每天重复”即可。")
        for template in recurring:
            col_name, col_action = st.columns([5, 1])
            capacity_text = "计入容量" if template["counts_toward_capacity"] else "不计入容量"
            col_name.markdown(
                f"**{template['title']}**  \\n+{template['start_time'] or '未设时间'} · {template['estimated_minutes']} 分钟 · {capacity_text}"
            )
            if col_action.button("停止重复", key=f"stop_recurring_{template['id']}"):
                stop_recurring_task(template["id"])
                st.success("已停止未来生成，历史记录仍然保留。")
                st.rerun()

    col1, col2 = st.columns([1, 2])
    selected_date = col1.date_input("查看日期", date.today(), key="task_filter_date")
    status_filter = col2.selectbox("状态筛选", ["全部"] + TASK_STATUSES)
    tasks = list_tasks(
        selected_date.isoformat(), None if status_filter == "全部" else status_filter
    )
    capacity = assess_capacity(tasks)
    if capacity["overloaded"]:
        st.warning(f"当天计划共 {capacity['total_minutes']} 分钟，已经超过建议可执行范围。")

    if not tasks:
        st.info("这个日期暂无任务。")
        return
    selected_id = st.selectbox(
        "选择任务进行编辑",
        [task["id"] for task in tasks],
        format_func=lambda task_id: next(task["title"] for task in tasks if task["id"] == task_id),
    )
    for task in tasks:
        task_card(task)
        cols = st.columns([1, 1, 1, 1, 3])
        if task["status"] not in {"已完成", "已放弃"}:
            if cols[0].button("现在完成", key=f"finish_{task['id']}"):
                complete_task(task["id"])
                st.rerun()
            if cols[1].button("晚些时候", key=f"later_{task['id']}"):
                update_task(task["id"], {"start_time": None, "end_time": None, "time_slot": "晚上"})
                st.rerun()
            if cols[2].button("移到明天", key=f"tomorrow_{task['id']}"):
                count = postpone_task(task["id"], (date.today() + timedelta(days=1)).isoformat())
                if count >= 3:
                    st.warning("该任务已连续延期 3 次：请拆分、降级或放弃。")
                st.rerun()
            if cols[3].button("放弃", key=f"abandon_{task['id']}"):
                abandon_task(task["id"])
                st.rerun()

    st.divider()
    st.subheader("修改任务")
    _edit_form(selected_id)
    with st.expander("删除任务（不可撤销）"):
        confirm = st.checkbox("我确认删除当前选中的任务", key=f"confirm_delete_{selected_id}")
        if st.button("删除", disabled=not confirm, key=f"delete_{selected_id}"):
            delete_task(selected_id)
            st.rerun()
