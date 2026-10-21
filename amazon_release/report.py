from __future__ import annotations

import html
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


_RATING_SUFFIX = re.compile(r"\s+\d+(?:\.\d+)?\s+out of 5 stars.*$", re.I)
_PRICE_IN_TITLE = re.compile(r"(?:offer\s+from|from)\s+\$\s*([\d,.]+)", re.I)


def _safe_product_url(record: dict) -> str:
    asin = str(record.get("asin", "")).strip().upper()
    candidate = str(record.get("product_url") or f"https://www.amazon.com.au/dp/{asin}")
    parsed = urlparse(candidate)
    if parsed.netloc.lower() not in {"amazon.com.au", "www.amazon.com.au"}:
        return f"https://www.amazon.com.au/dp/{asin}"
    return candidate


def _image_url(record: dict) -> str:
    supplied = str(record.get("image_url") or "").strip()
    if supplied:
        return supplied
    asin = str(record.get("asin", "")).strip().upper()
    return f"https://images-na.ssl-images-amazon.com/images/P/{asin}.01.LZZZZZZZ.jpg"


def _float_or_none(value: object) -> float | None:
    try:
        return float(value) if value is not None and str(value).strip() else None
    except (TypeError, ValueError):
        return None


def _int_or_none(value: object) -> int | None:
    try:
        return int(value) if value is not None and str(value).strip() else None
    except (TypeError, ValueError):
        return None


def build_seller_analysis(
    record: dict,
    *,
    is_new: bool = False,
    max_rank: int = 80,
    max_reviews: int = 1000,
) -> dict[str, object]:
    """Build bounded seller signals without claiming confirmed sales."""
    rank = _int_or_none(record.get("rank"))
    rating = _float_or_none(record.get("rating"))
    reviews = _int_or_none(record.get("review_count"))
    rank_score = 0.0 if rank is None else max(0.0, min(1.0, (max_rank - rank + 1) / max_rank))
    rating_score = 0.0 if rating is None else max(0.0, min(1.0, rating / 5.0))
    review_score = 0.0 if reviews is None else max(0.0, min(1.0, math.log1p(max(0, reviews)) / math.log1p(max_reviews)))
    score = round(100 * (0.45 * rank_score + 0.20 * rating_score + 0.20 * review_score + 0.15 * int(is_new)))
    heat_label = "高热度信号" if score >= 70 else "中热度信号" if score >= 45 else "观察"

    if reviews is None:
        competition = "评论数据缺失，先人工核验"
    elif reviews <= 30:
        competition = "评论壁垒较低，可测试差异化切入"
    elif reviews <= 200:
        competition = "中等竞争，需比较价格与功能"
    else:
        competition = "评论壁垒较高，避免直接同质化"

    advice: list[str] = []
    if rating is None:
        advice.append("评价数据缺失，先核验真实体验")
    elif rating < 4.0:
        advice.append("低评分：重点研究质量、尺寸、耐用性和说明书问题")
    elif rating < 4.4:
        advice.append("评价一般：围绕差评痛点做功能或材质改进")
    else:
        advice.append("评价较好：寻找材质、套装、内容物或售后差异化")
    if reviews is None or reviews <= 30:
        advice.append("评论量较低：先验证需求、主图和转化，再控制备货")
    elif reviews >= 500:
        advice.append("评论量较高：避开同质化，优先寻找细分人群")
    if record.get("price") is None:
        advice.append("售价缺失：补查售价、佣金、头程和广告后再算利润")
    return {
        "score": score,
        "heat_label": heat_label,
        "sales_claim": "未确认销量",
        "competition": competition,
        "improvement": "；".join(advice),
        "rank_signal": f"新品榜第 {rank} 名" if rank is not None else "新品榜未排名",
        "rating_signal": f"{rating:.1f}/5" if rating is not None else "无评分",
        "review_signal": f"{reviews:,} 条评论" if reviews is not None else "无评论数",
    }


