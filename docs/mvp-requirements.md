# AmazonRelease MVP 需求冻结草案

状态：M1 工作基线（2026-10-21）

## 已冻结边界

- 目标平台：Amazon；站点：US 与 AU；部署在客户自己的服务器。
- 访问端：Mac 上的 Safari/Chrome，桌面优先，最低按 1440×900 设计，并兼容 1280×800。
- MVP 闭环：发现商品 → 查看竞品 → 情景利润 → 规则评分/筛选 → CSV/XLSX 导出。
- API 密钥只保存在服务器端；浏览器不直连 Keepa 或 SP-API。
- 销量必须标注为 `actual`、`estimated`、`proxy` 或 `unavailable`，估算和代理指标不得显示成真实销量。
- 竞品采购成本未知时只能输出“情景利润”，不能声称竞品真实净利润。

## 当前已确认字段

商品/快照的最小字段见 [`data-dictionary.md`](data-dictionary.md)。已有旧采集器中的 AU 新品榜字段只作为历史参考，不能作为 US/AU 全量数据源承诺。

## 待客户提供或确认

- 目标类目名称、Amazon browse node、关键词种子和排除项。
- US/AU 各 50 个真实 ASIN（覆盖价格、BSR、评论量、父子体和 FBA/FBM）。
- Keepa、SP-API、Helium 10/Jungle Scout 的账号、授权范围、缓存/展示/导出许可和费用。
- 费率、税费和时区的客户级覆盖配置。

在以上信息确认前，代码只能提供 CSV 兜底入口、配置校验和空数据状态，不能生成生产销量或固定成本结论。
