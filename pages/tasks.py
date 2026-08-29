"""按现实日期创建、查看和调整计划。"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import streamlit as st

from database import fetch_all
from models import CATEGORIES, PRIORITIES, TASK_STATUSES, TIME_SLOTS
from pages.common import minutes_text, page_header
from services.planner import assess_capacity
from services.tasks import (
    abandon_task,
    complete_task,
    create_daily_task,
    create_task,
    delete_task,
    get_task,
    list_recurring_tasks,
    list_tasks,
    postpone_task,
    stop_recurring_task,
    update_task,
)


SLOT_ICONS = {"上午": "☀️", "下午": "🌤", "晚上": "🌙", "全天": "·"}
WEEKDAYS = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")


def _goal_options() -> tuple[list[int | None], dict[int | None, str]]:
    goals = fetch_all(
        "SELECT id, name FROM goals WHERE status = '进行中' ORDER BY is_current DESC, id LIMIT 100"
    )
    ids: list[int | None] = [None] + [goal["id"] for goal in goals]
    labels = {None: "不关联目标", **{goal["id"]: goal["name"] for goal in goals}}
    return ids, labels


def _time_value(value: str | None) -> time | None:
    return datetime.strptime(value, "%H:%M").time() if value else None


def _safe_index(options: list[str], value: str, fallback: int = 0) -> int:
    return options.index(value) if value in options else fallback


def _date_label(day: date) -> str:
    difference = (day - date.today()).days
    if difference == -1:
        return "昨天"
    if difference == 0:
        return "今天"
    if difference == 1:
        return "明天"
    if difference < 0:
        return f"{abs(difference)} 天前"
    return f"{difference} 天后"


def _set_planner_date(day: date) -> None:
    st.session_state["planner_date"] = day
    st.session_state.pop("planner_edit_task_id", None)


def _date_navigator() -> date:
    if "planner_date" not in st.session_state:
        st.session_state["planner_date"] = date.today()

    left, today_column, picker, tomorrow_column, right = st.columns([1, 1, 3.2, 1, 1])
    selected = picker.date_input(
        "计划日期",
        key="planner_date",
        format="YYYY-MM-DD",
        label_visibility="collapsed",
    )
    left.button(
        "←",
        help="前一天",
        use_container_width=True,
        on_click=_set_planner_date,
        args=(selected - timedelta(days=1),),
    )
    today_column.button(
        "今天",
        use_container_width=True,
        on_click=_set_planner_date,
        args=(date.today(),),
    )
    tomorrow_column.button(
        "明天",
        use_container_width=True,
        on_click=_set_planner_date,
        args=(date.today() + timedelta(days=1),),
    )
    right.button(
        "→",
        help="后一天",
        use_container_width=True,
        on_click=_set_planner_date,
        args=(selected + timedelta(days=1),),
    )
    st.caption(
        f"{_date_label(selected)} · {selected:%Y年%m月%d日} · {WEEKDAYS[selected.weekday()]}"
    )
    return selected


def _create_form(day: date, expanded: bool) -> None:
    with st.expander(f"＋ 添加{_date_label(day)}的计划", expanded=expanded):
        goal_ids, goal_labels = _goal_options()
        with st.form(f"create_plan_{day.isoformat()}", clear_on_submit=True):
            title = st.text_input("计划内容 *", placeholder="例如：整理项目需求并写出明日执行清单")

            timing, slot_column, duration_column = st.columns([1.15, 1, 1])
            start_time = timing.time_input("开始时间（可选）", value=None)
            time_slot = slot_column.selectbox("时间段", TIME_SLOTS)
            estimated = duration_column.number_input(
                "预计分钟", min_value=0, value=30, step=5
            )

            category_column, priority_column = st.columns(2)
            category = category_column.selectbox(
                "类型", CATEGORIES, index=CATEGORIES.index("个人事务")
            )
            priority = priority_column.selectbox(
                "优先级", PRIORITIES, index=PRIORITIES.index("普通")
            )

            criteria = st.text_input(
                "完成标准",
                value="完成计划内容",
                placeholder="做到什么才算真正完成？",
            )
            notes = st.text_area(
                "备注（可选）",
                placeholder="相关资料、提醒或下一步。",
                height=78,
            )

            with st.expander("更多设置"):
                end_time = st.time_input("结束时间（可选）", value=None)
                goal_id = st.selectbox("关联目标", goal_ids, format_func=goal_labels.get)
                must_today = st.checkbox("必须在所选日期完成")
                exclude_capacity = st.checkbox("不计入当天计划时长（适合睡眠等事项）")
                repeat_daily = st.checkbox(
                    "设为每日计划（从今天开始）",
                    disabled=day != date.today(),
                    help="每日计划只能从今天启用；规划未来某一天时请保存为单次计划。",
                )

            submitted = st.form_submit_button(
                "保存计划", type="primary", use_container_width=True
            )

        if submitted:
            try:
                task_data = {
                    "title": title,
                    "category": category,
                    "priority": priority,
                    "planned_date": day.isoformat(),
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
                    st.success("每日计划已启用，并已加入今天。")
                else:
                    create_task(task_data)
                    st.success(f"已加入 {_date_label(day)} 的计划。")
            except ValueError as error:
                st.error(str(error))


def _summary(tasks: list[dict]) -> None:
    completed = sum(task["status"] == "已完成" for task in tasks)
    pending = sum(task["status"] in {"待开始", "进行中"} for task in tasks)
    planned_minutes = sum(
        int(task["estimated_minutes"])
        for task in tasks
        if task["status"] != "已放弃" and task.get("counts_toward_capacity", 1)
    )
    completion_rate = round(completed / len(tasks) * 100) if tasks else 0
    columns = st.columns(4)
    columns[0].metric("计划", len(tasks))
    columns[1].metric("待处理", pending)
    columns[2].metric("已完成", f"{completion_rate}%")
    columns[3].metric("预计投入", minutes_text(planned_minutes))


def _task_meta(task: dict) -> str:
    timing = task["start_time"] or task["time_slot"]
    if task["end_time"]:
        timing = f"{timing}–{task['end_time']}"
    recurring = " · 每日" if task.get("recurring_template_id") else ""
    return (
        f"{timing} · {task['estimated_minutes']} 分钟 · "
        f"{task['category']} · {task['priority']}{recurring}"
    )


def _select_task_for_edit(task_id: int) -> None:
    st.session_state["planner_edit_task_id"] = task_id


def _task_list(tasks: list[dict]) -> None:
    status_filter = st.selectbox(
        "显示计划",
        ["全部", "待处理", "已完成", "已放弃"],
        label_visibility="collapsed",
    )
    if status_filter == "待处理":
        visible = [task for task in tasks if task["status"] in {"待开始", "进行中"}]
    elif status_filter == "全部":
        visible = tasks
    else:
        visible = [task for task in tasks if task["status"] == status_filter]

    if not visible:
        if tasks:
            st.info("当前筛选下没有计划。")
        else:
            st.info("这一天还没有计划。点击上方的加号开始安排。")
        return

    for slot in TIME_SLOTS:
        slot_tasks = [task for task in visible if task["time_slot"] == slot]
        if not slot_tasks:
            continue
        st.markdown(f"#### {SLOT_ICONS[slot]} {slot}")
        for task in slot_tasks:
            with st.container(border=True):
                content, complete_column, edit_column = st.columns([6, 1.15, 1])
                if task["status"] == "已完成":
                    content.markdown(f"~~**{task['title']}**~~")
                    complete_column.caption("✓ 已完成")
                elif task["status"] == "已放弃":
                    content.markdown(f"~~{task['title']}~~")
                    complete_column.caption("已放弃")
                else:
                    content.markdown(f"**{task['title']}**")
                    if complete_column.button(
                        "完成", key=f"planner_complete_{task['id']}", use_container_width=True
                    ):
                        complete_task(task["id"])
                        st.rerun()
                content.caption(_task_meta(task))
                content.caption(f"完成标准：{task['acceptance_criteria']}")
                edit_column.button(
                    "编辑",
                    key=f"planner_edit_{task['id']}",
                    use_container_width=True,
                    on_click=_select_task_for_edit,
                    args=(task["id"],),
                )


def _edit_panel(task_id: int) -> None:
    task = get_task(task_id)
    if not task:
        st.session_state.pop("planner_edit_task_id", None)
        return

    st.divider()
    st.markdown("### 编辑计划")
    goal_ids, goal_labels = _goal_options()
    if task["goal_id"] not in goal_ids:
        goal_ids.append(task["goal_id"])
        goal_labels[task["goal_id"]] = "已归档目标"

    with st.form(f"planner_edit_form_{task_id}"):
        title = st.text_input("计划内容", value=task["title"])
        date_column, slot_column, status_column = st.columns(3)
        planned_date = date_column.date_input(
            "计划日期", value=date.fromisoformat(task["planned_date"])
        )
        time_slot = slot_column.selectbox(
            "时间段", TIME_SLOTS, index=_safe_index(TIME_SLOTS, task["time_slot"])
        )
        status = status_column.selectbox(
            "状态", TASK_STATUSES, index=_safe_index(TASK_STATUSES, task["status"])
        )

        start_column, end_column, duration_column = st.columns(3)
        start_time = start_column.time_input("开始", value=_time_value(task["start_time"]))
        end_time = end_column.time_input("结束", value=_time_value(task["end_time"]))
        estimated = duration_column.number_input(
            "预计分钟", min_value=0, value=int(task["estimated_minutes"]), step=5
        )

        category_column, priority_column, goal_column = st.columns(3)
        category = category_column.selectbox(
            "类型", CATEGORIES, index=_safe_index(CATEGORIES, task["category"])
        )
        priority = priority_column.selectbox(
            "优先级", PRIORITIES, index=_safe_index(PRIORITIES, task["priority"], 2)
        )
        goal_id = goal_column.selectbox(
            "关联目标",
            goal_ids,
            index=goal_ids.index(task["goal_id"]),
            format_func=goal_labels.get,
        )

        criteria = st.text_input("完成标准", value=task["acceptance_criteria"])
        notes = st.text_area("备注", value=task["notes"], height=82)
        completion = st.slider("完成进度", 0, 100, int(task["completion_percentage"]))
        must_today = st.checkbox("必须在所选日期完成", value=bool(task["must_today"]))
        counts_capacity = st.checkbox(
            "计入当天计划时长", value=bool(task["counts_toward_capacity"])
        )
        saved = st.form_submit_button("保存修改", type="primary")

    if saved:
        try:
            update_task(
                task_id,
                {
                    "title": title,
                    "planned_date": planned_date.isoformat(),
                    "start_time": start_time.strftime("%H:%M") if start_time else None,
                    "end_time": end_time.strftime("%H:%M") if end_time else None,
                    "time_slot": time_slot,
                    "estimated_minutes": estimated,
                    "status": status,
                    "completion_percentage": completion,
                    "category": category,
                    "priority": priority,
                    "goal_id": goal_id,
                    "acceptance_criteria": criteria,
                    "notes": notes,
                    "must_today": must_today,
                    "counts_toward_capacity": counts_capacity,
                },
            )
            _set_planner_date(planned_date)
            st.rerun()
        except ValueError as error:
            st.error(str(error))

    action_columns = st.columns([1.3, 1.3, 4])
    next_day = date.fromisoformat(task["planned_date"]) + timedelta(days=1)
    if task["status"] not in {"已完成", "已放弃"}:
        if action_columns[0].button("顺延一天", key=f"planner_postpone_{task_id}"):
            postponements = postpone_task(task_id, next_day.isoformat())
            _set_planner_date(next_day)
            if postponements >= 3:
                st.warning("这项计划已延期 3 次，建议拆小、降级或放弃。")
            st.rerun()
        if action_columns[1].button("放弃计划", key=f"planner_abandon_{task_id}"):
            abandon_task(task_id)
            st.rerun()

    with st.expander("删除计划"):
        if task.get("recurring_template_id"):
            st.caption("每日计划实例不会物理删除；移除时会标记为已放弃，以保留历史。")
        confirm = st.checkbox("确认删除这项计划", key=f"planner_delete_confirm_{task_id}")
        if st.button(
            "确认删除",
            key=f"planner_delete_{task_id}",
            disabled=not confirm,
        ):
            delete_task(task_id)
            st.session_state.pop("planner_edit_task_id", None)
            st.rerun()


def _recurring_plans() -> None:
    recurring = list_recurring_tasks()
    with st.expander(f"每日计划 · {len(recurring)}"):
        if not recurring:
            st.caption("暂无每日计划。在今天添加计划时，可在“更多设置”中启用每日重复。")
            return
        st.caption("停止后只影响未来，过去已经生成的记录会保留。")
        for template in recurring:
            description, action = st.columns([5, 1])
            description.markdown(f"**{template['title']}**")
            description.caption(
                f"{template['time_slot']} · {template['estimated_minutes']} 分钟 · {template['category']}"
            )
            if action.button(
                "停止", key=f"planner_stop_recurring_{template['id']}", use_container_width=True
            ):
                stop_recurring_task(template["id"])
                st.rerun()


def render() -> None:
    page_header("计划", "用现实日期安排今天、明天或未来；过去的计划也始终可查。")
    selected_date = _date_navigator()

    tasks = list_tasks(selected_date.isoformat())
    _create_form(selected_date, expanded=not tasks)
    tasks = list_tasks(selected_date.isoformat())

    st.markdown("### 当天计划")
    _summary(tasks)
    capacity = assess_capacity(tasks)
    if capacity["overloaded"]:
        st.warning(
            f"当天仍需投入 {minutes_text(capacity['total_minutes'])}，已超过建议容量。"
            "可以顺延低优先级计划，给执行留出余量。"
        )

    _task_list(tasks)
    editing_task_id = st.session_state.get("planner_edit_task_id")
    if editing_task_id:
        _edit_panel(int(editing_task_id))

    st.divider()
    _recurring_plans()
