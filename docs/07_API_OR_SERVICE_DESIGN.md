# API / Service 设计

## 1. 当前边界

项目没有 HTTP API。Streamlit 页面与 Python service 函数运行在同一进程内。因此本文记录的是内部调用契约；未来若没有多端同步或外部集成需求，不必为了形式增加 REST API。

## 2. 数据访问基础

`database.py` 提供：

- `get_connection`：事务化 SQLite 连接；
- `init_database`：创建 Schema、兼容升级、首次种子数据；
- `fetch_all` / `fetch_one`：参数化读取；
- `execute` / `execute_many`：参数化写入；
- `get_setting` / `save_setting`：键值设置读写。

约束：页面和 service 不应自行创建未启用外键的连接；写操作发生 SQLite 异常时必须向上抛出并由 UI 展示失败。

`data_safety.py` 提供：

- `inspect_database`：只读执行完整性、外键和表检查；
- `create_database_backup`：使用 SQLite Backup API 创建并复查一致性备份；
- `default_backup_directory`：为真实库和测试库选择隔离备份目录。

`database.py` 的 `init_database` 只在发现待执行迁移时调用自动备份；普通启动不会重复生成备份。

## 3. 当前 Service 契约

### tasks.py

| 函数 | 责任 |
|---|---|
| `list_tasks` / `get_task` | 按日期、状态等条件读取任务 |
| `create_task` / `update_task` | 校验并保存一次性任务 |
| `complete_task` | 标记完成、完成度 100，并记录实际分钟和时间 |
| `postpone_task` | 修改计划日期并增加顺延次数 |
| `abandon_task` / `delete_task` | 放弃或物理删除任务 |
| `list_recurring_tasks` | 读取每日模板 |
| `create_daily_task` | 创建每日模板并物化当天实例 |
| `materialize_daily_tasks` | 幂等生成指定日期的启用模板实例 |
| `stop_recurring_task` | 停用模板，不删除历史实例 |

关键不变量：同一模板同一天最多一个任务；状态和完成度需要同步；用户输入时间必须为合法 `HH:MM`。

### habits.py

- `create_habit`：创建唯一名称习惯；
- `list_habits`：返回习惯及指定日期日志；
- `save_habit_log`：按习惯和日期更新或插入；
- `calculate_streak`：从今天向过去计算连续完成天数。

### books.py

- `add_reading_log`：保存阅读日志并更新书籍页数、分钟、状态。

当前缺口：书籍新增/编辑和列表管理位于页面 SQL 中，应逐步迁入 service，并统一“今日分钟”的计算口径。

### planner.py

- `assess_capacity`：比较可用分钟和计入容量的预计分钟；
- `build_today_advice`：根据任务与设置生成规则化建议；
- `find_main_task`：选择今日主任务。

它只输出建议，不应绕过用户自动删除、顺延或完成任务。

### stats.py

- `date_range`：生成统计日期范围；
- `task_summary`：任务数量、完成数量、完成率和分钟；
- `category_stats` / `category_minutes`：分类统计；
- `learning_streak`：学习类已完成任务的连续天数。

统计函数必须注明日期边界、状态和分钟来源；未来增加习惯/阅读统计时不得混用口径。

### reminder.py

- `collect_reminders`：按时间和未完成任务生成页面内提醒；
- `is_night_closing`：判断是否进入晚间收尾时段。

提醒函数是只读规则，不发送系统通知，也不应修改任务状态。

## 4. 页面直连数据库的现状

Goals、Review、Books 的部分逻辑直接调用 `fetch_*` 或 `execute`。短期可以工作，但新增以下功能前应建立独立 service：

- `goals_service`：目标 CRUD、归档、版本与快照；
- `journal_service`：日记/复盘保存、历史和搜索；
- `capture_service`：捕获、转换和归档；
- 完整 `books_service`：书籍管理、阅读统计。

## 5. 目标 Service 契约（规划，未实现）

### Quick Capture

```text
create_capture(content) -> capture_id
list_captures(status="inbox") -> captures
convert_capture(capture_id, target_type, target_data) -> target_id
archive_capture(capture_id) -> None
```

转换必须在事务内完成：目标记录创建成功后才标记捕获已处理，失败时原始内容保留。

### Daily Journal

```text
save_journal(entry_date, content, tags) -> entry_id
get_journal(entry_date) -> entry | None
list_journals(date_range, query) -> entries
```

同一天是否允许多篇需要在开发前确认。当前推荐一日一个主条目，快速捕获可多条关联。

### Goal History

```text
update_goal(goal_id, changes, reason) -> goal
list_goal_versions(goal_id) -> versions
archive_goal(goal_id, reason) -> None
```

目标主记录更新和版本快照必须在同一事务中完成。

## 6. 错误约定

- 输入错误：抛出 `ValueError` 或领域化校验错误，由页面转成友好提示。
- 数据冲突：明确指出唯一性冲突，例如习惯名或书名已存在。
- 数据库错误：保留原始异常链和操作上下文，但不在 UI 暴露敏感路径或 SQL。
- service 不吞异常，不返回“假成功”。

## 7. 如果未来增加 HTTP API

只有明确出现多端客户端、第三方集成或远程同步时再设计。届时 API 应调用现有 service，而不是复制业务规则；还需补齐认证、授权、并发冲突、隐私和版本契约。
