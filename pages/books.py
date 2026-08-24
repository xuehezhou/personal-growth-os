"""书单、当前阅读与轻量阅读记录。"""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from database import execute, fetch_all
from pages.common import minutes_text, page_header
from services.books import add_reading_log


def _book_progress(book: dict) -> None:
    total = int(book["total_pages"])
    current = int(book["current_page"])
    percentage = round(current / total * 100) if total else 0
    st.markdown(f"#### 《{book['title']}》")
    st.caption(f"{book['stage']} · {book['category']} · 推荐顺序 {book['sequence']}")
    st.progress(min(percentage, 100))
    if total:
        st.write(f"进度：{current} / {total} 页（{percentage}%）")
    else:
        st.write("进度：请先填写总页数")
    st.caption(f"累计阅读：{minutes_text(book['total_minutes'])} · 目的：{book['purpose']}")
    if book["target_date"]:
        remaining = (date.fromisoformat(book["target_date"]) - date.today()).days
        st.caption(f"预计还有：{max(0, remaining)} 天完成")


def _reading_log_form(current_books: list[dict]) -> None:
    if not current_books:
        st.info("还没有当前阅读。请先从书单中选择一本开始阅读。")
        return
    book_ids = [book["id"] for book in current_books]
    labels = {book["id"]: book["title"] for book in current_books}
    with st.form("reading_log", clear_on_submit=True):
        book_id = st.selectbox("书籍", book_ids, format_func=labels.get)
        col1, col2 = st.columns(2)
        minutes = col1.number_input("今天阅读分钟", min_value=1, value=30)
        pages = col2.number_input("今天读了多少页", min_value=0, value=0)
        learned = st.text_area("今天学到了什么？")
        changed = st.text_area("哪个观点改变了我的认知？")
        link = st.text_area("这个知识跟现实有什么关系？")
        application = st.text_area("能否应用到 AI 项目 / 工作 / 人生？")
        submitted = st.form_submit_button("保存阅读记录", type="primary")
    if submitted:
        try:
            add_reading_log(book_id, minutes, pages, learned, changed, link, application)
            st.success("阅读记录已保存。")
            st.rerun()
        except ValueError as error:
            st.error(str(error))


def _manage_book(books: list[dict]) -> None:
    book_ids = [book["id"] for book in books]
    labels = {book["id"]: book["title"] for book in books}
    with st.expander("设置阅读状态与进度"):
        selected_id = st.selectbox("选择书籍", book_ids, format_func=labels.get)
        book = next(item for item in books if item["id"] == selected_id)
        with st.form(f"book_manage_{selected_id}"):
            status_options = ["待读", "当前阅读", "已完成"]
            status = st.selectbox("阅读状态", status_options, index=status_options.index(book["status"]))
            is_light = st.checkbox("作为并行轻阅读", value=bool(book["is_light_reading"]))
            col1, col2 = st.columns(2)
            total_pages = col1.number_input("总页数", min_value=0, value=int(book["total_pages"]))
            current_page = col2.number_input("当前页数", min_value=0, value=int(book["current_page"]))
            start_date = st.date_input(
                "开始日期", date.fromisoformat(book["start_date"]) if book["start_date"] else date.today()
            )
            target_default = date.fromisoformat(book["target_date"]) if book["target_date"] else date.today() + timedelta(weeks=int(book["estimated_weeks"]))
            target_date = st.date_input("预计完成日期", target_default)
            notes = st.text_area("阅读笔记", value=book["notes"])
            saved = st.form_submit_button("保存书籍信息")
        if saved:
            if status == "当前阅读":
                active = [item for item in books if item["status"] == "当前阅读" and item["id"] != selected_id]
                main_count = sum(not item["is_light_reading"] for item in active) + int(not is_light)
                light_count = sum(bool(item["is_light_reading"]) for item in active) + int(is_light)
                if main_count > 1 or light_count > 1:
                    st.error("同一时间最多精读 1 本主书，并行 1 本轻阅读。请先调整其他书籍状态。")
                    return
            execute(
                """
                UPDATE books
                SET status = ?, is_light_reading = ?, total_pages = ?, current_page = ?,
                    start_date = ?, target_date = ?, notes = ?
                WHERE id = ?
                """,
                (
                    status, int(is_light), total_pages, min(current_page, total_pages) if total_pages else current_page,
                    start_date.isoformat(), target_date.isoformat(), notes.strip(), selected_id,
                ),
            )
            st.success("书籍信息已保存。")
            st.rerun()


def render() -> None:
    page_header("阅读", "阅读不是为了收藏和打卡，而是为了改变判断与行动。")
    books = fetch_all(
        """
        SELECT id, title, list_type, stage, category, sequence, purpose,
               estimated_weeks, total_pages, current_page, start_date,
               target_date, status, today_minutes, total_minutes, notes,
               is_light_reading
        FROM books
        ORDER BY sequence
        LIMIT 100
        """
    )
    current_books = [book for book in books if book["status"] == "当前阅读"]
    st.markdown("### 当前阅读")
    if current_books:
        columns = st.columns(len(current_books))
        for column, book in zip(columns, current_books):
            with column.container(border=True):
                _book_progress(book)
    else:
        st.caption("尚未开始阅读。建议先从《原子习惯》或《深度工作》开始。")

    _reading_log_form(current_books)
    _manage_book(books)

    tabs = st.tabs(["核心书单", "扩展书单", "待读书单", "已完成"])
    filters = [
        lambda book: book["list_type"] == "核心书单",
        lambda book: book["list_type"] == "扩展书单",
        lambda book: book["status"] == "待读",
        lambda book: book["status"] == "已完成",
    ]
    for tab, predicate in zip(tabs, filters):
        with tab:
            for book in filter(predicate, books):
                with st.container(border=True):
                    _book_progress(book)

