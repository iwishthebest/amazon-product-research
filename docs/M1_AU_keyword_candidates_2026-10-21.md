# AU 候选关键词清单（数据推导）

状态：候选词，未经过客户确认，也不是搜索量或销量结论。

## 来源

- 输入文件：`data/reports/snapshot_2026-10-21.json`
- 输入记录：664 条商品记录
- 使用字段：`title`、`category_name`
- 生成方式：对标题进行英文词元化、转小写、去除常见功能词和页面噪声词后统计词频。

## 高频候选词

| 类型 | 候选词 |
|---|---|
| 核心主题 | `yoga`、`pilates`、`gym`、`exercise`、`training`、`fitness`、`sports` |
| 器材/产品 | `mat`、`foam`、`roller`、`machine`、`cable`、`trampoline`、`board`、`pad`、`ball`、`towel`、`block`、`straps` |
| 功能属性 | `adjustable`、`breathable`、`lightweight`、`grip`、`support`、`resistance`、`stretching`、`balance`、`sweat`、`non-slip` |
| 人群/服饰 | `women`、`men`、`girls`、`boys`、`shorts`、`hoodie`、`sleeve`、`pants`、`socks`、`cotton` |
| 使用场景 | `home`、`outdoor`、`running`、`travel`、`strength`、`muscle`、`waist`、`leg`、`foot` |

## 解释边界

- 词频来自新品榜标题，不等于 Amazon 搜索量、广告词量或实际销量。
- `offer`、`stars` 等页面残留词已视为噪声，不列入候选词。
- 候选词没有自动写入 `config.example.json`，也没有替代客户关键词种子。
- 后续应按 Pilates、Yoga 及其子类目分别统计，并由客户确认保留词、排除词、同义词和拼写变体。

## 下一步

将本清单交给客户确认，形成带有 `source=title_derived`、`status=candidate` 的关键词配置；确认后再进入 US/AU 关键词字段冻结和 M2 样本验证。

