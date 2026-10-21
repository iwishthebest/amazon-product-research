# Amazon AU New Releases Collector

这是一个面向 Amazon 澳洲站的 Python MVP，用于每日采集 `Pilates` 和 `Yoga` 新品榜页面，并输出首次发现的 ASIN。

默认分类：

- Pilates：`5044228051`
- Yoga：`5044231051`
- Marketplace：`A39IBJ37TRP1C6`

## 功能

- 自动发现 New Releases 页面中的分类链接；
- 遍历每个分类的分页；
- 提取 ASIN、标题、排名、链接、图片、价格、评分和评论数；
- SQLite 保存历史观测；
- 使用 `marketplace_id + asin` 全局去重；
- 将首次发现的商品导出为 CSV；
- 保存每日 JSON 快照；
- 支持本地 HTML fixture 离线运行，不访问 Amazon。

`first_seen_at` 表示本程序第一次观察到商品的时间，不等于 Amazon 的实际 listing 创建时间。New Releases 是排名列表，也不能保证覆盖分类下所有新建 ASIN。

## 安装

```powershell
python -m pip install -r requirements.txt
```

本项目的解析器使用 Python 标准库，`requests` 只在实时抓取模式下使用。

## 桌面 GUI（推荐给卖家客户）

双击 `start_gui.pyw`（或在项目目录运行 `python start_gui.py`）即可打开桌面工作台，不需要记命令行参数。GUI 提供：

- 配置文件、SQLite 数据库、输出目录和离线 fixture 的选择；
- 延迟、超时、重试、最大页数、分类深度及时区设置；
- 后台采集、运行状态、日志、停止请求和错误提示；
- 自动生成当天 HTML 选品报告，并在界面中查看商品数量、首次发现、高热度信号、类目数；
- 商品明细搜索、类目筛选、仅看首次发现、双击打开 Amazon 商品页；
- 保存配置、打开最新 HTML 报告和输出目录。

首次给客户演示时，勾选“使用离线 fixture（不联网）”，将 fixture 目录指向 `tests/fixtures`，点击“开始采集”即可验证完整流程。确认流程后取消勾选，再选择已获授权的数据访问方式进行在线采集。GUI 与命令行共用同一份 SQLite/JSON/CSV/HTML 数据，不会产生两套协议。

### GUI 工作台功能

新版 GUI 分为四个区域：

- **概览**：显示商品总数、首次发现、高热度信号和子类目数，并给出按机会评分排序的优先核验候选；
- **商品工作台**：支持标题/ASIN/类目搜索，评分下限，机会评分/排名/评论数/评分/标题排序，首次发现筛选，商品详情侧栏，复制 ASIN，打开商品页，以及导出当前筛选 CSV；
- **运行历史**：按日期查看快照、CSV 和 HTML 是否存在，双击或按钮打开指定日期的 HTML 报告；
- **设置**：集中管理配置、数据库、输出目录、fixture 和抓取参数，可加载与保存客户专用 JSON 配置。

界面会在无结果、无 HTML、空筛选和读取失败时显示可操作提示，不会把空数据误报为采集成功。商品详情中的机会评分、热度和改进建议仍然只是研究优先级信号，不能替代销量、利润和合规核验。

运行环境仍需先安装本项目依赖。若要分发为单文件 EXE，可在已安装 PyInstaller 的环境中执行 `pyinstaller --noconsole --onefile --name AmazonRelease start_gui.py`，并把 `config.example.json` 与 `tests/fixtures`（如需离线演示）放在 EXE 同目录。

## 离线验证

```powershell
python -m pytest -q --basetemp=.pytest-tmp
python run_amazon_release.py --help
```

## 实时运行

先复制并修改配置：

```powershell
Copy-Item config.example.json config.json
python run_amazon_release.py --config config.json
```

默认输出：

```text
data/amazon_release.sqlite3
data/reports/snapshot_YYYY-MM-DD.json
data/reports/categories_YYYY-MM-DD.json
data/reports/new_products_YYYY-MM-DD.csv
```

建议设置 `delay_seconds` 为 2 或更高，并根据 Amazon 条款和你的数据使用权限运行。程序不会绕过验证码、登录限制或其他访问控制。

## 离线 fixture 模式

```powershell
python run_amazon_release.py `
  --config config.example.json `
  --fixture-dir tests/fixtures `
  --db .tmp/amazon_release.sqlite3 `
  --output-dir .tmp/reports
```

fixture 文件名按分类节点命名，例如：

```text
category_5044228051.html
category_5044228051_page2.html
```

## 每日调度

Windows 任务计划程序可以每天执行：

```text
Program: python.exe
Arguments: C:\path\to\AmazonRelease\run_amazon_release.py --config C:\path\to\AmazonRelease\config.json
Start in: C:\path\to\AmazonRelease
```

## 图文 HTML 报告

将当天 JSON 快照渲染为按分类分组的商品卡片报告：

```powershell
python render_release_report.py `
  --snapshot data/reports/snapshot_YYYY-MM-DD.json `
  --new-products data/reports/new_products_YYYY-MM-DD.csv `
  --date YYYY-MM-DD `
  --output data/reports/release_YYYY-MM-DD.html
```

报告包含本地商品图、标题、ASIN、类目、Amazon 新品榜排名、价格、评分、评论数、机会评分、热度信号、评论竞争强度和改进方向，并支持卡片视图/竞品对比表切换、表头排序、标题/ASIN搜索、类目/热度/首次发现筛选。报告会明确区分“本地首次发现”与 Amazon 实际上架日期，也不会把新品榜排名冒充销量；没有销量、BSR 历史或成本数据时，商品只标记为“未确认销量”。Amazon 页面拒绝图片请求时会显示占位卡片，不会伪造图片。

如果已经生成 JSON 快照但图片仍未解析，可先下载 Amazon `hiRes` 主图并重新渲染：

```powershell
python resolve_release_images.py `
  --snapshot data/reports/snapshot_YYYY-MM-DD.json `
  --new-products data/reports/new_products_YYYY-MM-DD.csv `
  --output-html data/reports/release_YYYY-MM-DD.html
```

## 合规边界

生产环境优先使用 Amazon 官方接口或有明确授权的数据服务。不要使用 Selenium/requests 绕过验证码、登录限制、访问控制或高并发抓取页面。若需要完整的目录新品，而不是新品榜上的排名商品，应进一步接入 SP-API Catalog Items 或合规的目录数据提供商。
