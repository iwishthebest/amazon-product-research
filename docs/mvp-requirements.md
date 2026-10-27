# AmazonRelease MVP 需求冻结草案

状态：M1 工作基线（2026-10-21）

## 已冻结边界

- 目标平台：Amazon；站点：US 与 AU；部署在客户自己的服务器。
- 访问端：通过 Safari/Chrome 等浏览器访问，交付物为响应式 Web 页面，覆盖桌面、平板和移动端。
- MVP 闭环：发现商品 → 查看竞品 → 情景利润 → 规则评分/筛选 → CSV/XLSX 导出。
- API 密钥只保存在服务器端；浏览器不直连 Keepa 或 SP-API。
- 销量必须标注为 `actual`、`estimated`、`proxy` 或 `unavailable`，估算和代理指标不得显示成真实销量。
- 竞品采购成本未知时只能输出“情景利润”，不能声称竞品真实净利润。

## 当前已确认字段

商品/快照的最小字段见 [`data-dictionary.md`](data-dictionary.md)。已有旧采集器中的 AU 新品榜字段只作为历史参考，不能作为 US/AU 全量数据源承诺。

## 待补充或验证

- US 类目与节点；AU 关键词种子和排除项已确认，见 `data/keyword_config_au.json`。
- 从 US/AU 对应站点类目页取得各 50 个 ASIN，并覆盖价格、BSR、评论量、父子体和 FBA/FBM。
- Keepa、SP-API、Helium 10/Jungle Scout 的账号、授权范围、缓存/展示/导出许可和费用。
- 费率、税费和时区的客户级覆盖配置。

在数据源授权和字段验证完成前，代码可以生成带来源和时间戳的公开页面验证结果，但不能生成生产销量或固定成本结论。
