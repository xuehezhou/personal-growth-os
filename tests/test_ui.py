"""Streamlit 全页面冒烟测试，捕获重复控件键等运行时问题。"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def test_all_navigation_pages_render_without_exception() -> None:
    app = AppTest.from_file(str(APP_PATH), default_timeout=10).run()
    assert not app.exception

    navigation = app.radio[0]
    for page in ["目标与方向", "任务", "阅读", "习惯", "复盘", "数据统计", "设置", "今日"]:
        navigation.set_value(page)
        app.run()
        assert not app.exception, f"{page} 页面出现运行时异常"
        navigation = app.radio[0]

