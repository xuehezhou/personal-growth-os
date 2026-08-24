"""Personal Growth OS Streamlit 入口。"""

from __future__ import annotations

import streamlit as st

from database import init_database
from pages import books, dashboard, goals, habits, review, settings, tasks, today
from services.tasks import materialize_daily_tasks


st.set_page_config(
    page_title="Personal Growth OS",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .stApp { background: #f6f7f9; }
        .block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1280px; }
        [data-testid="stSidebar"] { background: #13231b; }
        [data-testid="stSidebar"] * { color: #edf6f0; }
        .hero {
            padding: 1.4rem 1.6rem; border-radius: 18px;
            background: linear-gradient(135deg, #183d2d, #2d6a4f);
            color: white; margin-bottom: 1rem;
        }
        .hero h1 { margin: 0; font-size: 2rem; }
        .hero p { margin: .35rem 0 0; color: #cfe4d7; }
        .task-card {
            background: white; border: 1px solid #e5e9e7; border-left: 5px solid #40916c;
            border-radius: 12px; padding: .85rem 1rem; margin: .5rem 0;
        }
        .task-card.done { opacity: .68; border-left-color: #9ca3af; }
        .task-meta { color: #66736d; font-size: .86rem; margin-top: .25rem; }
        .eyebrow { color: #2d6a4f; font-weight: 700; letter-spacing: .08em; font-size: .78rem; }
        div[data-testid="stMetric"] {
            background: white; border: 1px solid #e6ebe8; border-radius: 14px; padding: .7rem 1rem;
        }
        .priority-box {
            background: #fff8e7; border: 1px solid #f3d58b; border-radius: 14px;
            padding: 1rem 1.2rem; margin-bottom: 1rem;
        }
        .small-muted { color: #6b7280; font-size: .88rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

init_database()
materialize_daily_tasks()

PAGES = {
    "今日": today.render,
    "目标与方向": goals.render,
    "任务": tasks.render,
    "阅读": books.render,
    "习惯": habits.render,
    "复盘": review.render,
    "数据统计": dashboard.render,
    "设置": settings.render,
}

with st.sidebar:
    st.markdown("## 🌱 Growth OS")
    st.caption("把长期方向，变成今天的行动。")
    selected_page = st.radio("导航", list(PAGES), label_visibility="collapsed")
    st.divider()
    st.caption("V1 · 本地单用户 · 数据保存在 SQLite")

PAGES[selected_page]()
