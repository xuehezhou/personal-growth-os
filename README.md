# Personal Growth OS

Personal Growth OS 是一个本地运行的个人成长管理应用，把目标、任务、每日习惯、阅读和复盘连接成日常执行闭环。界面使用 Streamlit，数据保存在本机 SQLite 文件中。

## 当前可用能力

- 今日页：主任务、今日任务、容量判断、规则建议和快速创建任务；
- 任务：创建、编辑、完成、顺延、放弃、删除，以及每日任务模板；
- 目标：长期方向和长期/阶段/周目标基础管理；
- 习惯：新增习惯、每日打卡、分钟和连续天数；
- 阅读：书单进度、阅读分钟、页数和收获记录；
- 复盘：一日一条结构化复盘；
- 统计：任务完成、分类投入和学习连续天数；
- 设置与提醒：容量、提醒时间和应用页面内提醒。
- 数据安全：版本化数据库迁移、升级前自动备份、完整性检查和手工备份。

当前还没有 Quick Capture 收件箱、完整 Daily Journal 历史、Goal History、系统通知或云同步。详细状态见 [需求实现状态](docs/REQUIREMENTS_STATUS.md)。

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
├─ pages/              # 8 个当前页面
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

如果不使用虚拟环境：

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## 每天怎么用

1. 早晨打开“今日”，确认真正的主任务和当天容量。
2. 白天完成、顺延任务，并记录习惯和阅读。
3. 晚上填写“复盘”，留下事实、收获、问题和明日主任务。
4. 每周查看统计，调整任务数量和时间分配。

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

当前是 V0.2 数据安全基线：核心日常功能可以运行，数据库已具备版本记录、迁移前自动备份和完整性检查。V1.0 只有在真实连续使用至少 7 天且没有关键数据丢失后才成立。

## 遇到问题时提供什么

请提供完整命令、从 `Traceback` 开始的完整报错、`python --version`、操作页面和预期结果。不要发送密码、Token、Cookie、私人日记内容或真实数据库。
