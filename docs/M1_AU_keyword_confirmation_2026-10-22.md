# AU 关键词确认表（待客户确认）

本表由 `data/reports/snapshot_2026-10-21.json` 的商品标题按 `category_name` 分组提取。所有词均为 `source=title_derived`、`status=candidate`，不能解释为搜索量、销量或客户已确认需求。

## 类目候选词

| 类目 | 候选保留词 | 建议排除或清洗词 | 客户确认 |
|---|---|---|---|
| Pilates | `pilates`, `resistance`, `kit`, `band`, `reformer`, `ring`, `stretching`, `loop` | `offer`, `stars`, 品牌名、价格和评论残留 | 待确认 |
| Yoga | `yoga`, `shorts`, `gym`, `casual`, `pockets`, `hoodie`, `running`, `socks`, `lightweight`, `breathable` | `offer`, `stars`, 服饰品牌名 | 待确认 |
| Mats | `mat`, `yoga`, `exercise`, `thick`, `pilates`, `pad`, `non-slip`, `foldable`, `tpe`, `floor` | `offer`, `stars`, 尺寸、颜色和价格 | 待确认 |
| Blocks | `yoga`, `stretching`, `block`, `pilates`, `balance`, `cork`, `support`, `bricks`, `meditation`, `non-slip` | `offer`, `stars`, 单纯包装数量 | 待确认 |
| Mat Towels | `towel`, `yoga`, `gym`, `sweat`, `dry`, `quick`, `travel`, `absorbent`, `mat`, `pilates` | `offer`, `stars`, 颜色、尺寸和包装残留 | 待确认 |
| Mat Bags | `yoga`, `bag`, `mat`, `strap`, `carry`, `storage`, `waterproof`, `case`, `drawstring` | `offer`, `stars`, 颜色、尺寸和品牌名 | 待确认 |
| Foam Wedges | `wedge`, `yoga`, `board`, `squat`, `foam`, `eva`, `block`, `slant`, `foot`, `calf` | `offer`, `stars`, 尺寸和颜色 | 待确认 |
| Straps | `strap`, `resistance`, `ankle`, `sling`, `removable` | 与瑜伽无关的鞋类/凉鞋词需人工排除 | 待确认 |

## 同义词与拼写变体待确认

| 规范词 | 可能变体 | 处理建议 |
|---|---|---|
| `mat` | `mats`, `yoga mat`, `exercise mat` | 是否归并为一个主题词 |
| `towel` | `towels`, `yoga towel`, `mat towel` | 是否区分单件/套装 |
| `strap` | `straps`, `mat strap`, `ankle strap` | 按产品用途拆分 |
| `block` | `blocks`, `yoga block`, `brick`、`bricks` | 是否将 `brick` 作为同义词 |
| `band` | `bands`, `resistance band` | 是否区分弹力带和器械带 |
| `non-slip` | `non slip`, `anti-slip` | 统一连字符和词形 |

## 客户需要填写的确认项

1. 保留词：用于搜索或任务创建的词。
2. 排除词：不希望进入候选结果的品牌、服饰、鞋类或噪声词。
3. 同义词：是否合并复数、连字符和近义表达。
4. 类目边界：`Yoga` 根类目下的服饰和鞋类是否保留。
5. US 映射：确认 AU 词是否直接复用到 US，或另建 US 词表。

确认完成后，再将结果转换为正式配置；当前不修改 `config.example.json`。
