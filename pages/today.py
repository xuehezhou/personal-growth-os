"""一天一页的 Study Diary 主页面。"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from html import escape

import streamlit as st

from database import get_setting
from pages.common import minutes_text
from services.books import add_reading_log, list_books, reading_minutes_for_day
from services.directions import get_direction
from services.habits import list_habits, save_habit_log
from services.journal import (
    delete_quick_note,
    get_journal,
    list_quick_notes,
    save_journal,
    update_quick_note,
)
from services.tasks import (
    complete_task,
    create_task,
    delete_task,
    list_tasks,
    materialize_daily_tasks,
    update_task,
)


MOODS = ["😀 很好", "🙂 不错", "😐 一般", "😴 有点累", "😞 不太好"]
SLOTS = (("上午", "☀️"), ("下午", "🌤"), ("晚上", "🌙"), ("全天", "·"))
WEEKDAYS = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")


def _time_value(value: str | None) -> time | None:
    return datetime.strptime(value, "%H:%M").time() if value else None


def _move_to_direction() -> None:
    st.session_state["main_navigation"] = "🎯 方向"


def _day_label(day: date) -> str:
    difference = (day - date.today()).days
    if difference == -1:
        return "昨天"
    if difference == 0:
        return "今天"
    if difference == 1:
        return "明天"
    return f"{day:%m月%d日}"


def _set_today_view_date(day: date) -> None:
    st.session_state["today_view_date"] = day


def _date_selector() -> date:
    if "today_view_date" not in st.session_state:
        st.session_state["today_view_date"] = date.today()

    selected = st.session_state["today_view_date"]
    today_column, tomorrow_column, picker_column = st.columns(
        [1.15, 1.15, 3.2], vertical_alignment="bottom"
    )
    today_column.button(
        "今日计划",
        type="primary" if selected == date.today() else "secondary",
        use_container_width=True,
        on_click=_set_today_view_date,
        args=(date.today(),),
    )
    tomorrow_column.button(
        "明日安排",
        type="primary" if selected == date.today() + timedelta(days=1) else "secondary",
        use_container_width=True,
        on_click=_set_today_view_date,
        args=(date.today() + timedelta(days=1),),
    )
    selected = picker_column.date_input(
        "日期查询",
        key="today_view_date",
        format="YYYY-MM-DD",
        help="选择过去或未来的日期，查看并编辑那一天的完整安排。",
    )
    if selected != date.today():
        relation = _day_label(selected)
        st.caption(
            f"正在查看 {relation} · {selected:%Y年%m月%d日} · {WEEKDAYS[selected.weekday()]}。"
            "下面所有新增和保存都只写入这个日期。"
        )
    return selected


def _header(day: date, journal: dict) -> None:
    day_label = _day_label(day)
    question = "今天想怎样度过？" if day == date.today() else f"{day_label}想怎样度过？"
    st.markdown(
        f"""
        <div class="day-hero">
          <div class="day-name">{WEEKDAYS[day.weekday()]}</div>
          <div class="day-date">{day:%Y} · {day:%m} · {day:%d}</div>
          <div class="day-question">{question}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    mood_index = MOODS.index(journal["mood"]) if journal["mood"] in MOODS else 2
    with st.form(f"day_intention_{day.isoformat()}"):
        mood = st.radio(f"{day_label}状态", MOODS, index=mood_index, horizontal=True)
        st.markdown("### Today’s Focus")
        focus = st.text_input(
            f"{day_label}如果只能完成一件事情，我希望完成什么？",
            value=journal["focus"],
            placeholder="只写一件。",
        )
        left, right = st.columns(2)
        second = left.text_input(
            "另外一件重要的事",
            value=journal["secondary_focus_1"],
            placeholder="最多再安排两件",
        )
        third = right.text_input(
            "第三件重要的事",
            value=journal["secondary_focus_2"],
            placeholder="留空也很好",
        )
        submitted = st.form_submit_button(f"保存{day_label}的开始", type="primary")
    if submitted:
        save_journal(
            day,
            {
                "mood": mood,
                "focus": focus,
                "secondary_focus_1": second,
                "secondary_focus_2": third,
            },
        )
        st.success(f"{day_label}的状态与重点已保存")
        st.rerun()