def build_product_view(record: dict, new_asins: set[str] | None = None) -> dict[str, object]:
    raw_title = " ".join(str(record.get("title") or "").split())
    title = _RATING_SUFFIX.sub("", raw_title).strip(" -")
    price = record.get("price")
    currency = record.get("currency")
    if price is None:
        match = _PRICE_IN_TITLE.search(raw_title)
        price = match.group(1).replace(",", "") if match else None
        currency = currency or ("AUD" if price is not None else None)
    elif isinstance(price, (int, float)):
        price = f"{price:.2f}"
    asin = str(record.get("asin", "")).strip().upper()
    is_new = asin in (new_asins or set())
    view = {
        "asin": asin,
        "title": title or asin,
        "category_name": str(record.get("category_name") or "未分类"),
        "rank": record.get("rank"),
        "price": str(price) if price is not None else None,
        "currency": currency,
        "rating": record.get("rating"),
        "review_count": record.get("review_count"),
        "image_url": _image_url(record),
        "product_url": _safe_product_url(record),
        "observed_at": str(record.get("observed_at") or record.get("first_seen_at") or ""),
        "is_new": is_new,
    }
    view.update(build_seller_analysis(record, is_new=is_new))
    return view


def _category_stats(products: list[dict[str, object]]) -> dict[str, object]:
    ranks = [_int_or_none(item.get("rank")) for item in products]
    ratings = [_float_or_none(item.get("rating")) for item in products]
    reviews = [_int_or_none(item.get("review_count")) for item in products]
    valid_ranks = [value for value in ranks if value is not None]
    valid_ratings = [value for value in ratings if value is not None]
    low_review = sum(value is None or value <= 30 for value in reviews)
    return {
        "count": len(products),
        "top_rank": min(valid_ranks) if valid_ranks else None,
        "avg_rating": sum(valid_ratings) / len(valid_ratings) if valid_ratings else None,
        "low_review": low_review,
    }


def render_html(
    records: Iterable[dict],
    output_path: str | Path,
    *,
    report_date: str,
    new_asins: set[str] | None = None,
) -> Path:
    views = [build_product_view(record, new_asins) for record in records]
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for view in views:
        groups[str(view["category_name"])].append(view)
    for products in groups.values():
        products.sort(key=lambda item: (item["rank"] is None, item["rank"] or 999999, str(item["asin"])))

    new_count = sum(bool(item["is_new"]) for item in views)
    hot_count = sum(item["heat_label"] == "高热度信号" for item in views)
    category_rows: list[str] = []
    for category in sorted(groups):
        stats = _category_stats(groups[category])
        top_rank = f"第 {stats['top_rank']} 名" if stats["top_rank"] is not None else "无"
        avg_rating = f"{stats['avg_rating']:.1f}/5" if stats["avg_rating"] is not None else "无"
        category_rows.append(
            f"<tr><td>{html.escape(category)}</td><td>{stats['count']}</td><td>{top_rank}</td>"
            f"<td>{avg_rating}</td><td>{stats['low_review']}</td></tr>"
        )

    priority_rows: list[str] = []
    priority_views = sorted(views, key=lambda item: (-int(item["score"]), item["rank"] is None, item["rank"] or 999999))[:10]
    for index, product in enumerate(priority_views, 1):
        priority_rows.append(
            f"<tr><td>{index}</td><td>{html.escape(str(product['category_name']))}</td>"
            f"<td>{html.escape(str(product['title']))}</td><td>{product['score']}/100</td>"
            f"<td>{html.escape(str(product['rank_signal']))}</td><td>{html.escape(str(product['review_signal']))}</td>"
            f"<td>{html.escape(str(product['competition']))}</td></tr>"
        )

    cards: list[str] = []
    for category in sorted(groups):
        products = groups[category]
        cards.append(
            f'<section class="category" data-category="{html.escape(category, quote=True)}">'
            f'<h2>{html.escape(category)} <span>{len(products)} 个商品</span></h2><div class="grid">'
        )
        for product in products:
            badge = '<span class="badge new">今日首次发现 / New today</span>' if product["is_new"] else ""
            rank = f"第 {html.escape(str(product['rank']))} 名" if product["rank"] is not None else "未排名"
            price = f"{html.escape(str(product['currency'] or 'AUD'))} {html.escape(str(product['price']))}" if product["price"] else "售价未取得"
            observed = html.escape(str(product["observed_at"])[:19].replace("T", " ")) or "时间未取得"
            cards.append(
                f'<article class="card" data-category="{html.escape(category, quote=True)}" '
                f'data-heat="{html.escape(str(product["heat_label"]), quote=True)}" '
                f'data-search="{html.escape(str(product["title"]) + " " + str(product["asin"]), quote=True)}">'
                f'<a class="image-wrap" href="{html.escape(str(product["product_url"]), quote=True)}" target="_blank" rel="noreferrer">'
                f'<img loading="lazy" src="{html.escape(str(product["image_url"]), quote=True)}" alt="{html.escape(str(product["title"]))}" '
                "onerror=\"this.style.display='none';this.nextElementSibling.style.display='grid';\">"
                '<div class="placeholder">图片不可用<br><small>点击打开商品页</small></div></a>'
                f'<div class="meta">{badge}<span class="score">机会评分 {product["score"]}/100</span></div>'
                f'<div class="signals"><span class="heat">{html.escape(str(product["heat_label"]))}</span>'
                f'<span>{html.escape(str(product["rank_signal"]))}</span><span>{html.escape(str(product["rating_signal"]))}</span>'
                f'<span>{html.escape(str(product["review_signal"]))}</span></div>'
                f'<h3>{html.escape(str(product["title"]))}</h3>'
                f'<p class="asin">ASIN: {html.escape(str(product["asin"]))} · 采集时间：{observed}</p>'
                f'<p class="facts"><strong>{price}</strong> · <span class="claim">{html.escape(str(product["sales_claim"]))}</span></p>'
                f'<p class="competition"><strong>竞争：</strong>{html.escape(str(product["competition"]))}</p>'
                f'<p class="improvement"><strong>改进方向：</strong>{html.escape(str(product["improvement"]))}</p>'
                f'<a class="link" href="{html.escape(str(product["product_url"]), quote=True)}" target="_blank" rel="noreferrer">打开 Amazon AU 商品页 ↗</a>'
                '</article>'
            )
        cards.append("</div></section>")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    document = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Amazon AU 新品与产品开发选品分析 · {html.escape(report_date)}</title>
