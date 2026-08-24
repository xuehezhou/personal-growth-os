# 项目需求状态矩阵

状态定义：已实现＝代码存在且当前测试或运行证据支持；部分实现＝已有基础但未达到目标；未实现＝没有对应代码或数据结构。

| 模块 | 需求 | 当前状态 | 真实代码/数据位置 | 自动测试 |
|---|---|---|---|---|
| Today | 显示今日全部任务 | 已实现 | `pages/today.py`、`tasks` | ✅ |
| Today | 手动任务计入完成率 | 已实现 | `services/tasks.py`、`services/stats.py` | ✅ |
| Today | 上午/下午/晚上分组 | 已实现 | `pages/today.py` | ✅ 冒烟 |
| Planner | 容量预警 | 已实现 | `services/planner.py` | ✅ |
| Planner | 每天自动生成完整系统计划 | 部分实现 | 只有建议与首日示例；每日任务模板可生成实例 | ❌ |
| Tasks | 创建/编辑/完成/延期/放弃/删除 | 已实现 | `pages/tasks.py`、`services/tasks.py` | ✅ 核心 |
| Tasks | 验收标准 | 已实现 | `services/tasks.py` | ✅ |
| Tasks | 每日重复任务 | 已实现 | `recurring_task_templates` | ✅ |
| Goals | 编辑方向字段 | 已实现 | `pages/goals.py`、`directions` | ✅ 冒烟 |
| Goals | 新增/编辑/完成/暂停 | 已实现 | `pages/goals.py`、`goals` | ✅ 冒烟 |
| Goals | 归档 | 未实现 | 无归档状态/UI | ❌ |
| Goal History | 保存方向和目标历史版本 | 未实现 | 无版本表 | ❌ |
| Daily Review | 按日期保存复盘 | 已实现 | `pages/review.py`、`daily_reviews` | ✅ 冒烟 |
| Daily Journal | 一天一页完整生活记录 | 部分实现 | `daily_reviews.free_text` 是基础 | ❌ |
| Journal History | 浏览过去每天 | 部分实现 | 日期选择可读取，但无历史列表/聚合页 | ❌ |
| Quick Capture | 5–10 秒记录 | 未实现 | 无页面/Service/表 | ❌ |
| Capture Inbox | 编辑/分类/转换 | 未实现 | 无 | ❌ |
| Books | 初始化分阶段书单 | 已实现 | `database.py`、`books` | ✅ |
| Books | 当前阅读和进度 | 已实现 | `pages/books.py`、`reading_logs` | ✅ |
| Books | 新增/删除/调整顺序 | 未实现 | 无 UI/Service | ❌ |
| Habits | 新增与每日打卡 | 已实现 | `pages/habits.py`、`habit_logs` | ✅ 部分 |
| Habits | 修改/停用/删除 | 未实现 | `active` 字段存在但无 UI | ❌ |
| Sleep | 可配置睡眠时间 | 已实现 | `pages/settings.py`、`settings` | ✅ 提醒规则 |
| Reminder | 应用内任务/复盘/睡眠提醒 | 已实现 | `services/reminder.py` | ✅ |
| Reminder | 应用关闭后提醒 | 未实现 | 无后台进程/系统通知 | ❌ |
| Dashboard | 7/30 天任务统计 | 已实现 | `pages/dashboard.py`、`services/stats.py` | ✅ 部分 |
| Dashboard | 合并阅读/习惯/日记数据 | 未实现 | 当前只聚合任务 | ❌ |
| Data | SQLite 持久化 | 已实现 | `data/growth.db` | ✅ |
| Data | 一键备份/恢复 | 未实现 | 仅 README 手工说明 | ❌ |
| Search | 全局搜索 | 未实现 | 无 | ❌ |
| AI | AI 总结/计划/行为模式 | 未实现 | 当前为确定性规则 | ❌ |

