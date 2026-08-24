"""每日生活 + 学习 + 成长复盘。"""

from __future__ import annotations

from datetime import date, datetime

import streamlit as st

from database import execute, fetch_one
from pages.common import page_header


FIELDS = [
    "events", "main_task_done", "biggest_gain", "learning_improvement",
    "life_improvement", "work_problem", "life_state", "growth_thought",
    "time_waste", "tomorrow_main_task", "reduce_items", "keep_items",
    "problem_to_solve", "free_text",
]


def render() -> None:
    page_header("每日复盘", "复盘整天的生活，把今天的经验转成明天的选择。")
    review_date = st.date_input("复盘日期", date.today(), key="review_date")
    row = fetch_one(
        """
        SELECT events, main_task_done, biggest_gain, learning_improvement,
               life_improvement, work_problem, life_state, growth_thought,
               time_waste, tomorrow_main_task, reduce_items, keep_items,
               problem_to_solve, free_text
        FROM daily_reviews
        WHERE review_date = ?
        LIMIT 1
        """,
        (review_date.isoformat(),),
    ) or {field: "" for field in FIELDS}

    with st.form(f"review_form_{review_date}"):
        st.markdown("### A. 今天发生了什么")
        events = st.text_area(
            "1. 今天我实际做了什么？",
            value=row["events"],
            placeholder="学习、项目、阅读、锻炼、生活、社交、娱乐、临时事件……",
        )
        main_done = st.text_input("2. 今天最重要的任务完成了吗？", value=row["main_task_done"])
        biggest_gain = st.text_area("3. 今天最大的收获是什么？", value=row["biggest_gain"])

        st.markdown("### B. 今天哪里还可以优化")
        learning = st.text_area("4. 学习优化", value=row["learning_improvement"])
        life = st.text_area("5. 生活优化", value=row["life_improvement"])
        work_problem = st.text_area("6. 学习 / 工作遇到了什么问题？", value=row["work_problem"])
        life_state = st.text_area("7. 今天生活状态怎么样？", value=row["life_state"])
        growth = st.text_area("8. 今天有没有新的成长思考？", value=row["growth_thought"])
        waste = st.text_area("9. 今天浪费时间最多的地方是什么？", value=row["time_waste"])

        st.markdown("### C. 明天怎么调整")
        tomorrow = st.text_area("明天最重要的一件事情是什么？", value=row["tomorrow_main_task"])
        col1, col2 = st.columns(2)
        reduce_items = col1.text_area("要减少的事情", value=row["reduce_items"])
        keep_items = col2.text_area("要继续保持的事情", value=row["keep_items"])
        problem = st.text_area("需要解决的问题", value=row["problem_to_solve"])
        free_text = st.text_area("自由复盘 / 日记", value=row["free_text"], height=180)
        submitted = st.form_submit_button("保存今日复盘", type="primary")

    if submitted:
        execute(
            """
            INSERT INTO daily_reviews (
                review_date, events, main_task_done, biggest_gain,
                learning_improvement, life_improvement, work_problem, life_state,
                growth_thought, time_waste, tomorrow_main_task, reduce_items,
                keep_items, problem_to_solve, free_text, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(review_date) DO UPDATE SET
                events = excluded.events,
                main_task_done = excluded.main_task_done,
                biggest_gain = excluded.biggest_gain,
                learning_improvement = excluded.learning_improvement,
                life_improvement = excluded.life_improvement,
                work_problem = excluded.work_problem,
                life_state = excluded.life_state,
                growth_thought = excluded.growth_thought,
                time_waste = excluded.time_waste,
                tomorrow_main_task = excluded.tomorrow_main_task,
                reduce_items = excluded.reduce_items,
                keep_items = excluded.keep_items,
                problem_to_solve = excluded.problem_to_solve,
                free_text = excluded.free_text,
                updated_at = excluded.updated_at
            """,
            (
                review_date.isoformat(), events.strip(), main_done.strip(), biggest_gain.strip(),
                learning.strip(), life.strip(), work_problem.strip(), life_state.strip(),
                growth.strip(), waste.strip(), tomorrow.strip(), reduce_items.strip(),
                keep_items.strip(), problem.strip(), free_text.strip(),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        st.success("复盘已保存，关闭应用后仍会保留。")

