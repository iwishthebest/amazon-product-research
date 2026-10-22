# AmazonRelease：美国站 + 澳洲站竞品选品 MVP 实施基线

> 状态：MVP 基线 v0.1
>
> 已确认：目标平台为 Amazon；目标站点为美国站（US）和澳洲站（AU）；客户独立部署；最终用户以 Mac 电脑为主；本期先做 MVP。
>
> 待补充：`AmazonRelease` 项目中的目标类目、关键词种子和类目节点。当前工作区未发现该项目文件，因此本文不臆造具体类目。

## 1. 产品定位与边界

本项目交付一套部署在客户自有服务器上的 Amazon 竞品分析与选品决策 Web 应用。最终用户使用 Mac 电脑上的 Safari 或 Chrome 浏览器访问，不要求安装 macOS 原生客户端。第一版围绕“发现商品—查看竞品—估算利润—排序筛选—导出结果”形成闭环。

### MVP 必须实现

1. US/AU 两个 marketplace 切换，站点、货币、时区、接口区域独立配置。
2. 关键词搜索、ASIN 查询、CSV/Excel 批量导入。
3. 商品列表：ASIN、标题、主图、类目、价格、评分、评论数、BSR/销售排名、数据更新时间和来源。
4. 商品详情：当前价格、历史价格、历史销售排名、评论/评分变化、竞品对比。
5. 销量字段分级展示：真实订单数据、供应商估算、不可用；禁止将估算值显示为真实销量。
6. 利润测算：售价、采购价、头程物流、FBA/平台费用、包装、广告、退货损耗、税费等可编辑参数。
7. 规则评分、排序、筛选、收藏、备注和 CSV/XLSX 导出。
8. 手动刷新、任务状态、限流/授权/数据缺失提示。
9. 客户单机或单服务器独立部署，不做多租户、支付和订阅。

### 本期明确不做

- 自动上架、自动调价、广告投放、自动采购。
- 未经授权的大规模网页爬取。
- 复杂机器学习销量预测和“成功概率”承诺。
- macOS 原生客户端、原生手机 App；前端采用适配 Mac 浏览器的桌面优先响应式 Web。
- 竞品真实净利润推断。竞品采购价未知时，只能计算“按用户输入成本参数的情景利润”。

## 2. 两站点配置基线

| 配置项 | 美国站 | 澳洲站 |
|---|---|---|
| marketplace code | US | AU |
| Amazon marketplace ID | `ATVPDKIKX0DER` | `A39IBJ37TRP1C6` |
| Amazon 前台 | `amazon.com` | `amazon.com.au` |
| Seller Central | `sellercentral.amazon.com` | `sellercentral.amazon.com.au` |
| SP-API 区域端点 | `sellingpartnerapi-na.amazon.com` | `sellingpartnerapi-fe.amazon.com` |
| 默认币种 | USD | AUD |
| 默认语言 | en-US | en-AU |
| 时区 | America/Los_Angeles（可配置） | Australia/Sydney（可配置） |
| 费率/税费 | 独立配置，不写死 | 独立配置，不写死 |

Keepa 的 marketplace/domain 编号不要凭经验硬编码；在数据源验证脚本中通过供应商文档和实际 ASIN 请求确认 US/AU 映射，并将结果写入 `source_config`。所有历史值保存 `marketplace`、`currency`、`source` 和 `fetched_at`。

## 3. 数据源策略

## 3.1 Mac 用户适配与部署边界

- 客户服务器仍建议使用 Linux + Docker Compose；Mac 只是访问端，不承担数据库、API 密钥和数据同步任务。
- 支持 Safari 最新稳定版和 Chrome 最新稳定版；页面最低按 1440×900 桌面窗口设计，并兼容 1280×800。
- 导出文件使用 CSV/XLSX，确保可在 macOS 的 Excel、Numbers 或 LibreOffice 中打开。
- 不在 MVP 阶段打包 `.dmg`。如果后续必须离线或本地运行，再单独评估 Tauri/Electron、macOS 签名、公证和自动更新。
- API 密钥只保存在客户服务器端，不能写入浏览器 localStorage，也不能打包进前端。

## 3.2 推荐组合

1. **Keepa：主验证候选**。用于商品基础信息、价格历史、销售排名、报价/Buy Box、评论与评分历史，以及供应商实际提供的销量估算字段。
2. **Amazon SP-API：官方补充**。Catalog Items 用于商品目录、图片、摘要、变体和销售排名；Product Pricing/Fees 仅在客户有卖家授权和对应角色时接入，不能假设它能返回全市场竞品销量或完整历史价格。
3. **CSV/Excel：兜底入口**。用于在 API 审批、费用或字段覆盖不满足时，先验证页面、利润和评分闭环。

数据访问统一经过后端适配器，不允许前端直接调用 Keepa 或 SP-API。适配器输出统一的内部商品模型，后续更换供应商不影响前端。

## 3.3 销量字段的产品口径

