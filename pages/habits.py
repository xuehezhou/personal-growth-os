"""习惯页面。"""

from __future__ import annotations

from datetime import date

import streamlit as st

from models import CATEGORIES
from pages.common import page_header
from services.habits import calculate_streak, create_habit, list_habits, save_habit_log


def _create_habit_form() -> None:
    with st.expander("＋ 新增每日习惯"):
        with st.form("create_daily_habit", clear_on_submit=True):
            name = st.text_input("名称 *", placeholder="例如：喝水 8 杯")
            col1, col2 = st.columns(2)
            category = col1.selectbox("所属领域", CATEGORIES, index=CATEGORIES.index("生活"))
            target_minutes = col2.number_input(
                "每日目标分钟（非时间型习惯可填 0）",
                min_value=0,
                value=30,
                step=5,
            )
            submitted = st.form_submit_button("创建每日习惯", type="primary")
        if submitted:
            try:
                create_habit(name, category, target_minutes)
                st.success("每日习惯已创建，今后每天都会出现在习惯清单中。")
                st.rerun()
            except ValueError as error:
                st.error(str(error))


def render() -> None:
    page_header("习惯", "连续性不是目的；它是稳定生活和长期能力的证据。")
    _create_habit_form()
    selected_date = st.date_input("打卡日期", date.today(), key="habit_date")
    habits = list_habits(selected_date.isoformat())
    for habit in habits:
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 1, 1])
            col1.markdown(f"### {habit['name']}")
            col1.caption(f"{habit['category']} · 每日目标 {habit['target_minutes']} 分钟")
            col2.metric("连续完成", f"🔥 {calculate_streak(habit['id'])} 天")
            completed = col3.checkbox(
                "已完成", value=bool(habit["completed"]), key=f"habit_done_{selected_date}_{habit['id']}"
            )
            minutes = st.number_input(
                "实际分钟",
                min_value=0,
                value=int(habit["minutes"]),
                key=f"habit_minutes_{selected_date}_{habit['id']}",
            )
            notes = st.text_input(
                "备注", value=habit["notes"], key=f"habit_note_{selected_date}_{habit['id']}"
            )
            if st.button("保存打卡", key=f"save_habit_{selected_date}_{habit['id']}"):
                save_habit_log(habit["id"], selected_date.isoformat(), completed, minutes, notes)
                st.success(f"{habit['name']} 已保存。")
