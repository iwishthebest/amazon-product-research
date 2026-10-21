from __future__ import annotations

import argparse
import json
from pathlib import Path

from amazon_release.images import enrich_snapshot_images
from amazon_release.report import render_html


def main() -> int:
    parser = argparse.ArgumentParser(description="Download real Amazon product images and rebuild the HTML report.")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--new-products", required=True)
    parser.add_argument("--output-html", required=True)
    parser.add_argument("--delay-seconds", type=float, default=0.5)
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    args = parser.parse_args()
    snapshot = Path(args.snapshot)
    result = enrich_snapshot_images(
        snapshot,
        snapshot.parent / "images",
        delay_seconds=args.delay_seconds,
        timeout_seconds=args.timeout_seconds,
    )
    records = json.loads(snapshot.read_text(encoding="utf-8"))
    import csv
    with Path(args.new_products).open(newline="", encoding="utf-8-sig") as handle:
        new_asins = {row["asin"] for row in csv.DictReader(handle) if row.get("asin")}
    render_html(records, args.output_html, report_date=snapshot.stem.removeprefix("snapshot_"), new_asins=new_asins)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