| 数据状态 | 页面展示 | 是否参与需求得分 |
|---|---|---|
| 有客户真实订单/授权报告 | “实际销量”并标注周期 | 是 |
| 供应商模型估算 | “销量估算”并显示来源、时间和置信等级 | 是，但降低置信度 |
| 只有 BSR/评论/排名变化 | “销量代理指标”，不得命名为销量 | 可作为需求代理指标 |
| 无可用字段 | “暂无销量数据” | 不参与或按已知权重重归一化 |

## 4. 数据源验证实验（3–5 天）

### 样本设计

- US 与 AU 各准备 50 个 ASIN，总计约 100 个。
- 覆盖 `AmazonRelease` 的每个目标类目；在类目未导入前，使用临时测试类目并标记为 `TEMP`。
- 每站点覆盖高、中、低 BSR，低/中/高评论数，不同价格带，父体/子体和 FBA/FBM。
- 每个 ASIN 记录变体口径，避免把父体价格与子体排名混用。

### 验证步骤

1. 调用候选源，获取标题、ASIN、类目、图片、价格、配送费、评分、评论数、BSR、历史序列、报价和可用销量字段。
2. 记录请求耗时、HTTP 状态、限流信息、token/配额消耗、缺失字段和错误码。
3. 随机抽查每站点 10–15 个 ASIN，与对应站点当前页面人工核对价格、变体、评分、评论和排名。
4. 检查历史序列的时间跨度、采样间隔、断点、币种和单位。
5. 核对商业授权：客户独立部署能否使用、是否允许缓存、展示、导出、历史存储及二次分发。
6. 输出 `data-source-validation.md`、原始样本 CSV、字段覆盖统计和月度成本估算。

### 建议通过标准

| 项目 | MVP 通过线 |
|---|---|
| 商品基础字段完整率 | ≥95%（以供应商承诺字段为分母） |
| 当前价格核对 | ≥90% 样本在约定容差内；必须统一变体、配送、优惠口径 |
| 历史趋势覆盖 | ≥90% 样本达到约定时间跨度；不足时明确降级 |
| 销量估算 | 只验覆盖率、定义和趋势合理性，不声称真实精度 |
| API 稳定性 | 连续测试期间错误可重试，限流有退避和清晰提示 |
| 商业可用性 | 授权、缓存、展示、导出、费用均有书面确认 |
| 两站点隔离 | US/AU 不串站点、币种、排名和时间戳 |

## 5. 技术架构

```text
浏览器（Next.js）
        │ HTTPS/JSON
FastAPI 业务层 ── 评分/利润/导出服务
        │
数据源适配层 ── Keepa / SP-API / CSV
        │
PostgreSQL ── 商品档案、快照、历史、任务、成本参数
        │
后台刷新 Worker（MVP 可先手动触发，后续加入调度）
```

### 推荐技术栈

- 前端：Next.js + React + TypeScript + ECharts。
- 后端：Python 3.12 + FastAPI + Pydantic。
- 数据库：PostgreSQL 16；迁移使用 Alembic。
- 数据处理：Pandas/NumPy；导出使用 openpyxl 或 XlsxWriter。
- 测试：pytest、FastAPI TestClient、Playwright（关键页面）。
- 部署：Docker Compose + Linux；Nginx/Caddy 提供 HTTPS 反向代理。
- 日志：结构化 JSON 日志；密钥只放 `.env` 或客户的密钥管理系统。

## 6. 核心数据模型

### `marketplaces`

`code`、`amazon_marketplace_id`、`currency`、`locale`、`timezone`、`sp_api_region`、`enabled`。

### `products`

`asin`、`marketplace_code`、`parent_asin`、`title`、`brand`、`category_id`、`category_path`、`image_url`、`variation_attributes`、`first_seen_at`、`last_seen_at`。

唯一键：`(marketplace_code, asin)`。US 和 AU 的同一 ASIN 必须视为两个市场记录。

### `product_snapshots`

`product_id`、`price`、`shipping_cost`、`currency`、`rating`、`review_count`、`sales_rank`、`estimated_monthly_sales`、`sales_metric_type`、`offer_count`、`fba_fee_estimate`、`source`、`fetched_at`、`raw_payload_hash`。

### `product_history`

`product_id`、`metric_name`、`metric_value`、`unit`、`observed_at`、`source`、`confidence`。

### `cost_profiles`

`marketplace_code`、`product_id/category_id`、`purchase_cost`、`inbound_shipping`、`packaging_cost`、`platform_fee`、`fba_fee`、`ad_cost`、`return_reserve`、`tax_cost`、`effective_from`。

### `research_tasks`

`marketplace_code`、`category_id`、`keywords`、`asin_list`、`filters_json`、`status`、`started_at`、`finished_at`、`error_summary`。

### `source_sync_jobs`

`source`、`marketplace_code`、`request_count`、`success_count`、`rate_limit_count`、`missing_field_count`、`started_at`、`finished_at`、`status`。

