# 数据、备份与恢复

## 1. 数据范围

主数据库是：

```text
data/growth.db
```

其中包含设置、方向、目标、任务、每日模板、习惯与日志、书籍与阅读日志、每日复盘。备份文件与原文件同样敏感。

## 2. 基本原则

- 升级代码或 Schema 前先备份。
- 备份时先停止 Streamlit，避免复制正在写入的文件。
- 保留至少一个不与工作目录同盘的副本。
- 不把真实数据库提交到 Git 或公开云盘。
- 恢复前先备份当前现场，不直接覆盖唯一副本。

## 3. Windows 手工备份

推荐方式是在“设置 → 数据安全”点击“创建数据库备份”。系统会使用 SQLite Backup API 创建一致性副本，并自动执行完整性检查；应用运行时也可以安全使用。

如需完全手工复制，先在运行 Streamlit 的终端按 `Ctrl+C` 停止应用，然后在项目目录执行：

```powershell
New-Item -ItemType Directory -Force -Path .\backups
Copy-Item -LiteralPath .\data\growth.db -Destination .\backups\growth-2026-08-24.db
```

把日期替换为实际备份日期。若同一天可能备份多次，可在名称中加入时分。完成后确认目标文件存在且大小大于 0。

`backups/` 仍位于项目磁盘，只能防误修改，不能防硬盘故障。重要数据应再复制到用户控制的加密位置。

## 4. 备份验证

不要只确认文件“复制成功”。建议使用副本启动一次测试环境，或至少运行 SQLite 完整性检查：

```powershell
python -c "import sqlite3; c=sqlite3.connect(r'backups\growth-2026-08-24.db'); print(c.execute('PRAGMA integrity_check').fetchone()[0]); c.close()"
```

输出 `ok` 说明 SQLite 文件结构通过基本检查，但不代表所有业务内容都已人工核对。

## 5. 恢复流程

1. 停止 Streamlit。
2. 确认要恢复的备份文件路径、日期和文件大小。
3. 把当前 `data/growth.db` 复制为一份“恢复前现场”备份。
4. 将选定备份复制到 `data/growth.db`。
5. 启动应用，检查目标、任务、习惯和复盘等关键内容。
6. 运行自动化测试；测试仍须使用临时数据库，不能改写恢复后的文件。

示例复制命令中的文件名必须按实际情况替换：

```powershell
Copy-Item -LiteralPath .\data\growth.db -Destination .\backups\growth-before-restore.db
Copy-Item -LiteralPath .\backups\growth-2026-08-24.db -Destination .\data\growth.db -Force
```

`-Force` 会覆盖目标文件，所以只应在完成前两步核对和现场备份后使用。

## 6. 代码升级与数据库迁移

当前应用使用 `schema_migrations` 记录版本。有待执行迁移时，会先检查原数据库并在 `backups/` 自动创建迁移前备份。每次数据库结构变更仍应遵守：

```text
备份真实数据库
→ 在副本上执行升级
→ 检查表结构、行数、外键和应用启动
→ 运行回归测试
→ 再升级真实数据库
```

升级脚本应幂等，不能依靠清空数据库解决兼容问题。

## 7. 数据导出状态

当前没有完整的 UI 导出功能。直接复制 SQLite 是最完整的备份方式。CSV/Markdown/JSON 导出属于路线图能力；在实现前，不应把截图或统计页当作完整备份。

## 8. 故障处理

如果遇到 `database is locked`、`disk I/O error` 或损坏提示：

- 停止写操作并保存完整报错；
- 不要删除数据库、缓存或重装项目；
- 复制原文件保留现场；
- 检查磁盘空间、占用进程和文件权限；
- 在副本上执行 `PRAGMA integrity_check`；
- 只有确认备份有效后再恢复。
