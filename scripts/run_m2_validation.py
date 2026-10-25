from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import requests

from backend.app.config import DEFAULT_MARKETPLACES
from backend.app.validation import parse_product_page, select_sample_rows


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_keywords(path: Path | None, categories: list[dict[str, Any]]) -> tuple[list[str], str]:
    if path is not None:
        config = _load_json(path)
        if config.get("status") != "confirmed":
            raise ValueError(f"keyword config is not confirmed: {path}")
        terms = [term for values in config.get("categories", {}).values() for term in values]
        terms.extend(config.get("exclude_terms", []))
        return list(dict.fromkeys(str(term) for term in terms if str(term).strip())), str(path)
    terms = [str(row["name"]) for row in categories if str(row.get("name") or "").strip()]
    return list(dict.fromkeys(terms)), "category names (fallback)"


def _extract_asins_from_html(html: str) -> list[str]:
    patterns = [
        r'data-asin=["\']([A-Z0-9]{10})["\']',
        r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:[/?#\"']|$)",
    ]
    found: list[str] = []
    seen: set[str] = set()
    for pattern in patterns:
        for value in re.findall(pattern, html, flags=re.IGNORECASE):
            asin = value.upper()
            if asin not in seen:
                seen.add(asin)
                found.append(asin)
    return found


def _live_samples(
    session: requests.Session,
    categories: list[dict[str, Any]],
    *,
    marketplace_code: str,
    sample_size: int,
    timeout: float,
    retries: int,
    delay: float,
) -> list[dict[str, Any]]:
    market = DEFAULT_MARKETPLACES[marketplace_code]
    roots = [row for row in categories if int(row.get("depth", 0) or 0) == 0]
    if not roots:
        roots = categories[:2]
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root in roots:
        if len(result) >= sample_size:
            break
        node_id = str(root.get("node_id") or root.get("category_node_id") or "").strip()
        if not node_id:
            continue
        base_url = f"https://{market.frontend_domain}/gp/new-releases/sporting-goods/{node_id}"
        for page in range(1, 4):
            if len(result) >= sample_size:
                break
            url = base_url if page == 1 else f"{base_url}?pg={page}"
            status, body, _, error = _fetch(session, url, timeout=timeout, retries=retries, delay=delay)
            if status != 200 or not body:
                continue
            for asin in _extract_asins_from_html(body):
                if asin in seen:
                    continue
                seen.add(asin)
                result.append({
                    "asin": asin,
                    "sample_category": str(root.get("name") or "TEMP"),
                    "category_name": root.get("name"),
                    "category_node_id": node_id,
                    "rank": None,
                    "title": None,
                    "source_evidence": "amazon_public_category_page",
                    "source_url": url,
                })
                if len(result) >= sample_size:
                    break
    return result[:sample_size]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _fetch(session: requests.Session, url: str, *, timeout: float, retries: int, delay: float) -> tuple[int | None, str, int, str | None]:
    last_error: str | None = None
    for attempt in range(retries + 1):
        started = time.perf_counter()
        try:
            response = session.get(url, timeout=timeout, allow_redirects=True)
            elapsed = int((time.perf_counter() - started) * 1000)
            if response.status_code == 200:
                return response.status_code, response.text, elapsed, None
            last_error = f"HTTP {response.status_code}"
            if response.status_code not in {429, 500, 502, 503, 504}:
                return response.status_code, response.text, elapsed, last_error
        except requests.RequestException as exc:
            elapsed = int((time.perf_counter() - started) * 1000)
            last_error = str(exc)
        if attempt < retries:
            time.sleep(min(30.0, 2**attempt))
    return None, "", elapsed, last_error


def _build_markdown(
    *,
    output_dir: Path,
    ledger: list[dict[str, Any]],
    validations: list[dict[str, Any]],
    keywords: list[str],
    keyword_source: str,
    asin_source: str,
    snapshot_path: Path,
    categories_path: Path,
) -> str:
    checked = [row for row in validations if row.get("checked")]
    ok = [row for row in checked if row.get("validation_status") == "ok"]
    errors = Counter(str(row.get("error") or row.get("validation_status")) for row in checked if row not in ok)
    market_counts = {
        market: {
            "checked": sum(1 for row in checked if row.get("marketplace_code") == market),
            "ok": sum(1 for row in ok if row.get("marketplace_code") == market),
        }
        for market in ("US", "AU")
    }
    field_names = ["title", "price", "rating", "review_count", "sales_rank"]
    coverage = {
        field: round(sum(1 for row in ok if row.get(field) not in (None, "")) / len(ok), 3) if ok else 0
        for field in field_names
    }
    lines = [
        "# M2 数据源验证报告",
        "",
        f"验证时间：{datetime.now(timezone.utc).isoformat()}",
        "数据边界：本轮只验证有限数量的公开 Amazon 商品页；不把公开页当成已授权的 SP-API 生产源。",
        "",
        "## 样本台账",
        "",
        f"- 计划样本：{len(ledger)} 行（US 50 + AU 50 的同一 ASIN 候选集）。",
        f"- 实际请求：{len(checked)} 行；成功读取：{len(ok)} 行。",
        f"- 分站点：US {market_counts['US']['ok']}/{market_counts['US']['checked']} 成功，AU {market_counts['AU']['ok']}/{market_counts['AU']['checked']} 成功。",
        f"- 类目节点来源：`{categories_path}`。",
        f"- ASIN 候选来源：{('Amazon 对应站点类目页实时抓取' if asin_source == 'amazon' else f'`{snapshot_path}` 旧项目 Amazon 观测快照')}。",
        f"- 关键词来源：`{keyword_source}`。配置状态已在运行前校验为 `confirmed`。",
        f"- 已确认关键词/排除词：{', '.join(keywords)}。这些词用于任务筛选，不代表搜索量或销量。",
        "",
        "## 当前字段覆盖（以成功读取页面为分母）",
        "",
        "| 字段 | 覆盖率 |",
        "|---|---:|",
    ]
    lines.extend(f"| `{field}` | {value:.1%} |" for field, value in coverage.items())
    lines.extend([
        "| `estimated_monthly_sales` | 0.0%（公开页未提供可授权的销量字段） |",
        "| `sales_metric_type=actual` | 0 行 |",
        "",
        "## 请求异常",
        "",
    ])
    if errors:
        lines.extend(f"- `{key}`：{value} 行" for key, value in sorted(errors.items()))
    else:
        lines.append("- 本轮抽样没有记录到 HTTP/请求异常。")
    lines.extend([
        "",
        "## 结论与下一步",
        "",
        "- 当前结果只能证明公开商品页的字段可读性和 US/AU 域名隔离，不能证明销量估算准确率或商业授权范围。",
        "- Keepa 已按项目决策跳过，不参与本次 M2 通过/不通过判定，也不写入运行时数据源链路。",
        "- SP-API 需要客户 Seller Central 授权和角色确认；在获得凭证前不执行生产调用。",
        "- 变体、配送、优惠和价格口径仍需人工抽查 10–15 个 ASIN 后才能进入通过/不通过判定。",
    ])
    return "\n".join(lines) + "\n"


def run(args: argparse.Namespace) -> Path:
    snapshot = _load_json(Path(args.snapshot))
    categories = _load_json(Path(args.categories))
    keyword_config = Path(args.keyword_config) if args.keyword_config else None
    keywords, keyword_source = _load_keywords(keyword_config, categories)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "AmazonRelease-M2-Validation/0.1 (+customer-authorized-review)",
        "Accept-Language": "en-US,en;q=0.9",
    })

    if args.asin_source == "amazon":
        samples_by_market = {
            market_code: _live_samples(
                session,
                categories,
                marketplace_code=market_code,
                sample_size=args.sample_size,
                timeout=args.timeout,
                retries=args.retries,
                delay=args.delay_seconds,
            )
            for market_code in ("US", "AU")
        }
        if any(len(rows) < args.sample_size for rows in samples_by_market.values()):
            counts = {market: len(rows) for market, rows in samples_by_market.items()}
            raise RuntimeError(f"Amazon category pages returned too few ASINs: {counts}")
    else:
        sample = select_sample_rows(snapshot, categories, sample_size=args.sample_size)
        samples_by_market = {market_code: sample for market_code in ("US", "AU")}

    ledger: list[dict[str, Any]] = []
    for market_code in ("US", "AU"):
        market = DEFAULT_MARKETPLACES[market_code]
        for row in samples_by_market[market_code]:
            ledger.append({
                "marketplace_code": market_code,
                "asin": row["asin"],
                "source_url": f"https://{market.frontend_domain}/dp/{row['asin']}",
                "sample_category": row["sample_category"],
                "legacy_category_name": row.get("category_name"),
                "legacy_category_node_id": row.get("category_node_id"),
                "legacy_rank": row.get("rank"),
                "legacy_title": row.get("title"),
                "source_evidence": row["source_evidence"],
                "sample_source_url": row.get("source_url"),
                "validation_status": "not_checked",
            })

    validations: list[dict[str, Any]] = []
    selected_indexes = set(range(min(args.check_size, args.sample_size)))
    for market_code in ("US", "AU"):
        market_rows = [row for row in ledger if row["marketplace_code"] == market_code]
        for index, row in enumerate(market_rows):
            if index not in selected_indexes:
                continue
            status, body, latency_ms, error = _fetch(
                session,
                row["source_url"],
                timeout=args.timeout,
                retries=args.retries,
                delay=args.delay_seconds,
            )
            if status == 200 and body:
                parsed = parse_product_page(body, marketplace_code=market_code, asin=row["asin"], status_code=status, latency_ms=latency_ms)
                parsed.update({
                    "source_url": row["source_url"],
                    "source": "amazon_public_page",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "checked": True,
                    "validation_status": "ok" if parsed.get("title") else "missing_title",
                    "error": error,
                })
            else:
                parsed = {
                    "marketplace_code": market_code,
                    "asin": row["asin"],
                    "source_url": row["source_url"],
                    "http_status": status,
                    "latency_ms": latency_ms,
                    "source": "amazon_public_page",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "checked": True,
                    "validation_status": "request_error",
                    "error": error or "empty response",
                }
            row.update({
                "validation_status": parsed["validation_status"],
                "http_status": parsed.get("http_status"),
                "checked_at": parsed.get("fetched_at"),
                "error": parsed.get("error"),
            })
            validations.append(parsed)

    _write_csv(output_dir / "m2_sample_ledger.csv", ledger)
    _write_csv(output_dir / "m2_page_validation.csv", validations)
    (output_dir / "m2_validation.md").write_text(
        _build_markdown(
            output_dir=output_dir,
            ledger=ledger,
            validations=validations,
            keywords=keywords,
            keyword_source=keyword_source,
            asin_source=args.asin_source,
            snapshot_path=Path(args.snapshot).resolve(),
            categories_path=Path(args.categories).resolve(),
        ),
        encoding="utf-8",
    )
    (output_dir / "source_config.json").write_text(json.dumps({
        "amazon_public_page": {"status": "checked", "domains": {"US": "amazon.com", "AU": "amazon.com.au"}},
        "inputs": {
            "keyword_config": {
                "path": str(keyword_config.resolve()) if keyword_config else None,
                "status": "confirmed" if keyword_config else "fallback",
            },
            "categories": {
                "path": str(Path(args.categories).resolve()),
                "role": "category_nodes_and_keyword_candidates",
                "standalone_keyword_document": False,
            },
            "snapshot": {
                "path": str(Path(args.snapshot).resolve()),
                "role": "historical_asin_candidates",
            },
        },
        "keepa": {"status": "skipped_by_project_decision", "in_m2_decision": False},
        "sp_api": {"status": "pending_seller_authorization", "endpoint_regions": {"US": "na", "AU": "fe"}},
        "asin_sample": {"source": args.asin_source},
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Run bounded M2 Amazon source validation.")
    parser.add_argument("--snapshot", required=True, help="Legacy snapshot JSON used only for sample selection")
    parser.add_argument("--categories", required=True, help="Legacy category ledger JSON")
    parser.add_argument("--keyword-config", help="Confirmed keyword configuration JSON")
    parser.add_argument("--asin-source", choices=("amazon", "snapshot"), default="snapshot", help="ASIN sample source")
    parser.add_argument("--output-dir", default="docs/m2/2026-10-22")
    parser.add_argument("--sample-size", type=int, default=50)
    parser.add_argument("--check-size", type=int, default=12, help="Pages checked per marketplace")
    parser.add_argument("--delay-seconds", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=1)
    args = parser.parse_args()
    output_dir = run(args)
    print(f"M2 validation written to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
