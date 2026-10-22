# M2 数据源验证报告

验证时间：2026-10-21T17:06:14.989882+00:00
数据边界：本轮只验证有限数量的公开 Amazon 商品页；不把公开页当成已授权的 SP-API 生产源。

## 样本台账

- 计划样本：100 行（US 50 + AU 50 的同一 ASIN 候选集）。
- 实际请求：24 行；成功读取：19 行。
- 分站点：US 7/12 成功，AU 12/12 成功。
- 类目/关键词种子来源：`C:\Users\nozdi\Documents\ChatGPT\AmazonRelease\data\reports\categories_2026-10-21.json`。该文件是类目节点台账，不是独立关键词文档；当前以 `name` 字段生成关键词候选。
- ASIN 候选来源：`C:\Users\nozdi\Documents\ChatGPT\AmazonRelease\data\reports\snapshot_2026-10-21.json`。该文件是旧项目的真实历史观测快照。
- 关键词候选：Pilates, Yoga, Barrels, Chairs, Fitness Circles, Flexbands, Floor Mats, Reformer Boxes, Reformers, Sets, Spine Supporters, Straps, Blocks, Foam Wedges, Mat Bags, Mat Straps, Mat Towels, Mats, Meditation Benches, Sandbags, Silk Eye Bags, Starter Sets, Accessories, Aerobic Training Machines, Balance Trainers, Clothing, Exercise Machine Accessories, Fitness Technology, Footwear, Massage Belts & Electric Stimulators, Strength Training Equipment, Trampolines & Accessories, Sport Specific Clothing, Boys, Girls, Men, Women。这些词来自类目台账，仍需客户确认，不是已冻结关键词。

## 当前字段覆盖（以成功读取页面为分母）

| 字段 | 覆盖率 |
|---|---:|
| `title` | 100.0% |
| `price` | 73.7% |
| `rating` | 89.5% |
| `review_count` | 89.5% |
| `sales_rank` | 15.8% |
| `estimated_monthly_sales` | 0.0%（公开页未提供可授权的销量字段） |
| `sales_metric_type=actual` | 0 行 |

## 请求异常

- `HTTP 404`：5 行

## 结论与下一步

- 当前结果只能证明公开商品页的字段可读性和 US/AU 域名隔离，不能证明销量估算准确率或商业授权范围。
- Keepa 已按项目决策跳过，不参与本次 M2 通过/不通过判定，也不写入运行时数据源链路。
- SP-API 两个区域端点的未授权 HEAD 探测均返回 403，说明端点可达但不能替代 Seller Central 授权和字段验证；在获得凭证前不执行生产调用。
- 变体、配送、优惠和价格口径仍需人工抽查 10–15 个 ASIN 后才能进入通过/不通过判定。
