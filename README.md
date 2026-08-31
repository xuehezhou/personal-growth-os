# Study Diary

Study Diary 是一本本地运行的数字日记：一天一页，把计划、学习、生活、阅读、运动、灵感和晚上复盘自然地放在同一天里。界面使用 Streamlit，数据保存在本机 SQLite 文件中。

## 当前可用能力

- 今天：状态、方向、唯一 Focus、时间轴任务、自由日记、学习、生活、成长思考、阅读、运动和晚上复盘；
- 今日计划：顶部可切换“今日计划”“明日安排”，也可按日期查询过去或未来；切换后复用完全相同的一天一页界面，所有内容按所选日期保存；
- 日记：月份切换、最近记录、默认阅读模式、历史日期按需编辑和最近 7 天轻统计；
- 方向：长期目标、当前阶段、当前目标、主要矛盾、优先事项和暂时不做，完全由用户填写；
- 灵感：侧边栏一条输入即可保存，Today 可编辑和删除；
- 阅读：推荐书单、用户新增、当前阅读、进度、每日记录和确认删除；
- 设置与提醒：睡眠时间、页面内提醒、数据库健康检查与手工备份。
- 数据安全：版本化数据库迁移、升级前自动备份、完整性检查和手工备份。

当前没有复杂 Inbox 转换、系统级通知或云同步。详细状态见 [需求实现状态](docs/REQUIREMENTS_STATUS.md)。

## 技术栈

- Python 3.11+
- Streamlit
- SQLite
- pandas
- pytest

## 项目结构

```text
personal-growth-os/
├─ app.py              # 应用入口和导航
├─ pages/              # 今天、日记、方向、阅读、设置 5 个页面
├─ services/           # 任务、规划、统计、提醒等业务规则
├─ database.py         # SQLite Schema、事务和初始化
├─ data_safety.py      # 数据库检查与一致性备份
├─ models.py           # 状态常量与容量数据模型
├─ data/growth.db      # 本地真实数据，不提交 Git
├─ tests/              # 核心与页面烟雾测试
├─ backups/            # 本地备份，不提交 Git
└─ docs/               # 产品和工程文档基线
```

新手建议先读 [项目地图](docs/00_PROJECT_MAP.md)，开发者再读 [系统架构](docs/05_ARCHITECTURE.md) 和 [数据库设计](docs/06_DATABASE_DESIGN.md)。

## 安装与启动（Windows PowerShell）

当前本机项目目录为 `D:\All chatgtp\Study-diary`。在 Windows PowerShell 中运行：

```powershell
cd "D:\All chatgtp\Study-diary"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

浏览器打开 `http://127.0.0.1:8501/`。停止应用时，在运行终端按 `Ctrl+C`。

也可以运行项目根目录的 `launch_study_diary.ps1`。桌面快捷方式会调用这个启动器：服务未运行时在后台启动，启动成功后自动打开浏览器；服务已运行时直接打开页面。启动日志保存在本地 `logs/` 目录且不会提交 Git。

如果不使用虚拟环境：

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## 每天怎么用

1. 打开“今天”，写下状态和唯一 Focus。
2. 在“今天”顶部点击“明日安排”提前规划明天，或通过日期查询回看和调整过去的安排。
3. 加入今天的时间安排，白天随手完成任务、记录灵感和阅读。
4. 在 My Day 自由写学习、生活和成长思考。
5. 晚上完成 End of Day，点击“保存这一天”。
6. 在“日记”中以阅读模式翻看过去。

“每天保持 8 小时睡眠”可以既是每日任务，也是 480 分钟目标的习惯：前者记录当天承诺，后者观察长期稳定性。操作示例见 [用户指南](docs/11_USER_GUIDE.md)。

## 数据与备份

真实数据默认位于：

```text
data/growth.db
```

它包含目标、任务、习惯、阅读和复盘，属于敏感个人数据。升级或恢复前请停止应用并先复制备份。完整流程见 [数据、备份与恢复](docs/12_DATA_AND_BACKUP.md)。

## 运行测试

```powershell
python -m pytest -q -p no:cacheprovider --basetemp tests/runtime
```

测试必须使用临时数据库，不能清空或替换 `data/growth.db`。

## 文档入口

- [当前项目审计](docs/CURRENT_PROJECT_AUDIT.md)
- [产品愿景](docs/01_PRODUCT_VISION.md)
- [PRD](docs/02_PRD.md)
- [用户流程](docs/03_USER_FLOW.md)
- [UI / UX 规格](docs/04_UI_UX_SPEC.md)
- [系统架构](docs/05_ARCHITECTURE.md)
- [数据库设计](docs/06_DATABASE_DESIGN.md)
- [Service 设计](docs/07_API_OR_SERVICE_DESIGN.md)
- [开发计划](docs/08_DEVELOPMENT_PLAN.md)
- [测试计划](docs/09_TEST_PLAN.md)
- [路线图](docs/10_ROADMAP.md)
- [关键决策](docs/14_DECISIONS.md)

## 当前版本定位

当前是 Study Diary 0.3：一天一页的核心记录链路已经可用，数据库具备按日期隔离、方向快照、迁移前自动备份和完整性检查，当前 Schema 为 v4。

## 遇到问题时提供什么

请提供完整命令、从 `Traceback` 开始的完整报错、`python --version`、操作页面和预期结果。不要发送密码、Token、Cookie、私人日记内容或真实数据库。
