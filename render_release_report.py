from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from amazon_release.report import render_html


def main() -> int:
    parser = argparse.ArgumentParser(description="Render an Amazon release JSON snapshot as a visual HTML report.")
    parser.add_argument("--snapshot", required=True, help="Snapshot JSON path")
    parser.add_argument("--new-products", help="CSV of products first observed today")
    parser.add_argument("--output", required=True, help="HTML output path")
    parser.add_argument("--date", required=True, help="Report date, YYYY-MM-DD")
    args = parser.parse_args()

    records = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    new_asins: set[str] = set()
    if args.new_products:
        with Path(args.new_products).open(newline="", encoding="utf-8-sig") as handle:
            new_asins = {row["asin"] for row in csv.DictReader(handle) if row.get("asin")}
    output = render_html(records, args.output, report_date=args.date, new_asins=new_asins)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
