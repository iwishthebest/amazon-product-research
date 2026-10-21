# Amazon Release GUI Version Implementation Plan

> **For agentic workers:** Execute the tasks inline with review checkpoints. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 Amazon AU 新品采集与卖家分析能力封装为无需命令行的可视化桌面软件，客户可配置、运行、查看结果并导出报告。

**Architecture:** 使用 Python 标准库 Tkinter 构建 Windows 桌面 GUI，复用现有 `amazon_release.cli.run_once`、配置与报告产物，不改动抓取/解析/存储协议。耗时采集在线程中运行，主线程只负责界面更新；结果区读取 JSON/CSV 并以表格展示，HTML 报告可在系统浏览器打开。

**Tech Stack:** Python 3.10+、Tkinter、`threading`、现有 `requests`/SQLite/HTML 报告模块、pytest。

## Global Constraints

- 保持现有 CSV/JSON/SQLite 输出兼容。
- GUI 默认支持离线 fixture 运行，禁止绕过验证码、登录限制或访问控制。
- 所有网络运行在后台线程，界面始终可响应并提供停止请求。
- 结果中的“首次发现/热度”继续遵守现有证据边界，不声称销量。
- 不额外引入重型 GUI 依赖；保持 `requirements.txt` 可直接安装。

---

### Task 1: GUI 可测试的配置与运行服务

**Files:**
- Create: `amazon_release/gui.py`
- Create: `tests/test_gui.py`
- Modify: `run_amazon_release.py`

**Interfaces:**
- `build_gui_config(values: dict) -> dict`：将表单值转换为 `cli.run_once` 可用配置。
- `run_gui_job(config, fixture_dir, db_path, output_dir, dry_run=False) -> dict`：薄封装现有 `run_once`。
- `main()`：创建 `AmazonReleaseApp` 并启动 Tk 主循环。

- [x] 写失败测试：验证空路径/页数校验、配置转换、运行服务返回现有结果字段。
- [x] 运行 `python -m pytest tests/test_gui.py -q`，确认因模块/函数不存在而失败。
- [x] 实现配置转换、后台作业服务与最小 GUI 启动入口。
- [x] 再运行聚焦测试，确认通过。

### Task 2: 完整卖家工作台界面

**Files:**
- Modify: `amazon_release/gui.py`
- Modify: `tests/test_gui.py`

- [x] 写失败测试：结果目录扫描能找到最新快照/CSV/HTML，表格行模型能从快照构造标题、ASIN、评分和热度。
- [x] 实现“项目设置”区（配置文件、数据库、输出目录、fixture 开关、页数/延迟/超时、干跑）。
- [x] 实现“开始采集/停止请求/打开输出目录/打开 HTML 报告/保存配置”按钮。
- [x] 实现后台线程、进度状态、日志窗口、错误弹窗和完成摘要。
- [x] 实现结果标签页：指标卡、商品表格、关键词搜索、类目筛选、仅首次发现筛选、双击打开 Amazon 链接。
- [x] 运行 GUI 聚焦测试和全量 pytest。

### Task 3: 客户可用入口、文档与验证

**Files:**
- Modify: `README.md`
- Modify: `config.example.json`
- Create: `start_gui.py`

- [x] 增加双击/命令行启动说明、首次使用流程、在线/离线模式和合规提示。
- [x] 添加稳定的 `python start_gui.py` 入口，工作目录不正确时仍能定位项目包。
- [x] 运行 `python -m compileall -q amazon_release start_gui.py`、`python -m pytest -q --basetemp=.pytest-tmp-gui` 和离线 GUI 服务验收。
- [x] 检查 `git diff --check`，确认无未验证成功表述或无关文件变更。