def _direction_card() -> None:
    direction = get_direction()
    current_goal = escape(direction["current_goal"] or "尚未填写")
    primary_conflict = escape(direction["primary_conflict"] or "尚未填写")
    left, right = st.columns([4, 1])
    with left:
        st.markdown("## 🎯 此刻最重要的方向")
        st.markdown(
            f"""
            <div class="direction-note">
              <strong>当前目标</strong><br>{current_goal}<br><br>
              <strong>当前主要矛盾</strong><br>{primary_conflict}
            </div>
            """,
            unsafe_allow_html=True,
        )
    right.button(
        "编辑方向",
        on_click=_move_to_direction,
        use_container_width=True,
        key="today_edit_direction",
    )


def _quick_task_form(day: date) -> None:
    day_label = _day_label(day)
    with st.expander(f"＋ 添加{day_label}计划", expanded=False):
        with st.form(f"quick_task_{day.isoformat()}", clear_on_submit=True):
            title = st.text_input("任务名称", placeholder="例如：下午修项目 Bug")
            left, right = st.columns(2)
            start = left.time_input("时间（可选）", value=None)
            slot = right.selectbox("时间段", ["上午", "下午", "晚上", "全天"])
            notes = st.text_area("备注（可选）", height=80)
            added = st.form_submit_button(f"加入{day_label}计划", type="primary")
        if added:
            try:
                create_task(
                    {
                        "title": title,
                        "planned_date": day.isoformat(),
                        "start_time": start.strftime("%H:%M") if start else None,
                        "time_slot": slot,
                        "category": "个人事务",
                        "priority": "普通",
                        "estimated_minutes": 0,
                        "acceptance_criteria": "任务已完成",
                        "notes": notes,
                        "source": "user",
                    }
                )
                st.success(f"已加入{day_label}计划")
                st.rerun()
            except ValueError as error:
                st.error(str(error))


def _task_editor(task: dict) -> None:
    with st.expander("编辑", expanded=False):
        with st.form(f"edit_day_task_{task['id']}"):
            title = st.text_input("任务", value=task["title"])
            left, right = st.columns(2)
            start = left.time_input("开始", value=_time_value(task["start_time"]))
            end = right.time_input("结束", value=_time_value(task["end_time"]))
            slot = st.selectbox(
                "时间段",
                ["上午", "下午", "晚上", "全天"],
                index=["上午", "下午", "晚上", "全天"].index(task["time_slot"]),
            )
            notes = st.text_area("备注", value=task["notes"], height=70)
            saved = st.form_submit_button("保存修改")
        if saved:
            try:
                update_task(
                    task["id"],
                    {
                        "title": title,
                        "start_time": start.strftime("%H:%M") if start else None,
                        "end_time": end.strftime("%H:%M") if end else None,
                        "time_slot": slot,
                        "notes": notes,
                    },
                )
                st.rerun()
            except ValueError as error:
                st.error(str(error))
        if st.button("删除这项", key=f"delete_day_task_{task['id']}"):
            delete_task(task["id"])
            st.rerun()


def _timeline(day: date) -> None:
    day_label = _day_label(day)
    st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)
    st.markdown(f"## {day_label}的时间安排")
    _quick_task_form(day)
    tasks = list_tasks(day.isoformat())
    for slot, icon in SLOTS:
        slot_tasks = [task for task in tasks if task["time_slot"] == slot]
        st.markdown(f"### {icon} {slot}")
        if not slot_tasks:
            st.caption("留白，也是一种安排。")
            continue
        for task in slot_tasks:
            left, middle, right = st.columns([1.4, 6, 1.4])
            time_text = task["start_time"] or "随时"
            if task["end_time"]:
                time_text += f" — {task['end_time']}"
            left.markdown(f"**{time_text}**")
            done = task["status"] == "已完成"
            middle.markdown(f"{'~~' if done else ''}{task['title']}{'~~' if done else ''}")
            if done:
                right.caption("✓ 已完成")
            elif right.button("完成", key=f"finish_day_task_{task['id']}"):
                complete_task(task["id"])
                st.rerun()
            _task_editor(task)
    total = len(tasks)
    completed = sum(task["status"] == "已完成" for task in tasks)
    rate = round(completed / total * 100) if total else 0
    st.caption(f"{day_label} {total} 项 · 已完成 {completed} 项 · {rate}%")
    st.progress(rate)


