# AU 关键词确认表（已确认）

本表由 `data/reports/snapshot_2026-10-21.json` 的商品标题按 `category_name` 分组提取，客户已于 2026-10-22 确认。正式配置见 `data/keyword_config_au.json`。关键词可用于任务创建和筛选，不代表搜索量或销量已经验证。

## 类目候选词

| 类目 | 保留词 | 排除或清洗词 | 状态 |
|---|---|---|---|
| Pilates | `pilates`, `resistance`, `kit`, `band`, `reformer`, `ring`, `stretching`, `loop` | `offer`, `stars`, 品牌名、价格和评论残留 | 已确认 |
| Yoga | `yoga`, `shorts`, `gym`, `casual`, `pockets`, `hoodie`, `running`, `socks`, `lightweight`, `breathable` | `offer`, `stars`, 服饰品牌名 | 已确认 |
| Mats | `mat`, `yoga`, `exercise`, `thick`, `pilates`, `pad`, `non-slip`, `foldable`, `tpe`, `floor` | `offer`, `stars`, 尺寸、颜色和价格 | 已确认 |
| Blocks | `yoga`, `stretching`, `block`, `pilates`, `balance`, `cork`, `support`, `bricks`, `meditation`, `non-slip` | `offer`, `stars`, 单纯包装数量 | 已确认 |
| Mat Towels | `towel`, `yoga`, `gym`, `sweat`, `dry`, `quick`, `travel`, `absorbent`, `mat`, `pilates` | `offer`, `stars`, 颜色、尺寸和包装残留 | 已确认 |
| Mat Bags | `yoga`, `bag`, `mat`, `strap`, `carry`, `storage`, `waterproof`, `case`, `drawstring` | `offer`, `stars`, 颜色、尺寸和品牌名 | 已确认 |
| Foam Wedges | `wedge`, `yoga`, `board`, `squat`, `foam`, `eva`, `block`, `slant`, `foot`, `calf` | `offer`, `stars`, 尺寸和颜色 | 已确认 |
| Straps | `strap`, `resistance`, `ankle`, `sling`, `removable` | 与瑜伽无关的鞋类/凉鞋词需人工排除 | 已确认 |

## 已确认的同义词与拼写变体

| 规范词 | 可能变体 | 处理建议 |
|---|---|---|
| `mat` | `mats`, `yoga mat`, `exercise mat` | 是否归并为一个主题词 |
| `towel` | `towels`, `yoga towel`, `mat towel` | 是否区分单件/套装 |
| `strap` | `straps`, `mat strap`, `ankle strap` | 按产品用途拆分 |
| `block` | `blocks`, `yoga block`, `brick`、`bricks` | 是否将 `brick` 作为同义词 |
| `band` | `bands`, `resistance band` | 是否区分弹力带和器械带 |
| `non-slip` | `non slip`, `anti-slip` | 统一连字符和词形 |

## 当前口径

- AU 关键词、排除项和同义词已进入 `data/keyword_config_au.json`，状态为 `confirmed`。
- 关键词配置只用于任务创建和筛选，不代表搜索量或销量结论。
- US 站是否复用 AU 词表，待 US 类目抓取后单独检查覆盖情况。
