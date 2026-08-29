"""Study Diary Streamlit 入口。"""

from __future__ import annotations

from datetime import date

import streamlit as st

from database import init_database
from pages import books, goals, journal, settings, tasks, today
from services.journal import create_quick_note
from services.tasks import materialize_daily_tasks


st.set_page_config(
    page_title="Study Diary",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        :root {
            --paper: #fbfaf6;
            --ink: #29312e;
            --muted: #75807b;
            --sage: #789486;
            --sage-soft: #e8efea;
            --warm: #f2eadf;
        }
        .stApp { background: var(--paper); color: var(--ink); }
        .block-container {
            max-width: 1060px;
            padding-top: 2.2rem;
            padding-bottom: 7rem;
        }
        [data-testid="stSidebar"] {
            background: #eef2ed;
            border-right: 1px solid #dde5df;
        }
        [data-testid="stSidebar"] * { color: #314039; }
        h1, h2, h3 { letter-spacing: -0.02em; }
        .day-hero {
            padding: 2.8rem 0 3.2rem;
            margin-bottom: 1.5rem;
        }
        .day-name {
            color: var(--sage);
            font-size: .86rem;
            font-weight: 700;
            letter-spacing: .18em;
            text-transform: uppercase;
        }
        .day-date {
            font-family: Georgia, "Times New Roman", serif;
            font-size: 3.15rem;
            line-height: 1.08;
            margin: .35rem 0 .6rem;
            color: #26332d;
        }
        .day-question { color: var(--muted); font-size: 1.08rem; }
        .section-space { height: 2.7rem; }
        .chapter {
            margin-top: 3.8rem;
            padding-top: 2.4rem;
            border-top: 1px solid #dfe5e1;
        }
        .chapter-kicker {
            color: var(--sage);
            font-size: .78rem;
            font-weight: 800;
            letter-spacing: .2em;
        }
        .direction-note {
            padding: 1.35rem 1.5rem;
            border-radius: 16px;
            background: var(--sage-soft);
            margin: 1rem 0;
        }
        .focus-note {
            padding: 1.6rem 1.7rem;
            border-radius: 18px;
            background: #fff;
            border: 1px solid #e4e4dd;
            box-shadow: 0 8px 28px rgba(50, 67, 58, .05);
        }
        .timeline-item {
            border-left: 2px solid #b6c7bd;
            padding: .2rem 0 1.25rem 1.25rem;
            margin-left: .35rem;
        }
        .timeline-time { color: var(--sage); font-weight: 700; font-size: .85rem; }
        .timeline-title { font-size: 1rem; color: var(--ink); }
        .journal-prose {
            font-family: Georgia, "Times New Roman", serif;
            white-space: pre-wrap;
            line-height: 1.85;
            font-size: 1.06rem;
        }
        .saved-note { color: #668273; font-size: .84rem; }
        div[data-testid="stProgress"] > div > div { background-color: var(--sage); }
        div[data-testid="stMetric"] {
            background: transparent;
            border: 0;
            padding: .2rem .4rem;
        }
        .stButton button, .stFormSubmitButton button { border-radius: 10px; }
        textarea { line-height: 1.65 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

init_database()
materialize_daily_tasks()

PAGES = {
    "📖 今天": today.render,
    "＋ 计划": tasks.render,
    "📅 日记": journal.render,
    "🎯 方向": goals.render,
    "📚 阅读": books.render,
    "⚙️ 设置": settings.render,
}

with st.sidebar:
    st.markdown("## 📖 Study Diary")
    st.caption("一天一页，记下真实生活。")
    selected_page = st.radio(
        "导航",
        list(PAGES),
        label_visibility="collapsed",
        key="main_navigation",
    )
    st.divider()
    st.markdown("### 💡 快速记录")
    with st.form("sidebar_quick_note", clear_on_submit=True):
        quick_content = st.text_area(
            "刚刚想到什么？",
            placeholder="只管记下来，暂时不用分类。",
            height=92,
            label_visibility="collapsed",
        )
        quick_saved = st.form_submit_button("保存灵感", use_container_width=True)
    if quick_saved:
        try:
            create_quick_note(quick_content, date.today())
            st.success("已放入今天的灵感箱")
        except ValueError as error:
            st.error(str(error))
    st.divider()
    st.caption("本地单用户 · 数据只保存在 SQLite")

PAGES[selected_page]()
