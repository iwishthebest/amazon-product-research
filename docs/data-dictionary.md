# AmazonRelease MVP 数据字典

## 站点配置 `marketplaces`

| 字段 | 类型 | 约束 |
|---|---|---|
| `code` | string | `US` 或 `AU`，大写 |
| `amazon_marketplace_id` | string | Amazon 官方市场 ID |
| `frontend_domain` | string | 前台域名 |
| `seller_central_domain` | string | Seller Central 域名 |
| `sp_api_endpoint` | string | SP-API 区域端点 |
| `sp_api_region` | string | `na` 或 `fe` |
| `currency` | string | US=`USD`，AU=`AUD` |
| `locale` | string | 默认 `en-US` / `en-AU` |
| `timezone` | string | 可由客户覆盖 |

## 商品快照 `product_snapshots`

主键按 `(marketplace_code, asin)` 隔离。价格、排名、评分和评论数均必须与同一站点、同一变体口径关联。

| 字段 | 说明 |
|---|---|
| `price` / `shipping_cost` / `currency` | 当前价格与配送费 |
| `rating` / `review_count` | 当前评分和评论数 |
| `sales_rank` | BSR/销售排名，不能直接命名为销量 |
| `estimated_monthly_sales` | 仅在来源明确提供估算时填写 |
| `sales_metric_type` | `actual` / `estimated` / `proxy` / `unavailable`，必填 |
| `source` / `fetched_at` | 数据来源与抓取时间，必填来源 |

## 历史值 `product_history`

保存 `marketplace_code`、`asin`、`metric_name`、`metric_value`、`unit`、`observed_at`、`source` 和可选 `confidence`。不得用读取时间冒充缺失的观测时间。

## 成本参数 `cost_profiles`

售价、采购价、头程、平台费、FBA、包装、广告、退货预留和税费均可编辑；所有利润结果标记 `is_scenario=true`。
