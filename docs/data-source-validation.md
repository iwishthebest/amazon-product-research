# 数据源验证记录模板

状态：Keepa 已按项目决策跳过；当前仅保留公开 Amazon 页面抽查、SP-API 待授权和 CSV 兜底入口。

## 已执行的 M2 抽查

2026-10-22 已从旧项目数据生成 US/AU 各 50 行候选台账，并对公开 Amazon 商品页各抽查 12 行。详细原始结果见 [`docs/m2/2026-10-22/`](m2/2026-10-22/)：AU 12/12 成功，US 7/12 成功，US 5 行 HTTP 404。Keepa 不纳入本项目数据源链路；该结果只用于页面字段可读性和站点隔离检查，不等价于 SP-API 授权验证。

## 旧项目输入文件

- 类目节点与关键词候选来源：`C:\Users\nozdi\Documents\ChatGPT\AmazonRelease\data\reports\categories_2026-10-21.json`。这是类目节点台账，不是独立关键词文档；当前以 `name` 字段生成关键词候选。
- 真实历史 ASIN 候选来源：`C:\Users\nozdi\Documents\ChatGPT\AmazonRelease\data\reports\snapshot_2026-10-21.json`。包含 `asin`、类目节点、标题、排名、评分、评论数、价格和观测时间。

## 样本台账

| marketplace | asin | category | variant_scope | price_band | bsr_band | review_band | fulfillment | source | fetched_at |
|---|---|---|---|---|---|---|---|---|---|
| US | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO |
| AU | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO |

## 逐源记录

对每个候选源记录：请求耗时、HTTP 状态、限流/退避、配额消耗、缺失字段、错误码、历史跨度、采样间隔、币种和单位。

## 通过标准

- 商品基础字段完整率 ≥95%（以供应商承诺字段为分母）。
- 当前价格人工核对 ≥90% 样本在统一变体/配送/优惠口径下通过。
- 历史趋势覆盖 ≥90% 样本达到约定跨度；不足时明确降级。
- 销量只评估覆盖率、定义和趋势合理性，不声称真实精度。
- 商业授权、缓存、展示、导出、费用均有书面确认。
- US/AU 的商品、币种、排名和时间戳完全隔离。
