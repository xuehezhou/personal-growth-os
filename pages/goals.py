"""目标与人生方向页面。"""

from __future__ import annotations

from datetime import date, datetime

import streamlit as st

from database import execute, fetch_all, fetch_one
from pages.common import page_header


LEVEL_LABELS = {"long_term": "长期目标", "stage": "阶段目标", "weekly": "本周目标"}


def _direction_editor() -> None:
    direction = fetch_one(
        """
        SELECT long_term_vision, primary_conflict, secondary_conflicts,
               current_priority, not_doing
        FROM directions
        WHERE id = 1
        LIMIT 1
        """
    ) or {}
    left, right = st.columns(2)
    with left:
        st.markdown("### 人生方向")
        st.markdown(f"**长期目标**  \\n+{direction.get('long_term_vision', '')}")
        st.markdown("### 当前主要矛盾")
        st.warning(direction.get("primary_conflict", "尚未设置"))
        st.markdown("**当前次要矛盾**")
        st.write(direction.get("secondary_conflicts", "尚未设置"))
    with right:
        st.markdown("### 当前优先解决")
        st.success(direction.get("current_priority", "尚未设置"))
        st.markdown("### 当前阶段暂时不做")
        st.info(direction.get("not_doing", "尚未设置"))

    with st.expander("编辑方向与矛盾"):
        with st.form("direction_form"):
            long_term = st.text_area("长期目标", value=direction.get("long_term_vision", ""))
            primary = st.text_area("当前主要矛盾", value=direction.get("primary_conflict", ""))
            secondary = st.text_area("当前次要矛盾", value=direction.get("secondary_conflicts", ""))
            priority = st.text_area("当前优先解决", value=direction.get("current_priority", ""))
            not_doing = st.text_area("当前阶段暂时不重点投入", value=direction.get("not_doing", ""))
            saved = st.form_submit_button("保存方向", type="primary")
        if saved:
            execute(
                """
                UPDATE directions
                SET long_term_vision = ?, primary_conflict = ?, secondary_conflicts = ?,
                    current_priority = ?, not_doing = ?, updated_at = ?
                WHERE id = 1
                """,
                (
                    long_term.strip(), primary.strip(), secondary.strip(), priority.strip(),
                    not_doing.strip(), datetime.now().isoformat(timespec="seconds"),
                ),
            )
            st.success("人生方向已保存。")
            st.rerun()


def _goal_editor() -> None:
    goals = fetch_all(
        """
        SELECT id, parent_id, level, name, why, start_date, target_date, progress,
               success_criteria, status, is_current
        FROM goals
        ORDER BY
            CASE level WHEN 'long_term' THEN 1 WHEN 'stage' THEN 2 ELSE 3 END,
            is_current DESC,
            id
        LIMIT 100
        """
    )
    st.markdown("### Goal → Weekly Goal → Task")
    if not goals:
        st.caption("尚未创建目标。")
    for goal in goals:
        icon = "🎯" if goal["is_current"] else "○"
        with st.container(border=True):
            top = st.columns([4, 1])
            top[0].markdown(f"#### {icon} {goal['name']}")
            top[0].caption(f"{LEVEL_LABELS[goal['level']]} · {goal['status']}")
            top[1].metric("进度", f"{goal['progress']}%")
            st.progress(int(goal["progress"]))
            if goal["why"]:
                st.write(f"为什么：{goal['why']}")
            if goal["success_criteria"]:
                st.write(f"成功标准：{goal['success_criteria']}")

    with st.expander("＋ 新建目标"):
        parent_options = [None] + [goal["id"] for goal in goals]
        parent_labels = {None: "无上级目标", **{goal["id"]: goal["name"] for goal in goals}}
        with st.form("new_goal"):
            name = st.text_input("目标名称 *")
            level = st.selectbox("层级", list(LEVEL_LABELS), format_func=LEVEL_LABELS.get)
            parent_id = st.selectbox("上级目标", parent_options, format_func=parent_labels.get)
            why = st.text_area("为什么做")
            col1, col2 = st.columns(2)
            start = col1.date_input("开始日期", date.today())
            target = col2.date_input("目标截止日期", date.today())
            progress = st.slider("当前进度", 0, 100, 0)
            criteria = st.text_area("成功标准")
            is_current = st.checkbox("设为当前最高优先级目标")
            submitted = st.form_submit_button("创建目标", type="primary")
        if submitted:
            if not name.strip():
                st.error("目标名称不能为空。")
            else:
                if is_current:
                    execute("UPDATE goals SET is_current = 0 WHERE is_current = 1")
                execute(
                    """
                    INSERT INTO goals (
                        parent_id, level, name, why, start_date, target_date, progress,
                        success_criteria, status, is_current, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '进行中', ?, ?)
                    """,
                    (
                        parent_id, level, name.strip(), why.strip(), start.isoformat(),
                        target.isoformat(), progress, criteria.strip(), int(is_current),
                        datetime.now().isoformat(timespec="seconds"),
                    ),
                )
                st.success("目标已创建。")
                st.rerun()

    if goals:
        with st.expander("编辑已有目标"):
            selected_id = st.selectbox(
                "选择目标", [goal["id"] for goal in goals],
                format_func=lambda goal_id: next(goal["name"] for goal in goals if goal["id"] == goal_id),
            )
            goal = next(item for item in goals if item["id"] == selected_id)
            with st.form(f"edit_goal_{selected_id}"):
                name = st.text_input("名称", value=goal["name"])
                why = st.text_area("为什么做", value=goal["why"])
                progress = st.slider("进度", 0, 100, int(goal["progress"]))
                criteria = st.text_area("成功标准", value=goal["success_criteria"])
                status = st.selectbox("状态", ["进行中", "已完成", "已暂停"], index=["进行中", "已完成", "已暂停"].index(goal["status"]))
                is_current = st.checkbox("当前最高优先级目标", value=bool(goal["is_current"]))
                saved = st.form_submit_button("保存目标")
            if saved:
                if is_current:
                    execute("UPDATE goals SET is_current = 0 WHERE is_current = 1")
                execute(
                    """
                    UPDATE goals
                    SET name = ?, why = ?, progress = ?, success_criteria = ?,
                        status = ?, is_current = ?
                    WHERE id = ?
                    """,
                    (name.strip(), why.strip(), progress, criteria.strip(), status, int(is_current), selected_id),
                )
                st.success("目标已更新。")
                st.rerun()


def render() -> None:
    page_header("目标与方向", "先决定往哪里走，再决定今天做什么。")
    _direction_editor()
    st.divider()
    _goal_editor()

