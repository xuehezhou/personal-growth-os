# 项目需求状态矩阵

状态定义：已实现＝代码存在且当前测试或运行证据支持；部分实现＝已有基础但未达到目标；未实现＝没有对应代码或数据结构。

| 模块 | 需求 | 当前状态 | 真实代码/数据位置 | 自动测试 |
|---|---|---|---|---|
| Today | 显示今日全部任务 | 已实现 | `pages/today.py`、`tasks` | ✅ |
| Today | 手动任务计入完成率 | 已实现 | `services/tasks.py`、`services/stats.py` | ✅ |
| Today | 上午/下午/晚上分组 | 已实现 | `pages/today.py` | ✅ 冒烟 |
| Planner | 容量预警 | 已实现 | `services/planner.py` | ✅ |
| Planner | 每天自动生成完整系统计划 | 部分实现 | 只有建议与首日示例；每日任务模板可生成实例 | ❌ |
| Tasks | 创建/编辑/完成/删除 | 已实现 | `pages/today.py`、`services/tasks.py` | ✅ 核心 |
| Tasks | 今日页同构规划明日并按日期查询历史/未来 | 已实现 | `pages/today.py`、`tasks.planned_date` | ✅ 核心 + UI 交互 |
| Tasks | 验收标准 | 已实现 | `services/tasks.py` | ✅ |
| Tasks | 每日重复任务 | 已实现 | `recurring_task_templates` | ✅ |
| Goals | 编辑方向字段 | 已实现 | `pages/goals.py`、`directions` | ✅ 冒烟 |
| Goals | 新增/编辑/完成/暂停 | 已实现 | `pages/goals.py`、`goals` | ✅ 冒烟 |
| Goals | 归档 | 未实现 | 无归档状态/UI | ❌ |
| Goal History | 保存当天方向快照 | 已实现 | `goal_snapshots`、`services/journal.py` | ✅ |
| Daily Review | 按日期保存复盘 | 已实现 | `pages/review.py`、`daily_reviews` | ✅ 冒烟 |
| Daily Journal | 一天一页完整生活记录 | 已实现 | `daily_journals`、`pages/today.py` | ✅ |
| Journal History | 浏览过去每天 | 已实现 | `pages/journal.py`，默认阅读模式 | ✅ 冒烟 |
| Quick Capture | 5–10 秒记录 | 已实现 | 侧边栏、`quick_notes`、`services/journal.py` | ✅ |
| Capture Inbox | 编辑/分类/转换 | 未实现 | 无 | ❌ |
| Books | 初始化分阶段书单 | 已实现 | `database.py`、`books` | ✅ |
| Books | 当前阅读和进度 | 已实现 | `pages/books.py`、`reading_logs` | ✅ |
| Books | 新增/删除/调整当前阅读 | 已实现 | `pages/books.py`、`services/books.py` | ✅ 冒烟 |
| Habits | 新增与每日打卡 | 已实现 | `pages/habits.py`、`habit_logs` | ✅ 部分 |
| Habits | 修改/停用/删除 | 未实现 | `active` 字段存在但无 UI | ❌ |
| Sleep | 可配置睡眠时间 | 已实现 | `pages/settings.py`、`settings` | ✅ 提醒规则 |
| Reminder | 应用内任务/复盘/睡眠提醒 | 已实现 | `services/reminder.py` | ✅ |
| Reminder | 应用关闭后提醒 | 未实现 | 无后台进程/系统通知 | ❌ |
| Light Stats | 最近 7 天日记/阅读/锻炼/任务 | 已实现 | `pages/journal.py`、`services/journal.py` | ✅ |
| Data | SQLite 持久化 | 已实现 | `data/growth.db` | ✅ |
| Data | Schema 版本与迁移前备份 | 已实现 | `database.py`、`schema_migrations`、`data_safety.py` | ✅ |
| Data | 设置页手工备份 | 已实现 | `pages/settings.py`、`backups/` | ✅ |
| Data | 一键恢复 | 未实现 | 当前按恢复文档手工执行 | ❌ |
| Search | 全局搜索 | 未实现 | 无 | ❌ |
| AI | AI 总结/计划/行为模式 | 未实现 | 当前为确定性规则 | ❌ |
