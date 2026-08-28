"""历史日记：月份浏览与默认阅读模式。"""

from __future__ import annotations

from datetime import date
from html import escape

import streamlit as st

from pages import today
from pages.common import page_header
from services.journal import get_day_details, list_journal_entries, recent_seven_day_stats


def _text_section(title: str, content: str) -> None:
    if not content:
        return
    st.markdown(f"### {title}")
    st.markdown(
        f'<div class="journal-prose">{escape(content)}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)


def _read_day(day: date) -> None:
    details = get_day_details(day)
    journal = details["journal"]
    snapshot = details["snapshot"]
    st.markdown(
        f"""
        <div class="day-hero">
          <div class="day-name">{day:%A}</div>
          <div class="day-date">{day:%Y} · {day:%m} · {day:%d}</div>
          <div class="day-question">{journal["mood"] or "那一天"}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if journal["focus"]:
        st.markdown(
            f'<div class="focus-note"><small>TODAY’S FOCUS</small><br><strong>{escape(journal["focus"])}</strong></div>',
            unsafe_allow_html=True,
        )
    if snapshot:
        with st.expander("🎯 当时的我正在为什么努力", expanded=False):
            st.markdown(f"**当前目标**  \n{snapshot['current_goal'] or '—'}")
            st.markdown(f"**当前主要矛盾**  \n{snapshot['primary_conflict'] or '—'}")
            if snapshot["current_stage"]:
                st.markdown(f"**当前阶段**  \n{snapshot['current_stage']}")

    if details["tasks"]:
        st.markdown("### 那天的计划")
        for task in details["tasks"]:
            marker = "✓" if task["status"] == "已完成" else "○"
            timing = task["start_time"] or task["time_slot"]
            st.markdown(f"{marker} **{timing}** · {task['title']}")
        st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)

    _text_section("✍️ 今天发生了什么", journal["day_story"])
    _text_section("🧠 学习", journal["learning_notes"])
    _text_section("🌿 生活", journal["life_notes"])
    _text_section("💭 成长思考", journal["growth_thoughts"])
    _text_section("📚 阅读留下的东西", journal["reading_note"])

    if details["reading"]:
        st.markdown("### 阅读记录")
        for item in details["reading"]:
            st.markdown(
                f"《{item['title']}》 · {item['minutes']} min · {item['pages_read']} 页"
            )
            if item["learned"]:
                st.caption(item["learned"])
    if journal["exercise_minutes"]:
        st.markdown(
            f"### 🌱 运动\n{journal['exercise_minutes']} 分钟 · "
            f"{journal['exercise_content'] or '未填写内容'}"
        )
    if details["notes"]:
        st.markdown("### 💡 那天的灵感")
        for note in details["notes"]:
            st.markdown(f"- {note['created_at'][11:16]} · {note['content']}")

    review_parts = [
        ("做得最好", journal["review_best"]),
        ("最大问题", journal["review_problem"]),
        ("最大收获", journal["review_gain"]),
        ("明天最重要的事", journal["tomorrow_focus"]),
        ("留给自己", journal["self_message"]),
    ]
    if any(value for _, value in review_parts):
        st.markdown(
            '<div class="chapter"><div class="chapter-kicker">END OF DAY</div></div>',
            unsafe_allow_html=True,
        )
        for label, value in review_parts:
            if value:
                st.markdown(f"**{label}**  \n{value}")


def render() -> None:
    page_header("日记", "不是数据列表，而是翻开以前生活过的每一天。")
    stats = recent_seven_day_stats()
    columns = st.columns(4)
    columns[0].metric("过去 7 天写日记", f"{stats['journal_days']} 天")
    columns[1].metric("阅读", f"{stats['reading_minutes']} min")
    columns[2].metric("锻炼", f"{stats['exercise_days']} 天")
    columns[3].metric("任务完成率", f"{stats['task_completion_rate']}%")

    month_value = st.date_input(
        "查看月份",
        value=date.today().replace(day=1),
        key="journal_month",
    )
    entries = list_journal_entries(month_value.strftime("%Y-%m"))
    st.markdown(f"## {month_value:%B %Y}")
    if not entries:
        st.info("这个月还没有保存过日记。")
        return

    labels = {}
    for entry in entries:
        entry_day = date.fromisoformat(entry["journal_date"])
        total = int(entry["task_total"] or 0)
        completed = int(entry["task_completed"] or 0)
        snippet = (
            entry["day_story"] or entry["focus"] or "这一天留下了一页记录"
        ).replace("\n", " ")
        labels[entry["journal_date"]] = (
            f"{entry_day:%b %d · %a}　{entry['mood'] or ''}　"
            f"任务 {completed}/{total}　{snippet[:42]}"
        )
    selected_text = st.selectbox(
        "选择一天",
        [entry["journal_date"] for entry in entries],
        format_func=labels.get,
        label_visibility="collapsed",
    )
    selected_day = date.fromisoformat(selected_text)
    edit_key = f"journal_edit_{selected_text}"
    if st.session_state.get(edit_key):
        if st.button("← 返回阅读模式", key=f"back_read_{selected_text}"):
            st.session_state[edit_key] = False
            st.rerun()
        today.render(selected_day, embedded=True)
    else:
        st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)
        if st.button("编辑这一天", key=f"edit_history_{selected_text}"):
            st.session_state[edit_key] = True
            st.rerun()
        _read_day(selected_day)