<style>
:root {{ color-scheme: light; --ink:#17202a; --muted:#667085; --line:#e6e8ec; --accent:#c2410c; --blue:#155e75; --bg:#f5f7fb; --green:#166534; }}
* {{ box-sizing:border-box; }} body {{ margin:0; color:var(--ink); background:var(--bg); font:14px/1.5 Segoe UI,"Microsoft YaHei",Arial,sans-serif; }}
header {{ padding:34px 5vw 24px; background:linear-gradient(135deg,#17202a,#155e75); color:white; }} header h1 {{ margin:0 0 8px; font-size:clamp(24px,4vw,42px); }} header p {{ margin:0; opacity:.86; }}
main {{ width:min(1600px,92vw); margin:24px auto 60px; }} .notice {{ background:#fff7ed; border:1px solid #fed7aa; border-radius:12px; padding:14px 16px; margin-bottom:18px; }}
.summary {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin-bottom:18px; }} .summary .metric {{ background:white; border:1px solid var(--line); border-radius:12px; padding:16px; }} .metric strong {{ display:block; font-size:28px; color:var(--blue); }} .metric span {{ color:var(--muted); }}
.toolbar {{ display:flex; flex-wrap:wrap; gap:10px; padding:14px; background:white; border:1px solid var(--line); border-radius:12px; margin-bottom:24px; }} input,select {{ border:1px solid #cbd5e1; border-radius:8px; padding:9px 10px; background:white; color:var(--ink); }} input {{ min-width:260px; flex:1; }}
.comparison {{ background:white; border:1px solid var(--line); border-radius:12px; padding:14px; margin-bottom:28px; overflow:auto; }} table {{ border-collapse:collapse; width:100%; min-width:620px; }} th,td {{ padding:9px 10px; border-bottom:1px solid var(--line); text-align:left; }} th {{ color:var(--muted); font-weight:600; }}
.category {{ margin:0 0 34px; }} h2 {{ display:flex; justify-content:space-between; gap:16px; align-items:baseline; border-bottom:1px solid var(--line); padding-bottom:10px; }} h2 span {{ color:var(--muted); font-size:13px; font-weight:400; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(285px,1fr)); gap:16px; }} .card {{ background:white; border:1px solid var(--line); border-radius:14px; overflow:hidden; box-shadow:0 3px 12px #17202a0d; display:flex; flex-direction:column; min-width:0; }}
.image-wrap {{ aspect-ratio:1/1; background:#f1f3f6; display:grid; place-items:center; color:var(--muted); text-align:center; text-decoration:none; overflow:hidden; }} .image-wrap img {{ width:100%; height:100%; object-fit:contain; background:white; }} .placeholder {{ display:none; place-items:center; width:100%; height:100%; padding:20px; }}
.card h3 {{ margin:8px 14px 4px; font-size:15px; line-height:1.35; }} .meta,.facts,.asin,.link,.competition,.improvement,.signals {{ margin-left:14px; margin-right:14px; }} .meta {{ margin-top:11px; display:flex; justify-content:space-between; align-items:center; gap:8px; }} .score {{ color:var(--blue); font-weight:700; }} .badge {{ color:white; background:var(--accent); border-radius:999px; padding:3px 8px; font-size:11px; }} .badge.new {{ white-space:nowrap; }}
.signals {{ display:flex; flex-wrap:wrap; gap:5px; margin-top:8px; color:var(--muted); font-size:12px; }} .signals span {{ background:#f1f5f9; border-radius:999px; padding:3px 7px; }} .signals .heat {{ background:#dcfce7; color:var(--green); font-weight:600; }}
.asin {{ color:var(--muted); font-size:12px; margin-top:0; margin-bottom:5px; }} .facts {{ margin-top:0; color:var(--muted); }} .facts strong {{ color:var(--ink); }} .claim {{ color:#92400e; }} .competition,.improvement {{ font-size:13px; margin-top:7px; margin-bottom:0; }} .improvement {{ color:#334155; }} .link {{ margin-top:auto; margin-bottom:14px; color:#b45309; font-weight:600; text-decoration:none; }} .link:hover {{ text-decoration:underline; }}
footer {{ color:var(--muted); border-top:1px solid var(--line); padding-top:16px; margin-top:30px; }} .hidden {{ display:none !important; }}
</style></head><body><header><h1>Amazon AU 新品与产品开发选品分析</h1><p>Amazon AU New Releases · Sports, Fitness &amp; Outdoors · Pilates / Yoga · 报告日期：{html.escape(report_date)}</p></header><main>
<div class="notice"><strong>证据边界：</strong>“今日首次发现”表示本地程序第一次观察到该 ASIN；新品榜热度信号（非销量确认）只代表新品榜内位置，不等于实际销量。当前数据没有 Amazon 销量、BSR 历史或利润成本，因此“卖得好”仍需人工核验。</div>
<section class="summary"><div class="metric"><strong>{len(views)}</strong><span>商品总数</span></div><div class="metric"><strong>{new_count}</strong><span>本次首次发现</span></div><div class="metric"><strong>{hot_count}</strong><span>高热度信号</span></div><div class="metric"><strong>{len(groups)}</strong><span>子类目数</span></div></section>
<section class="toolbar"><input id="search" placeholder="搜索标题或 ASIN"><select id="category-filter"><option value="">全部类目</option>{''.join(f'<option>{html.escape(category)}</option>' for category in sorted(groups))}</select><select id="heat-filter"><option value="">全部热度</option><option>高热度信号</option><option>中热度信号</option><option>观察</option></select></section>
<section class="comparison"><h2>重点候选 <span>按机会评分排序，仅供优先研究</span></h2><table><thead><tr><th>#</th><th>类目</th><th>商品</th><th>评分</th><th>新品榜</th><th>评论</th><th>竞争线索</th></tr></thead><tbody>{''.join(priority_rows)}</tbody></table></section>
<section class="comparison"><h2>类目横向比较</h2><table><thead><tr><th>类目</th><th>商品数</th><th>最高新品榜位</th><th>平均评分</th><th>低评论量商品</th></tr></thead><tbody>{''.join(category_rows)}</tbody></table></section>
{''.join(cards)}<footer>评分用于筛选优先级，不是销量预测：45% 新品榜排名、20% 评分、20% 评论量、15% 本地首次发现。低评论量定义为不超过 30 条；售价、采购成本、佣金、头程、广告和退货率仍需补充后计算利润。</footer></main>
<script>const search=document.getElementById('search'), category=document.getElementById('category-filter'), heat=document.getElementById('heat-filter'); function applyFilters() {{ const q=search.value.toLowerCase().trim(), c=category.value, h=heat.value; document.querySelectorAll('.card').forEach(card=>{{ const ok=(!q||card.dataset.search.toLowerCase().includes(q))&&(!c||card.dataset.category===c)&&(!h||card.dataset.heat===h); card.classList.toggle('hidden',!ok); }}); document.querySelectorAll('.category').forEach(section=>{{ section.classList.toggle('hidden',!section.querySelector('.card:not(.hidden)')); }}); }} [search,category,heat].forEach(el=>el.addEventListener('input',applyFilters));</script></body></html>'''
    output.write_text(document, encoding="utf-8")
    return output
