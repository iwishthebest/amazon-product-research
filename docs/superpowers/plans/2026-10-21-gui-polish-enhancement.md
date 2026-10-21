# Amazon Release GUI Polish and Enhancement Plan

> **For agentic workers:** Execute the tasks inline with review checkpoints. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有可用 GUI 上完成一轮面向卖家客户的视觉升级和工作流增强，使采集、筛选、历史查看、导出和配置更易用。

**Architecture:** 保留现有 `run_gui_job` 和 Tkinter 桌面入口，在 GUI 模块中补充可测试的结果查询服务层（筛选、排序、历史、CSV 导出），再将它们接入重构后的 dashboard、商品工作台和设置面板。所有耗时采集继续放在后台线程，报告与 SQLite/JSON/CSV 协议保持兼容。

**Tech Stack:** Python 3.10+、Tkinter/ttk、标准库 `csv/json/pathlib/threading`、现有 pytest。

## Global Constraints

- 不引入重型 GUI 框架或外部网络资源；保持 `requirements.txt` 不变。
- 不改变现有采集、解析、SQLite、JSON、CSV、HTML 报告接口。
- 不能把新品榜排名或本地首次发现表述为确认销量。
- 所有新交互必须在无历史结果、空目录和离线 fixture 下可用。
- 保留工作区中原有未提交修改，不做无关重构。

---

### Task 1: 结果查询与导出服务

**Files:**
- Modify: `amazon_release/gui.py`
- Modify: `tests/test_gui.py`

**Interfaces:**
- `filter_product_rows(rows, query="", category="", new_only=False, min_score=0) -> list[dict]`
- `sort_product_rows(rows, key="score", descending=True) -> list[dict]`
- `discover_run_history(output_dir) -> list[dict]`
- `export_product_rows_csv(rows, output_path) -> Path`

- [x] 写筛选、排序、历史发现和导出失败测试，并确认测试先失败。
- [x] 实现纯函数，保证不修改传入的 rows。
- [x] 运行 GUI 聚焦测试确认通过。

### Task 2: 视觉系统与客户工作台布局

**Files:**
- Modify: `amazon_release/gui.py`
- Modify: `tests/test_gui.py`

- [x] 写 GUI smoke 测试，确认主题、主标题、导航和关键按钮在窗口创建后存在。
- [x] 增加统一色板、字体、按钮层级、状态徽章、卡片样式和分隔布局。
- [x] 将现有 Notebook 升级为“概览 / 商品工作台 / 运行历史 / 设置”四个清晰区域。
- [x] 增加可读的空状态、运行状态、结果更新时间和证据边界提示。
- [x] 将设置表单收进设置页，减少主界面拥挤。

### Task 3: 商品工作台增强

**Files:**
- Modify: `amazon_release/gui.py`
- Modify: `tests/test_gui.py`

- [x] 增加评分下限、排序字段、升降序控制和结果数量显示。
- [x] 增加商品详情侧栏，显示机会评分、排名、评价、竞争判断、改进建议和链接操作。
- [x] 增加“导出当前筛选 CSV”“复制 ASIN”“打开商品页”操作。
- [x] 保证筛选、排序、选择、刷新之间状态一致。

### Task 4: 历史、配置和交付验证

**Files:**
- Modify: `amazon_release/gui.py`
- Modify: `README.md`
- Modify: `tests/test_gui.py`

- [x] 历史页显示每次快照日期、商品数、HTML/CSV 是否存在，并支持打开报告。
- [x] 选择配置文件后加载可编辑参数；保存配置前做路径和数值校验。
- [x] 增加客户首次使用引导和常用操作说明。
- [x] 运行全量 pytest、Tk smoke、compileall、git diff --check，并记录尚存限制。
