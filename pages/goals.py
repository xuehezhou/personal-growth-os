"""方向页：一本轻量的阶段思考页。"""

from __future__ import annotations

import streamlit as st

from pages.common import page_header
from services.directions import get_direction, save_direction


def render() -> None:
    page_header("方向", "方向可以变化，但今天保存过的方向快照不会被未来覆盖。")
    direction = get_direction()

    st.markdown("## Long Term")
    st.caption("不需要写得宏大，只写此刻真正相信的方向。")
    with st.form("direction_page_form"):
        long_term = st.text_area(
            "我的长期目标",
            value=direction["long_term_vision"],
            height=150,
            placeholder="我希望几年后的自己，正在过怎样的生活、做怎样的事情？",
        )

        st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)
        st.markdown("## Current Stage")
        stage = st.text_area(
            "当前阶段目标",
            value=direction["current_stage"],
            placeholder="这一阶段最重要的成长主题是什么？",
        )
        current_goal = st.text_area(
            "当前目标",
            value=direction["current_goal"],
            placeholder="现在正在全力完成什么？",
        )

        st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)
        st.markdown("## Current Problem")
        primary = st.text_area(
            "当前主要矛盾",
            value=direction["primary_conflict"],
            placeholder="现在最阻碍我继续成长的问题是什么？",
        )
        secondary = st.text_area(
            "当前次要矛盾",
            value=direction["secondary_conflicts"],
            placeholder="一行一个，写下仍需留意但不抢占核心注意力的问题。",
        )

        left, right = st.columns(2)
        priority = left.text_area(
            "当前优先解决",
            value=direction["current_priority"],
            placeholder="接下来先解决什么？",
        )
        not_doing = right.text_area(
            "当前暂时不做",
            value=direction["not_doing"],
            placeholder="为了保持专注，哪些事情先放下？",
        )
        saved = st.form_submit_button("保存方向", type="primary")

    if saved:
        save_direction(
            {
                "long_term_vision": long_term,
                "current_stage": stage,
                "current_goal": current_goal,
                "primary_conflict": primary,
                "secondary_conflicts": secondary,
                "current_priority": priority,
                "not_doing": not_doing,
            }
        )
        st.success("方向已保存。以后日记首次保存时，会保留当天的方向快照。")
        st.rerun()

    if direction["updated_at"]:
        st.caption(f"最近更新：{direction['updated_at'].replace('T', ' ')}")
