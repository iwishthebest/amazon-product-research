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

报告包含本地商品图、标题、ASIN、类目、Amazon 新品榜排名、价格、评分、评论数、机会评分、热度信号、评论竞争强度和改进方向，并支持按标题/ASIN、类目和热度筛选。报告会明确区分“本地首次发现”与 Amazon 实际上架日期，也不会把新品榜排名冒充销量；没有销量、BSR 历史或成本数据时，商品只标记为“未确认销量”。Amazon 页面拒绝图片请求时会显示占位卡片，不会伪造图片。

如果已经生成 JSON 快照但图片仍未解析，可先下载 Amazon `hiRes` 主图并重新渲染：

```powershell
python resolve_release_images.py `
  --snapshot data/reports/snapshot_YYYY-MM-DD.json `
  --new-products data/reports/new_products_YYYY-MM-DD.csv `
  --output-html data/reports/release_YYYY-MM-DD.html
```

## 合规边界

生产环境优先使用 Amazon 官方接口或有明确授权的数据服务。不要使用 Selenium/requests 绕过验证码、登录限制、访问控制或高并发抓取页面。若需要完整的目录新品，而不是新品榜上的排名商品，应进一步接入 SP-API Catalog Items 或合规的目录数据提供商。