def _habit_strip(day: date) -> None:
    habits = list_habits(day.isoformat())
    if not habits:
        return
    st.markdown("### 🌱 Life")
    columns = st.columns(3)
    for index, habit in enumerate(habits):
        with columns[index % 3]:
            checked = st.checkbox(
                habit["name"],
                value=bool(habit["completed"]),
                key=f"diary_habit_{day}_{habit['id']}",
            )
            if checked != bool(habit["completed"]):
                save_habit_log(
                    habit["id"],
                    day.isoformat(),
                    checked,
                    habit["target_minutes"] if checked else 0,
                )
                st.rerun()


def _reading(day: date) -> None:
    current_books = [book for book in list_books() if book["status"] == "当前阅读"]
    st.markdown("## 📚 Reading")
    if not current_books:
        st.caption("还没有设置当前阅读，可在“阅读”页选择一本。")
        return
    for book in current_books:
        total = int(book["total_pages"])
        current = int(book["current_page"])
        today_minutes = reading_minutes_for_day(day, book["id"])
        st.markdown(f"### 《{book['title']}》")
        st.caption(f"今天 {today_minutes} min · 进度 {current} / {total or '—'}")
        if total:
            st.progress(min(100, round(current / total * 100)))
    with st.form(f"today_reading_{day.isoformat()}", clear_on_submit=True):
        labels = {book["id"]: book["title"] for book in current_books}
        book_id = st.selectbox("书籍", list(labels), format_func=labels.get)
        left, right = st.columns(2)
        minutes = left.number_input("分钟", min_value=1, value=30)
        pages = right.number_input("读了多少页", min_value=0, value=0)
        learned = st.text_area("今天读到什么值得记住？", height=90)
        saved = st.form_submit_button("保存阅读")
    if saved:
        add_reading_log(
            book_id, minutes, pages, learned, "", "", "",
            log_date=day,
        )
        st.success("阅读记录已保存")
        st.rerun()


