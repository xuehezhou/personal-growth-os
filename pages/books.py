"""书单、当前阅读与每日阅读记录。"""

from __future__ import annotations

from datetime import date

import streamlit as st

from pages.common import page_header
from services.books import (
    add_book,
    add_reading_log,
    delete_book,
    list_books,
    reading_minutes_for_day,
    update_book,
)


def _progress(book: dict) -> None:
    total = int(book["total_pages"])
    current = int(book["current_page"])
    percent = min(100, round(current / total * 100)) if total else 0
    st.markdown(f"### 《{book['title']}》")
    st.caption(
        f"{book['category']} · 今日 {reading_minutes_for_day(date.today(), book['id'])} min "
        f"· 累计 {book['total_minutes']} min"
    )
    if total:
        st.progress(percent)
        st.caption(f"{current} / {total} 页 · {percent}%")
    else:
        st.caption(f"当前 {current} 页 · 尚未填写总页数")


def _log_form(current_books: list[dict]) -> None:
    if not current_books:
        st.info("先从书单中选择一本，设为“当前阅读”。")
        return
    labels = {book["id"]: book["title"] for book in current_books}
    with st.form("book_reading_log", clear_on_submit=True):
        book_id = st.selectbox("当前阅读", list(labels), format_func=labels.get)
        left, right = st.columns(2)
        minutes = left.number_input("今天阅读分钟", min_value=1, value=30)
        pages = right.number_input("今天读了多少页", min_value=0, value=0)
        learned = st.text_area(
            "今天读到什么值得记住？",
            placeholder="留下一段能在未来重新理解这次阅读的话。",
        )
        saved = st.form_submit_button("保存阅读记录", type="primary")
    if saved:
        add_reading_log(book_id, minutes, pages, learned, "", "", "")
        st.success("阅读记录已保存")
        st.rerun()


def _add_book() -> None:
    with st.expander("＋ 添加一本书"):
        with st.form("add_book_form", clear_on_submit=True):
            title = st.text_input("书名")
            left, right = st.columns(2)
            category = left.text_input("分类", value="自定义")
            total_pages = right.number_input("总页数（可选）", min_value=0, value=0)
            submitted = st.form_submit_button("加入书单")
        if submitted:
            try:
                add_book(title, total_pages, category)
                st.success("已加入书单")
                st.rerun()
            except ValueError as error:
                st.error(str(error))


def _manage_book(book: dict, context: str) -> None:
    with st.expander(f"管理《{book['title']}》"):
        statuses = ["待读", "当前阅读", "已完成"]
        with st.form(f"manage_book_{context}_{book['id']}"):
            title = st.text_input("书名", value=book["title"])
            left, right = st.columns(2)
            total_pages = left.number_input(
                "总页数", min_value=0, value=int(book["total_pages"])
            )
            current_page = right.number_input(
                "当前页", min_value=0, value=int(book["current_page"])
            )
            status = st.selectbox(
                "状态", statuses, index=statuses.index(book["status"])
            )
            light = st.checkbox(
                "作为轻阅读",
                value=bool(book["is_light_reading"]),
                help="可以与一本主书同时阅读。",
            )
            notes = st.text_area("书籍备注", value=book["notes"])
            saved = st.form_submit_button("保存")
        if saved:
            try:
                update_book(
                    book["id"],
                    {
                        "title": title,
                        "total_pages": total_pages,
                        "current_page": current_page,
                        "status": status,
                        "is_light_reading": light,
                        "notes": notes,
                    },
                )
                st.rerun()
            except ValueError as error:
                st.error(str(error))

        st.warning("删除书籍会同时删除这本书的阅读记录。")
        confirmed = st.checkbox(
            "我确认删除书籍和相关阅读记录",
            key=f"confirm_delete_book_{context}_{book['id']}",
        )
        if st.button("删除这本书", key=f"delete_book_{context}_{book['id']}"):
            try:
                delete_book(book["id"], confirmed)
                st.rerun()
            except ValueError as error:
                st.error(str(error))


def render() -> None:
    page_header("阅读", "少一些书单压力，多留下一点真正改变自己的东西。")
    books = list_books()
    current_books = [book for book in books if book["status"] == "当前阅读"]

    st.markdown("## 当前阅读")
    if current_books:
        columns = st.columns(min(2, len(current_books)))
        for index, book in enumerate(current_books):
            with columns[index % len(columns)]:
                _progress(book)
    else:
        st.caption("还没有当前阅读。")
    _log_form(current_books)

    st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)
    st.markdown("## 我的书单")
    _add_book()
    tabs = st.tabs(["待读", "当前阅读", "已完成", "全部"])
    predicates = [
        lambda item: item["status"] == "待读",
        lambda item: item["status"] == "当前阅读",
        lambda item: item["status"] == "已完成",
        lambda item: True,
    ]
    for tab_index, (tab, predicate) in enumerate(zip(tabs, predicates)):
        with tab:
            matching = [book for book in books if predicate(book)]
            if not matching:
                st.caption("这里还是空的。")
            for book in matching:
                _progress(book)
                _manage_book(book, str(tab_index))
                st.divider()
