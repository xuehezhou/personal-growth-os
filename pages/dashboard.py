"""7/30 天成长统计。"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from pages.common import minutes_text, page_header
from services.stats import category_minutes, category_stats, learning_streak, task_summary


def render() -> None:
    page_header("数据统计", "观察时间投向，而不是只看忙碌程度。")
    days = st.segmented_control("统计范围", options=[7, 30], default=7, format_func=lambda value: f"过去 {value} 天")
    days = int(days or 7)
    summary = task_summary(days)
    metrics = st.columns(6)
    metrics[0].metric("任务完成率", f"{summary['completion_rate']}%")
    metrics[1].metric("实际投入", minutes_text(summary["actual_minutes"]))
    metrics[2].metric("项目实战", minutes_text(category_minutes("项目实战", days)))
    metrics[3].metric("阅读", minutes_text(category_minutes("阅读", days)))
    metrics[4].metric("锻炼", minutes_text(category_minutes("锻炼", days)))
    metrics[5].metric("连续学习", f"{learning_streak()} 天")

    data = category_stats(days)
    st.markdown("### 成长领域分布")
    if not data:
        st.info("还没有已完成任务的实际投入数据。完成任务并记录实际分钟后，这里会出现统计。")
        return
    frame = pd.DataFrame(data)
    total = frame["minutes"].sum()
    frame["占比"] = (frame["minutes"] / total * 100).round(1)
    frame["小时"] = (frame["minutes"] / 60).round(1)
    left, right = st.columns([2, 1])
    left.bar_chart(frame.set_index("category")["minutes"], color="#40916c")
    right.dataframe(
        frame[["category", "小时", "占比"]].rename(columns={"category": "成长领域"}),
        hide_index=True,
        use_container_width=True,
    )

