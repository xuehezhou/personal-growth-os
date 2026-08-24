"""Personal Growth OS 的领域常量与轻量数据模型。"""

from __future__ import annotations

from dataclasses import dataclass


CATEGORIES = [
    "AI技术",
    "项目实战",
    "Git/GitHub",
    "Debug",
    "部署",
    "数据库",
    "RAG",
    "Agent",
    "商业",
    "金融",
    "阅读",
    "表达",
    "英语",
    "锻炼",
    "个人事务",
    "生活",
    "社交 / 人际",
    "整理 / 家务",
    "休息 / 娱乐",
    "成长思考",
]

PRIORITIES = ["主任务", "重要", "普通", "低"]
TIME_SLOTS = ["上午", "下午", "晚上", "全天"]
TASK_STATUSES = ["待开始", "进行中", "已完成", "已放弃"]


@dataclass(frozen=True)
class PlanCapacity:
    """每日可执行容量，单位为分钟。"""

    deep_work_minutes: int = 300
    learning_project_minutes: int = 360
    total_minutes: int = 600

