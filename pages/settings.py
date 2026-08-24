"""提醒设置。"""

from __future__ import annotations

from datetime import time

import streamlit as st

from database import get_setting, save_setting
from pages.common import page_header


def _parse_time(value: str) -> time:
    hour, minute = [int(part) for part in value.split(":")]
    return time(hour, minute)


def render() -> None:
    page_header("设置", "V1 使用应用内提醒：页面打开时检查，不在后台常驻。")
    with st.form("reminder_settings"):
        enabled = st.checkbox("开启任务提醒", value=get_setting("reminders_enabled", "1") == "1")
        lead_options = [5, 10, 15, 30]
        current_lead = int(get_setting("reminder_lead_minutes", "10"))
        lead = st.selectbox("提前提醒", lead_options, index=lead_options.index(current_lead))
        sleep_enabled = st.checkbox(
            "开启睡眠提醒", value=get_setting("sleep_reminder_enabled", "1") == "1"
        )
        sleep_time = st.time_input("默认睡觉时间", _parse_time(get_setting("sleep_time", "23:00")))
        prepare = st.number_input(
            "睡前准备提醒（提前分钟）",
            min_value=5,
            max_value=120,
            value=int(get_setting("sleep_prepare_minutes", "30")),
            step=5,
        )
        review_time = st.time_input("每日复盘提醒时间", _parse_time(get_setting("review_time", "21:15")))
        submitted = st.form_submit_button("保存设置", type="primary")
    if submitted:
        save_setting("reminders_enabled", "1" if enabled else "0")
        save_setting("reminder_lead_minutes", str(lead))
        save_setting("sleep_reminder_enabled", "1" if sleep_enabled else "0")
        save_setting("sleep_time", sleep_time.strftime("%H:%M"))
        save_setting("sleep_prepare_minutes", str(prepare))
        save_setting("review_time", review_time.strftime("%H:%M"))
        st.success("提醒设置已保存。")

