from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from amazon_release.report import render_combined_html


def _load_new(path: Path) -> set[str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return {row["asin"] for row in csv.DictReader(handle) if row.get("asin")}


def main() -> int:
    parser = argparse.ArgumentParser(description="Render combined US/AU Amazon release report.")
    parser.add_argument("--us-snapshot", required=True)
    parser.add_argument("--us-new-products", required=True)
    parser.add_argument("--au-snapshot", required=True)
    parser.add_argument("--au-new-products", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--date", required=True)
    args = parser.parse_args()
    records = {
        "us": json.loads(Path(args.us_snapshot).read_text(encoding="utf-8")),
        "au": json.loads(Path(args.au_snapshot).read_text(encoding="utf-8")),
    }
    new = {"us": _load_new(Path(args.us_new_products)), "au": _load_new(Path(args.au_new_products))}
    print(render_combined_html(records, args.output, report_date=args.date, site_new_asins=new))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