所有外部数据必须保留来源和抓取时间；原始响应只保存供应商许可允许保存的部分，必要时仅保存哈希和标准化字段。

## 7. API 与页面

### 后端接口

- `GET /api/marketplaces`
- `POST /api/research/tasks`
- `GET /api/research/tasks/{task_id}`
- `GET /api/products`
- `GET /api/products/{marketplace}/{asin}`
- `GET /api/products/{marketplace}/{asin}/history`
- `POST /api/products/import`
- `POST /api/profit/calculate`
- `POST /api/scoring/evaluate`
- `GET /api/reports/export`
- `GET /api/system/source-status`

### MVP 页面

1. 工作台：站点、最近任务、数据源状态。
2. 选品搜索：类目、关键词、ASIN、价格、BSR、评论、评分和利润筛选。
3. 结果榜单：综合分、需求、趋势、利润、竞争、风险、置信度。
4. 商品详情：当前值、历史曲线、竞品对比、成本参数和备注。
5. 利润计算器：US/AU 分别保存币种和费率。
6. 导入/导出：模板下载、错误行报告、CSV/XLSX 导出。
7. 管理页：数据源密钥状态、刷新任务、日志摘要、备份提示。

## 8. 评分与利润规则

第一版使用可解释规则，不训练复杂模型：

\[
S=0.25D+0.20G+0.25P+0.20C+0.10R
\]

- `D` 需求：销量估算或销量代理指标、BSR、评论增长等。
- `G` 趋势：价格/排名/评论/销量指标的时间变化。
- `P` 利润：按用户成本参数计算的利润率和 ROI。
- `C` 竞争机会：评论门槛、报价数量、品牌集中度、价格分散度。
- `R` 风险可控：数据完整度、侵权/合规人工标记、退货和供应链风险。

缺失字段不得直接填 0。默认采用“已知权重重归一化 + 置信度下降 + 页面提示数据不足”。

\[
\text{单件利润}=售价-采购成本-头程物流-平台费-FBA费-包装-广告-退货预留-税费
\]

竞品采购价未知时，页面必须显示“情景利润”，并要求用户输入成本；不得声称是竞品真实净利润。

## 9. 开发任务与里程碑

| 里程碑 | 任务 | 产出 | 预计周期 |
|---|---|---|---|
| M1 需求冻结 | 导入类目、确定字段、验收口径、两站点配置 | PRD、数据字典、验收标准 | 1–2 天 |
| M2 数据验证 | Keepa/SP-API/CSV 适配器原型、样本测试、授权核查 | 验证报告、样本 CSV、成本表 | 3–5 天 |
| M3 骨架 | Docker、数据库迁移、FastAPI、Next.js、站点切换 | 可启动系统、OpenAPI 草案 | 2–4 天 |
| M4 业务闭环 | 商品查询、详情、历史、利润、评分、导出 | 可用 MVP | 7–10 天 |
| M5 联调测试 | 限流、缺失数据、错误重试、权限、跨站点隔离 | 测试报告、缺陷清单 | 3–5 天 |
| M6 独立部署 | 客户服务器部署、备份恢复、HTTPS、交付培训 | 部署包、手册、验收记录 | 1–3 天 |

按单人开发、数据源顺利可用估计，日历周期约 3–5 周；API 审批、账号购买和客户反馈不计入纯开发工期。

## 10. 交付与验收

### 交付物

- 源代码、Dockerfile、`docker-compose.yml`、数据库迁移。
- `.env.example`，不包含真实密钥。
- 数据源适配器、字段映射和 `data-source-validation.md`。
- 选品评分、利润计算和缺失数据策略说明。
- 自动化测试、部署手册、备份恢复手册、使用说明。
- 已知限制：销量估算口径、数据缺失、接口限流、第三方费用和授权范围。

### 验收场景

1. US/AU 切换后，商品、货币、费率、历史曲线不串站。
2. 通过关键词、ASIN 和 CSV 均能创建任务并看到状态。
3. 价格、BSR、评分、评论与正确 ASIN/变体关联。
4. API 限流、密钥失效、字段缺失时有可理解提示，任务不会静默成功。
5. 利润计算可用人工样例复现；评分排序与导出结果一致。
6. 重启容器后历史数据、配置和收藏仍存在；备份可恢复。
7. 任何“销量”显示均标注实际/估算/代理/不可用类型。

## 11. 当前立即执行清单

1. 从 `AmazonRelease` 项目导入目标类目名称、Amazon browse node、关键词和排除项。
2. 客户提供或确认 Keepa、SP-API、Helium 10/Jungle Scout 等账号及商业使用许可。
3. 为 US/AU 各准备 50 个真实 ASIN，优先覆盖目标类目。
4. 先运行数据源验证，不先承诺销量准确率和固定 API 费用。
5. 验证通过后冻结字段和接口，进入 M3 骨架开发。

