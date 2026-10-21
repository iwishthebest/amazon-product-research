import json

from amazon_release.cli import build_parser, main


def test_cli_exposes_delay_override():
    args = build_parser().parse_args(["--delay-seconds", "0"])
    assert args.delay_seconds == 0


def test_fixture_mode_generates_daily_report(tmp_path):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    (fixture_dir / "category_5044228051.html").write_text(
        '<div data-asin="B0ABC12345"><a href="/dp/B0ABC12345"><span class="p13n-sc-truncate">Pilates Ring</span></a></div>',
        encoding="utf-8",
    )
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "marketplace_id": "A39IBJ37TRP1C6",
        "roots": [{
            "name": "Pilates",
            "node_id": "5044228051",
            "url": "https://www.amazon.com.au/gp/new-releases/sporting-goods/5044228051",
        }],
        "discover_subcategories": False,
        "delay_seconds": 0,
    }), encoding="utf-8")

    exit_code = main([
        "--config", str(config),
        "--fixture-dir", str(fixture_dir),
        "--db", str(tmp_path / "products.sqlite3"),
        "--output-dir", str(tmp_path / "reports"),
    ])

    assert exit_code == 0
    reports = list((tmp_path / "reports").glob("new_products_*.csv"))
    assert len(reports) == 1
    assert "B0ABC12345" in reports[0].read_text(encoding="utf-8-sig")
