# M1：Amazon AU 类目与关键词证据

状态：已核对项目内现有数据；US 站、关键词种子和外部数据源授权仍待确认。

## 证据路径

- 配置基线：`config.example.json`
- 类目发现快照：`data/reports/categories_2026-10-21.json`
- 商品观测快照：`data/reports/snapshot_2026-10-21.json`
- 历史对照：`data/reports/categories_2026-10-20.json`
- 本地数据库：`data/amazon_release.sqlite3`

## 已确认的 AU 范围

| 项目 | 值 | 证据 |
|---|---|---|
| 站点 | Amazon Australia | `config.example.json` 的 `allowed_domain` |
| Marketplace ID | `A39IBJ37TRP1C6` | `config.example.json` |
| 根类目 | Pilates | 节点 `5044228051` |
| 根类目 | Yoga | 节点 `5044231051` |
| 抓取快照 | 39 个类目节点 | `categories_2026-10-21.json` |
| 商品观测 | 664 条记录、664 个唯一 ASIN | `snapshot_2026-10-21.json` |
| 排除项 | `5043942051` | `config.example.json` 的 `exclude_node_ids` |

根类目 URL：

- `https://www.amazon.com.au/gp/new-releases/sporting-goods/5044228051`
- `https://www.amazon.com.au/gp/new-releases/sporting-goods/5044231051`

已发现的一级子类目名称包括 Pilates 下的 `Barrels`、`Chairs`、`Fitness Circles`、`Flexbands`、`Floor Mats`、`Reformer Boxes`、`Reformers`、`Sets`、`Spine Supporters`、`Straps`；Yoga 下的 `Blocks`、`Foam Wedges`、`Mat Bags`、`Mat Straps`、`Mat Towels`、`Mats`、`Meditation Benches`、`Sandbags`、`Silk Eye Bags`、`Starter Sets`、`Straps`、`Yoga`。

## 关键词结论

在项目代码、`data` 目录和现有 Markdown 文档中，没有发现独立的关键词种子文档或 `keyword/关键词` 配置。当前可确认的是类目节点和商品标题；不能把标题词频自动写成客户确认的关键词种子。

因此 M1 暂记为：

- AU 类目节点：已确认，可进入字段与接口冻结。
- AU 关键词：待客户确认；暂不编造。
- US 类目、节点和关键词：待补充。
- Keepa、SP-API 或其他供应商：待确认账号、授权、缓存和导出许可。

## 下一道门

在进入 M2 数据源验证前，需要补齐一份客户确认表：

1. US 目标类目名称与 browse node；
2. US/AU 关键词种子及排除词；
3. 每个站点约 50 个真实 ASIN；
4. 可使用的数据源、账号和商业授权范围。

