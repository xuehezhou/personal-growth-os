"""Streamlit 全页面冒烟测试，捕获重复控件键等运行时问题。"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from streamlit.testing.v1 import AppTest

from database import DB_PATH, init_database
from services.journal import save_journal
from services.tasks import list_tasks


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def test_all_navigation_pages_render_without_exception() -> None:
    init_database(DB_PATH)
    save_journal(
        "2026-08-28",
        {
            "mood": "🙂 不错",
            "focus": "完成 Study Diary 页面验收",
            "day_story": "这是一条隔离测试数据库中的历史日记。",
        },
        DB_PATH,
    )
    app = AppTest.from_file(str(APP_PATH), default_timeout=10).run()
    assert not app.exception

    assert any(item.label == "日期查询" for item in app.date_input)
    assert any(button.label == "明日安排" for button in app.button)
    next(button for button in app.button if button.label == "明日安排").click()
    app.run()
    selected_date = next(item for item in app.date_input if item.label == "日期查询")
    assert selected_date.value == date.today() + timedelta(days=1)

    next(item for item in app.text_input if item.label == "任务名称").set_value(
        "明天的界面验收计划"
    )
    next(button for button in app.button if button.label == "加入明天计划").click()
    app.run()
    assert any(
        task["title"] == "明天的界面验收计划"
        for task in list_tasks(selected_date.value.isoformat(), db_path=DB_PATH)
    )
    assert not app.exception

    selected_date = next(item for item in app.date_input if item.label == "日期查询")
    selected_date.set_value(date.today() - timedelta(days=1))
    app.run()
    historical_date = next(item for item in app.date_input if item.label == "日期查询")
    assert historical_date.value == date.today() - timedelta(days=1)
    assert not app.exception

    navigation = next(item for item in app.radio if item.label == "导航")
    for page in ["📅 日记", "🎯 方向", "📚 阅读", "⚙️ 设置", "📖 今天"]:
        navigation.set_value(page)
        app.run()
        assert not app.exception, f"{page} 页面出现运行时异常"
        if page == "📅 日记":
            assert any(button.label == "编辑这一天" for button in app.button)
        navigation = next(item for item in app.radio if item.label == "导航")