def _journal_form(day: date, journal: dict) -> None:
    st.markdown('<div class="chapter"><div class="chapter-kicker">MY DAY</div></div>', unsafe_allow_html=True)
    with st.form(f"journal_page_{day.isoformat()}"):
        st.markdown("## ✍️ 今天发生了什么？")
        story = st.text_area(
            "日记正文",
            value=journal["day_story"],
            height=260,
            placeholder="自由地写。这里不需要结构，也不需要有结论。",
            label_visibility="collapsed",
        )

        st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)
        st.markdown("## 🧠 今天学到了什么？")
        learning = st.text_area(
            "学习记录",
            value=journal["learning_notes"],
            height=170,
            placeholder="今天有哪些真正理解了，而不是只是看过的东西？",
            label_visibility="collapsed",
        )
        technical = st.text_input(
            "今天最大的技术收获",
            value=journal["technical_gain"],
            placeholder="用一句话留下最值得复用的经验",
        )

        st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)
        st.markdown("## 🌿 今天的生活")
        life = st.text_area(
            "生活记录",
            value=journal["life_notes"],
            height=170,
            placeholder="不需要有意义，只记录今天真实发生的生活。",
            label_visibility="collapsed",
        )

        st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)
        st.markdown("## 💭 今天想明白了什么？")
        growth = st.text_area(
            "成长思考",
            value=journal["growth_thoughts"],
            height=170,
            label_visibility="collapsed",
        )
        reading_note = st.text_area(
            "今天读到什么值得记住？",
            value=journal["reading_note"],
            height=100,
        )
        ex_left, ex_right = st.columns([1, 3])
        exercise_minutes = ex_left.number_input(
            "运动分钟",
            min_value=0,
            value=int(journal["exercise_minutes"]),
        )
        exercise_content = ex_right.text_input(
            "运动内容",
            value=journal["exercise_content"],
            placeholder="散步、跑步、力量训练……",
        )

        st.markdown('<div class="chapter"><div class="chapter-kicker">END OF DAY</div></div>', unsafe_allow_html=True)
        st.markdown("## 🌙 晚上复盘")
        best = st.text_area("今天做得最好的一件事是什么？", value=journal["review_best"])
        problem = st.text_area("今天最大的问题是什么？", value=journal["review_problem"])
        gain = st.text_area("今天最大的收获是什么？", value=journal["review_gain"])
        tab_learning, tab_life, tab_self = st.tabs(["学习", "生活", "自己"])
        improvement_learning = tab_learning.text_area(
            "学习上还需要优化什么？",
            value=journal["improvement_learning"],
            key=f"improve_learning_{day}",
        )
        improvement_life = tab_life.text_area(
            "生活上还需要优化什么？",
            value=journal["improvement_life"],
            key=f"improve_life_{day}",
        )
        improvement_self = tab_self.text_area(
            "自己还需要调整什么？",
            value=journal["improvement_self"],
            key=f"improve_self_{day}",
        )
        tomorrow = st.text_area(
            "明天最重要的一件事情",
            value=journal["tomorrow_focus"],
        )
        self_message = st.text_area(
            "今天想给自己留一句什么？",
            value=journal["self_message"],
        )
        saved = st.form_submit_button("保存这一天", type="primary", use_container_width=True)
    if saved:
        saved_at = save_journal(
            day,
            {
                "day_story": story,
                "learning_notes": learning,
                "technical_gain": technical,
                "life_notes": life,
                "growth_thoughts": growth,
                "reading_note": reading_note,
                "exercise_minutes": exercise_minutes,
                "exercise_content": exercise_content,
                "review_best": best,
                "review_problem": problem,
                "review_gain": gain,
                "improvement_learning": improvement_learning,
                "improvement_life": improvement_life,
                "improvement_self": improvement_self,
                "tomorrow_focus": tomorrow,
                "self_message": self_message,
            },
        )
        st.success(f"✓ 已保存 · {saved_at[11:16]}")
        st.rerun()
    if journal["updated_at"]:
        st.markdown(
            f'<div class="saved-note">✓ 已保存 · {journal["updated_at"][11:16]}</div>',
            unsafe_allow_html=True,
        )


def _quick_notes(day: date) -> None:
    notes = list_quick_notes(day)
    st.markdown("## 💡 今天的灵感")
    if not notes:
        st.caption("侧边栏随时可以快速记下一句话。")
        return
    for note in notes:
        created_time = note["created_at"][11:16]
        with st.expander(f"{created_time} · {note['content'][:48]}"):
            content = st.text_area(
                "灵感内容",
                value=note["content"],
                key=f"quick_note_text_{note['id']}",
            )
            left, right = st.columns(2)
            if left.button("保存修改", key=f"quick_note_save_{note['id']}"):
                update_quick_note(note["id"], content)
                st.rerun()
            if right.button("删除", key=f"quick_note_delete_{note['id']}"):
                delete_quick_note(note["id"])
                st.rerun()


def _sleep_message(day: date) -> None:
    if day != date.today() or get_setting("sleep_reminder_enabled", "1") != "1":
        return
    sleep_hour, sleep_minute = map(int, get_setting("sleep_time", "23:00").split(":"))
    sleep_at = datetime.combine(day, time(sleep_hour, sleep_minute))
    now = datetime.now()
    if now >= sleep_at:
        st.error("🌙 今天到这里，去睡觉。")
    elif now >= sleep_at - timedelta(minutes=10):
        st.warning("放下高强度任务，准备洗漱。")
    elif now >= sleep_at - timedelta(minutes=30):
        st.info("今天差不多该收尾了。")


def render(selected_date: date | None = None, embedded: bool = False) -> None:
    day = selected_date or (_date_selector() if not embedded else date.today())
    if day >= date.today():
        materialize_daily_tasks(day.isoformat())
    journal = get_journal(day)
    if embedded:
        st.info(f"正在编辑 {day:%Y年%m月%d日}。保存只会更新这一天。")
    _header(day, journal)
    _direction_card()
    _timeline(day)
    st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)
    _habit_strip(day)
    _journal_form(day, journal)
    st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)
    _reading(day)
    st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)
    _quick_notes(day)
    _sleep_message(day)
