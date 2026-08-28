"""Streamlit 全页面冒烟测试，捕获重复控件键等运行时问题。"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from database import DB_PATH, init_database
from services.journal import save_journal


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

    navigation = next(item for item in app.radio if item.label == "导航")
    for page in ["📅 日记", "🎯 方向", "📚 阅读", "⚙️ 设置", "📖 今天"]:
        navigation.set_value(page)
        app.run()
        assert not app.exception, f"{page} 页面出现运行时异常"
        if page == "📅 日记":
            assert any(button.label == "编辑这一天" for button in app.button)
        navigation = next(item for item in app.radio if item.label == "导航")
