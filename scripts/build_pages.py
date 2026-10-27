from __future__ import annotations

import html
import re
import shutil
from pathlib import Path


DATE_RE = re.compile(r"release_(\d{4}-\d{2}-\d{2})\.html$")


def build(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    reports = sorted(
        ((match.group(1), path) for path in source.glob("release_*.html") if (match := DATE_RE.match(path.name))),
        reverse=True,
    )
    for date, path in reports:
        (destination / path.name).write_bytes(path.read_bytes())
    image_source = source / "images"
    if image_source.exists():
        shutil.copytree(image_source, destination / "images", dirs_exist_ok=True)
    links = "\n".join(
        f'<li><a href="{html.escape(path.name)}">{html.escape(date)} 每日竞品分析报告</a></li>'
        for date, path in reports
    ) or "<li>暂无日报</li>"
    latest = reports[0][0] if reports else "暂无"
    index = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AmazonRelease 每日竞品分析</title><style>body{{font:16px/1.6 system-ui,sans-serif;max-width:820px;margin:48px auto;padding:0 20px;color:#17202a}}a{{color:#155e75}}li{{margin:12px 0}}</style><h1>AmazonRelease 每日竞品分析</h1><p>最新报告：{html.escape(latest)}。数据为新品与竞品热度代理信号，不等同于确认销量。</p><ul>{links}</ul></html>'''
    (destination / "index.html").write_text(index, encoding="utf-8")


if __name__ == "__main__":
    build(Path("data/reports"), Path("site"))
