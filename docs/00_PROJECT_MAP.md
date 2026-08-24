# Personal Growth OS 项目地图

> Personal Growth OS 是一个把人生方向、每天行动和长期记录放在同一处的本地个人操作系统。

## 一条最容易理解的主线

```text
我
↓
打开“今日”
↓
确认方向和最重要任务
↓
安排并执行任务
↓
记录习惯、阅读和生活情况
↓
晚上复盘
↓
数据进入 SQLite 历史
↓
每周看统计并调整方向
```

目标形态还会加入：

```text
随时产生想法 → Quick Capture → 灵感箱 → 整理成任务 / 日记 / 目标
```

这条灵感链路当前尚未实现。

## 当前目录地图

```text
app.py                    应用入口、导航、样式、数据库初始化
database.py               Schema、默认数据、连接与通用查询
data_safety.py            SQLite 完整性检查与一致性备份
models.py                 分类、状态、时间段和容量常量
pages/                    8 个用户页面
services/                 任务、计划、统计、提醒、习惯、阅读规则
data/growth.db            用户真实数据
backups/                  迁移前与手工备份，不提交 Git
tests/                    核心业务与全页面冒烟测试
.streamlit/config.toml    本地监听和主题
docs/                     产品、技术、使用和决策文档
```

## 模块说明

### Today / 今日

- 干什么：显示今天最重要的任务、完成率、时间段、建议、提醒和习惯。
- 为什么需要：用户打开应用后不必在多个页面寻找“现在该做什么”。
- 数据从哪里来：`tasks`、`directions`、`habits`、`habit_logs`、`settings`。
- 保存到哪里：快速新增写入 `tasks` 或 `recurring_task_templates`；打卡写入 `habit_logs`。
- 关联模块：Goals、Tasks、Habits、Dashboard、Reminder。
- 什么时候用：早上规划、白天执行、晚上收尾。

### Goals / 目标与方向

- 干什么：记录长期方向、阶段目标、主要矛盾、当前优先和暂时不做。
- 为什么需要：防止每天很忙，却不知道自己在往哪里走。
- 数据从哪里来：用户输入；当前首启也会提供可编辑示例。
- 保存到哪里：`directions`、`goals`。
- 关联模块：Tasks、Planner、Today。
- 什么时候用：阶段开始、每周检查、方向变化时。
- 现状限制：没有历史版本，修改方向会覆盖旧值。

### Tasks / 任务

- 干什么：创建、编辑、完成、延期、放弃和管理每日重复任务。
- 为什么需要：把目标变成可验收的行动。
- 数据从哪里来：用户输入、首次示例计划、每日任务模板。
- 保存到哪里：`tasks`、`recurring_task_templates`。
- 关联模块：Today、Goals、Dashboard、Reminder。
- 什么时候用：安排具体行动和处理未完成任务时。

### Habits / 习惯

- 干什么：记录每天重复的行为和连续完成天数。
- 为什么需要：任务关注“今天做成什么”，习惯关注“长期是否稳定”。
- 数据从哪里来：默认建议和用户新增。
- 保存到哪里：`habits`、`habit_logs`。
- 关联模块：Today、Dashboard（目前只间接关联）。
- 什么时候用：每日打卡和检查连续性。

### Books / 阅读

- 干什么：维护当前阅读状态、页数、时间和轻量反思。
- 为什么需要：避免只收藏书，不形成认知和应用。
- 数据从哪里来：17 本推荐初始化书单和用户阅读记录。
- 保存到哪里：`books`、`reading_logs`。
- 关联模块：Habits、Today、Dashboard（目前统计未直接使用日志）。
- 什么时候用：开始一本书、每次阅读后、回顾笔记时。

### Review / 复盘

- 干什么：按日期记录发生的事、学习/生活问题、成长思考和明日调整。
- 为什么需要：把经历转化为下一天的选择。
- 数据从哪里来：用户自由填写。
- 保存到哪里：`daily_reviews`。
- 关联模块：Today、未来 Journal、未来 Dashboard。
- 什么时候用：每天晚上。
- 现状限制：它是“复盘页”，不是完整 Daily Journal。

### Dashboard / 数据统计

- 干什么：看 7/30 天完成率、投入时间、分类分布和连续学习。
- 为什么需要：用真实行为检查注意力分配。
- 数据从哪里来：当前主要来自 `tasks`。
- 保存到哪里：不单独保存，实时聚合。
- 关联模块：Tasks；未来应整合 Books、Habits、Journal。
- 什么时候用：每周或每月检查。

### Reminder / 提醒

- 干什么：检查即将开始、已超时、复盘和睡眠时间。
- 为什么需要：计划如果没有执行反馈，很容易失效。
- 数据从哪里来：`tasks` 和 `settings`。
- 保存到哪里：设置保存在 `settings`；提醒本身不保存。
- 关联模块：Today、Settings。
- 什么时候用：应用打开期间。

### Settings / 设置

- 干什么：修改任务提前提醒、复盘提醒和睡眠时间。
- 为什么需要：睡眠时间应由用户配置，不能写死。
- 数据从哪里来：默认值和用户修改。
- 保存到哪里：`settings`。
- 关联模块：Reminder、Today。
- 什么时候用：首次使用或作息变化时。

### Journal / 日记（目标模块，未完整实现）

- 目标：一天一页，聚合计划、实际发生、学习、生活、灵感和复盘。
- 当前基础：`daily_reviews.free_text` 可写自由日记，但没有 Journal 页面和历史聚合。

### Quick Capture / 灵感闪现（未实现）

- 目标：5–10 秒记录想法，默认进入 Inbox，之后再分类或转换。
- 当前状态：没有页面、Service 或数据表。

## 数据主链路

```text
用户操作
↓
Streamlit 页面
↓
Service（部分模块）或 database.py（部分页面直连）
↓
参数化 SQL
↓
data/growth.db
↓
页面重新查询并显示
```

## 文档导航

- 先看现状：[CURRENT_PROJECT_AUDIT.md](CURRENT_PROJECT_AUDIT.md)
- 看产品方向：[01_PRODUCT_VISION.md](01_PRODUCT_VISION.md)
- 看正式需求：[02_PRD.md](02_PRD.md)
- 看完成状态：[REQUIREMENTS_STATUS.md](REQUIREMENTS_STATUS.md)
- 看代码结构：[05_ARCHITECTURE.md](05_ARCHITECTURE.md)
- 看数据表：[06_DATABASE_DESIGN.md](06_DATABASE_DESIGN.md)
- 每天怎么用：[11_USER_GUIDE.md](11_USER_GUIDE.md)
