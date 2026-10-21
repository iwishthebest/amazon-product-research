from __future__ import annotations

import csv
import json
import os
import queue
import threading
import webbrowser
import tkinter as tk
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, BooleanVar, StringVar, Text, Tk, filedialog, messagebox, ttk
from typing import Any

from .cli import DEFAULT_CONFIG, load_config, run_once
from .report import build_product_view, render_html


def _number(values: dict[str, Any], key: str, cast: type, *, minimum: float | int | None = None) -> Any:
    raw = values.get(key)
    if raw in (None, ""):
        return None
    try:
        value = cast(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} 必须是有效数字") from exc
    if minimum is not None and value < minimum:
        raise ValueError(f"{key} 必须大于等于 {minimum}")
    return value


def build_gui_config(values: dict[str, Any]) -> dict[str, Any]:
    """Convert form values into the existing CLI configuration contract."""
    config_path = str(values.get("config_path") or "").strip()
    config = load_config(config_path or None)
    overrides: dict[str, Any] = {}
    for key, cast, minimum in (
        ("delay_seconds", float, 0),
        ("timeout_seconds", float, 1),
        ("max_retries", int, 0),
        ("max_pages", int, 1),
        ("max_category_depth", int, 0),
    ):
        value = _number(values, key, cast, minimum=minimum)
        if value is not None:
            overrides[key] = value
    timezone = str(values.get("timezone") or "").strip()
    if timezone:
        overrides["timezone"] = timezone
    config.update(overrides)
    return config


def run_gui_job(
    config: dict[str, Any],
    fixture_dir: str | Path | None,
    db_path: str | Path,
    output_dir: str | Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run one collection using the same pipeline as the command-line app."""
    result = run_once(
        config,
        fixture_dir=fixture_dir,
        db_path=db_path,
        output_dir=output_dir,
        dry_run=dry_run,
    )
    snapshot_path = Path(result["snapshot"])
    records = json.loads(snapshot_path.read_text(encoding="utf-8"))
    new_asins: set[str] = set()
    report_csv = Path(result["report"])
    if report_csv.exists():
        with report_csv.open(encoding="utf-8-sig", newline="") as handle:
            new_asins = {str(row.get("asin") or "").strip().upper() for row in csv.DictReader(handle)}
    report_date = snapshot_path.stem.removeprefix("snapshot_")
    html_path = snapshot_path.parent / f"release_{report_date}.html"
    render_html(records, html_path, report_date=report_date, new_asins=new_asins)
    result["html"] = str(html_path)
    return result


def discover_result_files(output_dir: str | Path) -> dict[str, Path | None]:
    output = Path(output_dir)

    def latest(pattern: str) -> Path | None:
        matches = sorted(output.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
        return matches[0] if matches else None

    return {
        "snapshot": latest("snapshot_*.json"),
        "new_products": latest("new_products_*.csv"),
        "html": latest("release_*.html"),
        "categories": latest("categories_*.json"),
    }


def load_result_rows(snapshot_path: str | Path | None, new_products_path: str | Path | None = None) -> list[dict[str, Any]]:
    if not snapshot_path or not Path(snapshot_path).exists():
        return []
    new_asins: set[str] = set()
    if new_products_path and Path(new_products_path).exists():
        with Path(new_products_path).open(encoding="utf-8-sig", newline="") as handle:
            new_asins = {str(row.get("asin") or "").strip().upper() for row in csv.DictReader(handle)}
    payload = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    return [build_product_view(record, new_asins) for record in payload if isinstance(record, dict)]


def filter_product_rows(
    rows: list[dict[str, Any]],
    *,
    query: str = "",
    category: str = "",
    new_only: bool = False,
    min_score: int = 0,
) -> list[dict[str, Any]]:
    """Return matching rows without changing the source list."""
    normalized_query = str(query or "").strip().casefold()
    normalized_category = str(category or "").strip()
    threshold = int(min_score or 0)
    matches: list[dict[str, Any]] = []
    for row in rows:
        haystack = f"{row.get('title', '')} {row.get('asin', '')} {row.get('category_name', '')}".casefold()
        if normalized_query and normalized_query not in haystack:
            continue
        if normalized_category and str(row.get("category_name") or "") != normalized_category:
            continue
        if new_only and not bool(row.get("is_new")):
            continue
        try:
            score = int(row.get("score") or 0)
        except (TypeError, ValueError):
            score = 0
        if score < threshold:
            continue
        matches.append(row)
    return matches


def sort_product_rows(
    rows: list[dict[str, Any]],
    *,
    key: str = "score",
    descending: bool = True,
) -> list[dict[str, Any]]:
    """Sort rows for the workbench while preserving the source list."""
    numeric_keys = {"rank", "price", "rating", "review_count", "score"}

    def value(row: dict[str, Any]) -> Any:
        raw = row.get(key)
        if key in numeric_keys:
            try:
                return float(raw) if raw not in (None, "") else float("-inf")
            except (TypeError, ValueError):
                return float("-inf")
        return str(raw or "").casefold()

    return sorted(rows, key=value, reverse=descending)


def discover_run_history(output_dir: str | Path) -> list[dict[str, Any]]:
    """Build a compact, newest-first index of saved daily snapshots."""
    output = Path(output_dir)
    history: list[dict[str, Any]] = []
    for snapshot in sorted(output.glob("snapshot_*.json"), reverse=True):
        date = snapshot.stem.removeprefix("snapshot_")
        csv_path = output / f"new_products_{date}.csv"
        html_path = output / f"release_{date}.html"
        products: int | None = None
        try:
            payload = json.loads(snapshot.read_text(encoding="utf-8"))
            products = len(payload) if isinstance(payload, list) else 0
        except (OSError, json.JSONDecodeError):
            products = None
        history.append({
            "date": date,
            "snapshot": snapshot,
            "new_products": csv_path,
            "html": html_path,
            "has_csv": csv_path.exists(),
            "has_html": html_path.exists(),
            "products": products,
        })
    return history


def export_product_rows_csv(rows: list[dict[str, Any]], output_path: str | Path) -> Path:
    """Export the current workbench selection in a seller-friendly CSV."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "asin", "title", "category_name", "rank", "price", "currency", "rating", "review_count",
        "score", "heat_label", "is_new", "competition", "improvement", "product_url", "observed_at",
    ]
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)
    return output


def _summarize(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "products": len(rows),
        "new_products": sum(bool(row.get("is_new")) for row in rows),
        "hot_products": sum(str(row.get("heat_label")) == "高热度信号" for row in rows),
        "categories": len({str(row.get("category_name") or "未分类") for row in rows}),
    }


class AmazonReleaseApp:
    def __init__(self, root: Tk | None = None) -> None:
        self.root = root or Tk()
        self.theme_name = "seller-light"
        self._configure_style()
        self.root.title("Amazon Release · 卖家新品工作台")
        self.root.geometry("1420x900")
        self.root.minsize(1120, 720)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.stop_requested = False
        self.rows: list[dict[str, Any]] = []
        self.filtered_rows: list[dict[str, Any]] = []
        self.result_files: dict[str, Path | None] = {}
        self.history_entries: list[dict[str, Any]] = []
        self.vars = {
            "config_path": StringVar(value=""),
            "db_path": StringVar(value="data/amazon_release.sqlite3"),
            "output_dir": StringVar(value="data/reports"),
            "fixture_dir": StringVar(value="tests/fixtures"),
            "timezone": StringVar(value="Australia/Sydney"),
            "delay_seconds": StringVar(value="2"),
            "timeout_seconds": StringVar(value="30"),
            "max_retries": StringVar(value="3"),
            "max_pages": StringVar(value="10"),
            "max_category_depth": StringVar(value="2"),
            "use_fixture": BooleanVar(value=False),
            "dry_run": BooleanVar(value=False),
            "search": StringVar(value=""),
            "category": StringVar(value=""),
            "new_only": BooleanVar(value=False),
            "score_min": StringVar(value="0"),
            "sort_key": StringVar(value="机会评分"),
            "sort_desc": BooleanVar(value=True),
        }
        self.status_var = StringVar(value="就绪 · 选择配置后可开始采集")
        self.result_count_var = StringVar(value="0 个商品")
        self.last_updated_var = StringVar(value="暂无本地结果")
        self.empty_products_var = StringVar(value="还没有符合条件的商品")
        self.metric_vars = {key: StringVar(value="0") for key in ("products", "new_products", "hot_products", "categories")}
        self.detail_title_var = StringVar(value="选择一个商品查看详细分析")
        self.detail_meta_var = StringVar(value="")
        self.detail_link_var = StringVar(value="")
        self._build()
        self._refresh_results()
        self.root.after(150, self._drain_events)

    def _configure_style(self) -> None:
        self.root.configure(background="#f4f7fb")
        self.root.option_add("*Font", ("Segoe UI", 10))
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("App.TFrame", background="#f4f7fb")
        style.configure("Surface.TFrame", background="#ffffff")
        style.configure("Header.TFrame", background="#0d2841")
        style.configure("Header.TLabel", background="#0d2841", foreground="#f8fafc")
        style.configure("HeaderMuted.TLabel", background="#0d2841", foreground="#b8c7d9")
        style.configure("HeaderStatus.TLabel", background="#174a65", foreground="#e0f2fe", padding=(10, 5))
        style.configure("Title.TLabel", background="#f4f7fb", foreground="#102a43", font=("Segoe UI", 16, "bold"))
        style.configure("Muted.TLabel", background="#f4f7fb", foreground="#64748b")
        style.configure("SurfaceMuted.TLabel", background="#ffffff", foreground="#64748b")
        style.configure("Card.TLabelframe", background="#ffffff", bordercolor="#e2e8f0", relief="solid")
        style.configure("Card.TLabelframe.Label", background="#ffffff", foreground="#475569", font=("Segoe UI", 10, "bold"))
        style.configure("KpiValue.TLabel", background="#ffffff", foreground="#0f4c5c", font=("Segoe UI", 25, "bold"))
        style.configure("Primary.TButton", background="#0f766e", foreground="#ffffff", padding=(14, 8), font=("Segoe UI", 10, "bold"))
        style.map("Primary.TButton", background=[("active", "#115e59"), ("disabled", "#94a3b8")])
        style.configure("Secondary.TButton", padding=(10, 7))
        style.configure("Danger.TButton", foreground="#b91c1c", padding=(10, 7))
        style.configure("TNotebook", background="#f4f7fb", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(18, 9), foreground="#52606d")
        style.map("TNotebook.Tab", foreground=[("selected", "#0f766e")])
        style.configure("Treeview", background="#ffffff", fieldbackground="#ffffff", foreground="#1e293b", rowheight=32, borderwidth=0)
        style.configure("Treeview.Heading", background="#eef3f8", foreground="#475569", relief="flat", padding=(8, 7), font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#dbeafe")], foreground=[("selected", "#0f172a")])

    def _build(self) -> None:
        outer = ttk.Frame(self.root, style="App.TFrame", padding=(18, 16))
        outer.pack(fill=BOTH, expand=True)
        header = ttk.Frame(outer, style="Header.TFrame", padding=(22, 17))
        header.pack(fill=X)
        brand = ttk.Frame(header, style="Header.TFrame")
        brand.pack(side=LEFT)
        ttk.Label(brand, text="AR", style="Header.TLabel", font=("Segoe UI", 20, "bold")).pack(side=LEFT, padx=(0, 12))
        brand_text = ttk.Frame(brand, style="Header.TFrame")
        brand_text.pack(side=LEFT)
        ttk.Label(brand_text, text="Amazon Release", style="Header.TLabel", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(brand_text, text="卖家新品与产品开发工作台", style="HeaderMuted.TLabel").pack(anchor="w")
        ttk.Label(header, textvariable=self.status_var, style="HeaderStatus.TLabel").pack(side=RIGHT, anchor="center")

        actions = ttk.Frame(outer, style="App.TFrame", padding=(0, 12, 0, 8))
        actions.pack(fill=X)
        self.start_button = ttk.Button(actions, text="开始采集", style="Primary.TButton", command=self.start_run)
        self.start_button.pack(side=LEFT)
        self.stop_button = ttk.Button(actions, text="停止请求", style="Danger.TButton", command=self.request_stop, state="disabled")
        self.stop_button.pack(side=LEFT, padx=(8, 0))
        ttk.Separator(actions, orient="vertical").pack(side=LEFT, fill="y", padx=14)
        ttk.Button(actions, text="刷新结果", style="Secondary.TButton", command=self._refresh_results).pack(side=LEFT)
        ttk.Button(actions, text="打开最新报告", style="Secondary.TButton", command=self.open_report).pack(side=LEFT, padx=7)
        ttk.Button(actions, text="输出目录", style="Secondary.TButton", command=self.open_output).pack(side=LEFT)
        ttk.Label(actions, textvariable=self.last_updated_var, style="Muted.TLabel").pack(side=RIGHT)

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill=BOTH, expand=True)
        overview = ttk.Frame(self.notebook, style="App.TFrame", padding=(4, 4))
        products = ttk.Frame(self.notebook, style="App.TFrame", padding=(4, 4))
        history = ttk.Frame(self.notebook, style="App.TFrame", padding=(4, 4))
        settings = ttk.Frame(self.notebook, style="App.TFrame", padding=(4, 4))
        self.notebook.add(overview, text="概览")
        self.notebook.add(products, text="商品工作台")
        self.notebook.add(history, text="运行历史")
        self.notebook.add(settings, text="设置")
        self._build_overview(overview)
        self._build_products(products)
        self._build_history(history)
        self._build_settings(settings)

    def _path_row(self, parent: ttk.Widget, row: int, label: str, key: str, button: str, command: Any) -> None:
        ttk.Label(parent, text=label, width=14).grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(parent, textvariable=self.vars[key]).grid(row=row, column=1, sticky="ew", padx=8, pady=5)
        ttk.Button(parent, text=button, command=command).grid(row=row, column=2, pady=5)

    def _build_overview(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="今日工作台", style="Title.TLabel").pack(anchor="w", pady=(7, 2))
        ttk.Label(parent, text="用榜内信号快速筛选值得进一步核验的商品，所有结论都保留证据边界。", style="Muted.TLabel").pack(anchor="w", pady=(0, 14))
        metrics = ttk.Frame(parent, style="App.TFrame")
        metrics.pack(fill=X)
        labels = {"products": ("商品总数", "当前快照中的全部商品"), "new_products": ("本次首次发现", "本地历史中第一次看到"), "hot_products": ("高热度信号", "新品榜内的优先线索"), "categories": ("覆盖子类目", "当前快照的分类数")}
        for index, key in enumerate(self.metric_vars):
            box = ttk.LabelFrame(metrics, text=labels[key][0], style="Card.TLabelframe", padding=(16, 12))
            box.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 8, 0))
            ttk.Label(box, textvariable=self.metric_vars[key], style="KpiValue.TLabel").pack(anchor="w")
            ttk.Label(box, text=labels[key][1], style="SurfaceMuted.TLabel").pack(anchor="w", pady=(3, 0))
            metrics.columnconfigure(index, weight=1)
        below = ttk.Panedwindow(parent, orient="horizontal")
        below.pack(fill=BOTH, expand=True, pady=(18, 0))
        candidate_panel = ttk.Frame(below, style="Surface.TFrame", padding=14)
        log_panel = ttk.Frame(below, style="Surface.TFrame", padding=14)
        below.add(candidate_panel, weight=3)
        below.add(log_panel, weight=2)
        ttk.Label(candidate_panel, text="优先核验候选", font=("Segoe UI", 12, "bold"), background="#ffffff", foreground="#102a43").pack(anchor="w")
        ttk.Label(candidate_panel, text="按机会评分排序，仅用于安排人工研究优先级。", style="SurfaceMuted.TLabel").pack(anchor="w", pady=(2, 9))
        columns = ("rank", "title", "score", "heat", "new")
        self.candidate_tree = ttk.Treeview(candidate_panel, columns=columns, show="headings", height=9)
        for column, heading, width in (("rank", "排名", 70), ("title", "商品", 360), ("score", "机会评分", 90), ("heat", "热度", 120), ("new", "首次发现", 90)):
            self.candidate_tree.heading(column, text=heading)
            self.candidate_tree.column(column, width=width, anchor="w")
        self.candidate_tree.pack(fill=BOTH, expand=True)
        self.candidate_tree.bind("<Double-1>", self._open_candidate)
        ttk.Label(log_panel, text="运行日志", font=("Segoe UI", 12, "bold"), background="#ffffff", foreground="#102a43").pack(anchor="w")
        ttk.Label(log_panel, text="采集过程、产物路径和错误会保存在这里。", style="SurfaceMuted.TLabel").pack(anchor="w", pady=(2, 9))
        self.log = Text(log_panel, height=12, state="disabled", wrap="word", background="#f8fafc", foreground="#334155", relief="flat", padx=8, pady=8)
        self.log.pack(fill=BOTH, expand=True)
        ttk.Label(parent, text="证据边界：首次发现是本地程序首次观察时间；新品榜排名是榜内热度信号，不代表销量或利润。", foreground="#9a3412", background="#f4f7fb").pack(anchor="w", pady=(10, 0))

    def _build_products(self, parent: ttk.Frame) -> None:
        toolbar = ttk.Frame(parent, style="Surface.TFrame", padding=(12, 10))
        toolbar.pack(fill=X, pady=(7, 10))
        ttk.Label(toolbar, text="搜索", style="SurfaceMuted.TLabel").pack(side=LEFT)
        ttk.Entry(toolbar, textvariable=self.vars["search"], width=27).pack(side=LEFT, padx=(6, 12))
        ttk.Label(toolbar, text="类目", style="SurfaceMuted.TLabel").pack(side=LEFT)
        self.category_combo = ttk.Combobox(toolbar, textvariable=self.vars["category"], width=15, state="readonly", values=[""])
        self.category_combo.pack(side=LEFT, padx=(6, 12))
        ttk.Label(toolbar, text="评分≥", style="SurfaceMuted.TLabel").pack(side=LEFT)
        score_combo = ttk.Combobox(toolbar, textvariable=self.vars["score_min"], values=["0", "40", "60", "70", "80"], width=5, state="readonly")
        score_combo.pack(side=LEFT, padx=(6, 12))
        ttk.Label(toolbar, text="排序", style="SurfaceMuted.TLabel").pack(side=LEFT)
        sort_combo = ttk.Combobox(toolbar, textvariable=self.vars["sort_key"], values=["机会评分", "新品榜排名", "评论数", "评分", "标题"], width=12, state="readonly")
        sort_combo.pack(side=LEFT, padx=(6, 8))
        ttk.Checkbutton(toolbar, text="降序", variable=self.vars["sort_desc"], command=self._apply_filters).pack(side=LEFT)
        ttk.Checkbutton(toolbar, text="仅首次发现", variable=self.vars["new_only"], command=self._apply_filters).pack(side=LEFT, padx=(8, 0))
        ttk.Label(toolbar, textvariable=self.result_count_var, style="SurfaceMuted.TLabel").pack(side=RIGHT)
        self.vars["search"].trace_add("write", lambda *_: self._apply_filters())
        self.vars["category"].trace_add("write", lambda *_: self._apply_filters())
        self.vars["score_min"].trace_add("write", lambda *_: self._apply_filters())
        self.vars["sort_key"].trace_add("write", lambda *_: self._apply_filters())
        ttk.Button(toolbar, text="导出当前筛选", style="Secondary.TButton", command=self.export_current).pack(side=RIGHT, padx=(0, 10))
        pane = ttk.Panedwindow(parent, orient="horizontal")
        pane.pack(fill=BOTH, expand=True)
        table_panel = ttk.Frame(pane, style="Surface.TFrame", padding=10)
        detail_panel = ttk.Frame(pane, style="Surface.TFrame", padding=16)
        pane.add(table_panel, weight=4)
        pane.add(detail_panel, weight=2)
        columns = ("rank", "title", "asin", "category", "price", "rating", "reviews", "score", "heat", "new")
        self.tree = ttk.Treeview(table_panel, columns=columns, show="headings", selectmode="browse")
        headings = {"rank": "排名", "title": "商品标题", "asin": "ASIN", "category": "类目", "price": "价格", "rating": "评分", "reviews": "评论", "score": "机会评分", "heat": "热度", "new": "首次发现"}
        widths = {"rank": 55, "title": 300, "asin": 110, "category": 95, "price": 85, "rating": 60, "reviews": 70, "score": 75, "heat": 105, "new": 75}
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="w")
        self.tree.tag_configure("new", background="#eff6ff")
        yscroll = ttk.Scrollbar(table_panel, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_panel, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        yscroll.pack(side=RIGHT, fill=Y)
        xscroll.pack(side="bottom", fill=X)
        self.tree.bind("<<TreeviewSelect>>", self._show_selected_detail)
        self.tree.bind("<Double-1>", self._open_selected_product)
        ttk.Label(detail_panel, text="商品分析", background="#ffffff", foreground="#102a43", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(detail_panel, textvariable=self.detail_title_var, background="#ffffff", foreground="#0f766e", font=("Segoe UI", 12, "bold"), wraplength=300).pack(anchor="w", pady=(15, 4))
        ttk.Label(detail_panel, textvariable=self.detail_meta_var, style="SurfaceMuted.TLabel", wraplength=320).pack(anchor="w")
        self.detail_body = Text(detail_panel, height=14, state="disabled", wrap="word", background="#f8fafc", foreground="#334155", relief="flat", padx=10, pady=10)
        self.detail_body.pack(fill=BOTH, expand=True, pady=(14, 10))
        detail_actions = ttk.Frame(detail_panel, style="Surface.TFrame")
        detail_actions.pack(fill=X)
        ttk.Button(detail_actions, text="复制 ASIN", command=self.copy_selected_asin).pack(side=LEFT)
        ttk.Button(detail_actions, text="打开商品页", style="Primary.TButton", command=self._open_selected_product).pack(side=RIGHT)
        self.empty_products_label = ttk.Label(table_panel, textvariable=self.empty_products_var, style="SurfaceMuted.TLabel")

    def _build_history(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="运行历史", style="Title.TLabel").pack(anchor="w", pady=(7, 2))
        ttk.Label(parent, text="每次运行都会留下快照、CSV 和 HTML 报告，便于复盘不同日期的榜单变化。", style="Muted.TLabel").pack(anchor="w", pady=(0, 14))
        toolbar = ttk.Frame(parent, style="Surface.TFrame", padding=10)
        toolbar.pack(fill=X, pady=(0, 10))
        ttk.Button(toolbar, text="刷新历史", command=self._refresh_history).pack(side=LEFT)
        ttk.Button(toolbar, text="打开选中报告", command=self.open_selected_history).pack(side=LEFT, padx=8)
        ttk.Label(toolbar, text="HTML 是可视化报告；CSV 适合继续在 Excel 中处理。", style="SurfaceMuted.TLabel").pack(side=RIGHT)
        history_panel = ttk.Frame(parent, style="Surface.TFrame", padding=10)
        history_panel.pack(fill=BOTH, expand=True)
        columns = ("date", "products", "csv", "html", "snapshot")
        self.history_tree = ttk.Treeview(history_panel, columns=columns, show="headings", selectmode="browse")
        for column, heading, width in (("date", "日期", 150), ("products", "商品数", 100), ("csv", "CSV", 100), ("html", "HTML 报告", 120), ("snapshot", "快照文件", 260)):
            self.history_tree.heading(column, text=heading)
            self.history_tree.column(column, width=width, anchor="w")
        self.history_tree.pack(fill=BOTH, expand=True)
        self.history_tree.bind("<Double-1>", lambda _event: self.open_selected_history())

    def _build_settings(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="采集设置", style="Title.TLabel").pack(anchor="w", pady=(7, 2))
        ttk.Label(parent, text="建议先保存一份客户专用配置；在线运行前请确认数据访问授权和请求频率。", style="Muted.TLabel").pack(anchor="w", pady=(0, 14))
        card = ttk.LabelFrame(parent, text="路径与数据源", style="Card.TLabelframe", padding=16)
        card.pack(fill=X)
        self._path_row(card, 0, "配置文件", "config_path", "选择 JSON", self._choose_config)
        self._path_row(card, 1, "SQLite 数据库", "db_path", "选择文件", self._choose_db)
        self._path_row(card, 2, "输出目录", "output_dir", "选择目录", self._choose_output)
        self._path_row(card, 3, "离线 fixture", "fixture_dir", "选择目录", self._choose_fixture)
        card.columnconfigure(1, weight=1)
        options = ttk.LabelFrame(parent, text="抓取参数", style="Card.TLabelframe", padding=16)
        options.pack(fill=X, pady=(14, 0))
        fields = [("请求延迟（秒）", "delay_seconds"), ("超时（秒）", "timeout_seconds"), ("最大重试", "max_retries"), ("每类最多页数", "max_pages"), ("分类发现深度", "max_category_depth"), ("时区", "timezone")]
        for index, (label, key) in enumerate(fields):
            row, col = divmod(index, 2)
            ttk.Label(options, text=label).grid(row=row, column=col * 2, sticky="w", padx=(0, 8), pady=7)
            ttk.Entry(options, textvariable=self.vars[key], width=24).grid(row=row, column=col * 2 + 1, sticky="ew", padx=(0, 20), pady=7)
        ttk.Checkbutton(options, text="使用离线 fixture（不联网）", variable=self.vars["use_fixture"]).grid(row=3, column=0, columnspan=2, sticky="w", pady=(9, 0))
        ttk.Checkbutton(options, text="干跑：不更新历史去重状态", variable=self.vars["dry_run"]).grid(row=3, column=2, columnspan=2, sticky="w", pady=(9, 0))
        for col in (1, 3):
            options.columnconfigure(col, weight=1)
        buttons = ttk.Frame(parent, style="App.TFrame")
        buttons.pack(fill=X, pady=(14, 0))
        ttk.Button(buttons, text="加载配置文件", command=self._load_config_from_field).pack(side=LEFT)
        ttk.Button(buttons, text="保存当前配置", style="Primary.TButton", command=self.save_config).pack(side=LEFT, padx=8)
        ttk.Label(parent, text="默认输出：JSON 快照、CSV 首次发现、SQLite 历史和 HTML 选品报告。", style="Muted.TLabel").pack(anchor="w", pady=(16, 0))

    def _form_values(self) -> dict[str, Any]:
        excluded = {"use_fixture", "dry_run", "search", "category", "new_only", "score_min", "sort_key", "sort_desc"}
        return {key: variable.get() for key, variable in self.vars.items() if key not in excluded}

    def _sort_key(self) -> str:
        return {"机会评分": "score", "新品榜排名": "rank", "评论数": "review_count", "评分": "rating", "标题": "title"}.get(self.vars["sort_key"].get(), "score")

    def start_run(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        try:
            config = build_gui_config(self._form_values())
            fixture = self.vars["fixture_dir"].get().strip() if self.vars["use_fixture"].get() else None
            if fixture and not Path(fixture).exists():
                raise ValueError("离线 fixture 目录不存在，请重新选择")
            db_path = self.vars["db_path"].get().strip()
            output_dir = self.vars["output_dir"].get().strip()
            if not db_path or not output_dir:
                raise ValueError("数据库和输出目录不能为空")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("设置有误", str(exc))
            return
        self._write_log("开始采集，请保持窗口打开……")
        self.status_var.set("运行中 · 正在采集")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.stop_requested = False
        self.worker = threading.Thread(target=self._worker_run, args=(config, fixture, db_path, output_dir, self.vars["dry_run"].get()), daemon=True)
        self.worker.start()

    def _worker_run(self, config: dict[str, Any], fixture: str | None, db_path: str, output_dir: str, dry_run: bool) -> None:
        try:
            result = run_gui_job(config, fixture, db_path, output_dir, dry_run)
        except Exception as exc:  # noqa: BLE001 - surface operational errors in the GUI
            self.events.put(("error", exc))
        else:
            self.events.put(("done", result))

    def request_stop(self) -> None:
        if self.worker and self.worker.is_alive():
            self.stop_requested = True
            self.stop_button.configure(state="disabled")
            self.status_var.set("停止请求已发出 · 当前步骤完成后结束")
            self._write_log("已发出停止请求。网络请求不会被强制中断，当前步骤完成后结束。")

    def _drain_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "done":
                    self._handle_done(payload)
                else:
                    self._handle_error(payload)
        except queue.Empty:
            pass
        self.root.after(150, self._drain_events)

    def _handle_done(self, result: dict[str, Any]) -> None:
        self.worker = None
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.status_var.set(f"完成 · {result.get('products', 0)} 个商品 · 新增 {result.get('new_products', 0)} 个")
        self._write_log(json.dumps(result, ensure_ascii=False, indent=2))
        self._refresh_results()
        self.notebook.select(0)

    def _handle_error(self, error: Exception) -> None:
        self.worker = None
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.status_var.set("运行失败 · 请查看日志")
        self._write_log(f"运行失败：{error}")
        messagebox.showerror("采集失败", str(error))

    def _write_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert(END, text.rstrip() + "\n")
        self.log.see(END)
        self.log.configure(state="disabled")

    def _refresh_results(self) -> None:
        self.result_files = discover_result_files(self.vars["output_dir"].get())
        try:
            self.rows = load_result_rows(self.result_files["snapshot"], self.result_files["new_products"])
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            self.rows = []
            self._write_log(f"读取结果失败：{exc}")
        summary = _summarize(self.rows)
        for key, value in summary.items():
            self.metric_vars[key].set(str(value))
        categories = sorted({str(row.get("category_name") or "未分类") for row in self.rows})
        self.category_combo.configure(values=[""] + categories)
        if self.vars["category"].get() not in categories:
            self.vars["category"].set("")
        self.last_updated_var.set(f"最新快照：{self.result_files['snapshot'].stem.removeprefix('snapshot_')}" if self.result_files.get("snapshot") else "暂无本地结果")
        self._apply_filters()
        self._refresh_candidates()
        self._refresh_history()

    def _apply_filters(self) -> None:
        if not hasattr(self, "tree"):
            return
        try:
            min_score = int(self.vars["score_min"].get() or 0)
        except ValueError:
            min_score = 0
        self.filtered_rows = sort_product_rows(
            filter_product_rows(self.rows, query=self.vars["search"].get(), category=self.vars["category"].get(), new_only=self.vars["new_only"].get(), min_score=min_score),
            key=self._sort_key(),
            descending=self.vars["sort_desc"].get(),
        )
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in self.filtered_rows:
            price = f"{row.get('currency') or 'AUD'} {row.get('price')}" if row.get("price") else "未取得"
            asin = str(row.get("asin") or "")
            self.tree.insert("", END, iid=asin, values=(
                row.get("rank") or "-", row.get("title"), asin, row.get("category_name"), price,
                row.get("rating") or "-", row.get("review_count") or "-", row.get("score"), row.get("heat_label"), "是" if row.get("is_new") else "否",
            ), tags=("new",) if row.get("is_new") else ())
        self.result_count_var.set(f"{len(self.filtered_rows)} / {len(self.rows)} 个商品")
        self.empty_products_var.set("没有符合当前筛选条件的商品" if self.rows else "还没有结果，请先运行采集")
        if self.filtered_rows:
            self.tree.selection_set(str(self.filtered_rows[0].get("asin")))
            self._show_selected_detail()
        else:
            self._clear_detail()

    def _refresh_candidates(self) -> None:
        for item in self.candidate_tree.get_children():
            self.candidate_tree.delete(item)
        candidates = sort_product_rows(self.rows, key="score", descending=True)[:8]
        for row in candidates:
            asin = str(row.get("asin") or "")
            self.candidate_tree.insert("", END, iid=asin, values=(row.get("rank") or "-", row.get("title"), row.get("score"), row.get("heat_label"), "是" if row.get("is_new") else "否"))

    def _show_selected_detail(self, _event: Any = None) -> None:
        selected = self.tree.selection()
        if not selected:
            self._clear_detail()
            return
        row = next((item for item in self.rows if str(item.get("asin")) == selected[0]), None)
        if not row:
            self._clear_detail()
            return
        self.detail_title_var.set(str(row.get("title") or row.get("asin")))
        self.detail_meta_var.set(f"ASIN {row.get('asin')} · {row.get('category_name')} · 机会评分 {row.get('score')}/100")
        details = [
            f"热度：{row.get('heat_label')}",
            f"新品榜：{row.get('rank_signal')}",
            f"评分：{row.get('rating_signal')}",
            f"评论：{row.get('review_signal')}",
            f"竞争判断：{row.get('competition')}",
            "",
            f"改进方向：{row.get('improvement')}",
            "",
            f"证据：{'本次首次发现' if row.get('is_new') else '历史中已有记录'}",
            "销量结论：未确认销量",
        ]
        self.detail_body.configure(state="normal")
        self.detail_body.delete("1.0", END)
        self.detail_body.insert("1.0", "\n".join(details))
        self.detail_body.configure(state="disabled")
        self.detail_link_var.set(str(row.get("product_url") or ""))

    def _clear_detail(self) -> None:
        self.detail_title_var.set("选择一个商品查看详细分析")
        self.detail_meta_var.set("")
        self.detail_body.configure(state="normal")
        self.detail_body.delete("1.0", END)
        self.detail_body.insert("1.0", "筛选结果后，点击左侧商品即可查看机会评分、竞争判断和改进方向。")
        self.detail_body.configure(state="disabled")
        self.detail_link_var.set("")

    def _open_candidate(self, _event: Any = None) -> None:
        selected = self.candidate_tree.selection()
        if not selected:
            return
        self.notebook.select(1)
        self.vars["search"].set(selected[0])

    def _selected_row(self) -> dict[str, Any] | None:
        selected = self.tree.selection() if hasattr(self, "tree") else ()
        return next((item for item in self.rows if selected and str(item.get("asin")) == selected[0]), None)

    def _open_selected_product(self, _event: Any = None) -> None:
        row = self._selected_row()
        if row:
            webbrowser.open(str(row.get("product_url")))

    def copy_selected_asin(self) -> None:
        row = self._selected_row()
        if not row:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(str(row.get("asin")))
        self.status_var.set(f"已复制 ASIN · {row.get('asin')}")

    def export_current(self) -> None:
        if not self.filtered_rows:
            messagebox.showinfo("暂无结果", "当前筛选没有可导出的商品。")
            return
        path = filedialog.asksaveasfilename(title="导出当前筛选", defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile="seller_filtered_products.csv")
        if not path:
            return
        try:
            export_product_rows_csv(self.filtered_rows, path)
        except OSError as exc:
            messagebox.showerror("导出失败", str(exc))
            return
        self.status_var.set(f"已导出 {len(self.filtered_rows)} 个商品")
        self._write_log(f"已导出筛选 CSV：{path}")

    def _refresh_history(self) -> None:
        if not hasattr(self, "history_tree"):
            return
        self.history_entries = discover_run_history(self.vars["output_dir"].get())
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for entry in self.history_entries:
            self.history_tree.insert("", END, iid=entry["date"], values=(entry["date"], entry["products"] if entry["products"] is not None else "读取失败", "有" if entry["has_csv"] else "无", "有" if entry["has_html"] else "无", str(entry["snapshot"])))

    def open_selected_history(self) -> None:
        selected = self.history_tree.selection()
        entry = next((item for item in self.history_entries if selected and item["date"] == selected[0]), None)
        if not entry:
            self.open_report()
            return
        if entry["has_html"]:
            webbrowser.open(entry["html"].resolve().as_uri())
        else:
            messagebox.showinfo("暂无 HTML", "这次运行只有快照或 CSV，没有 HTML 报告。")

    def save_config(self) -> None:
        target = self.vars["config_path"].get().strip()
        if not target:
            target = filedialog.asksaveasfilename(title="保存配置", defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not target:
            return
        try:
            config = build_gui_config(self._form_values())
            Path(target).parent.mkdir(parents=True, exist_ok=True)
            Path(target).write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
            self.vars["config_path"].set(target)
            self.status_var.set(f"配置已保存 · {Path(target).name}")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("保存失败", str(exc))

    def _load_config_from_field(self) -> None:
        path = self.vars["config_path"].get().strip()
        if not path:
            self._choose_config()
            return
        try:
            config = load_config(path)
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showerror("配置读取失败", str(exc))
            return
        for key in ("timezone", "delay_seconds", "timeout_seconds", "max_retries", "max_pages", "max_category_depth"):
            if key in config:
                self.vars[key].set(str(config[key]))
        self.status_var.set(f"配置已加载 · {Path(path).name}")

    def open_report(self) -> None:
        report = self.result_files.get("html") or discover_result_files(self.vars["output_dir"].get())["html"]
        if report:
            webbrowser.open(report.resolve().as_uri())
        else:
            messagebox.showinfo("暂无报告", "当前输出目录还没有 HTML 报告。请先运行采集。")

    def open_output(self) -> None:
        output = Path(self.vars["output_dir"].get()).resolve()
        output.mkdir(parents=True, exist_ok=True)
        if hasattr(os, "startfile"):
            os.startfile(output)  # type: ignore[attr-defined]
        else:
            webbrowser.open(output.as_uri())

    def _choose_config(self) -> None:
        path = filedialog.askopenfilename(title="选择配置 JSON", filetypes=[("JSON", "*.json")])
        if path:
            self.vars["config_path"].set(path)
            self._load_config_from_field()

    def _choose_db(self) -> None:
        path = filedialog.asksaveasfilename(title="选择 SQLite 数据库", defaultextension=".sqlite3", filetypes=[("SQLite", "*.sqlite3"), ("所有文件", "*.*")])
        if path:
            self.vars["db_path"].set(path)

    def _choose_output(self) -> None:
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.vars["output_dir"].set(path)
            self._refresh_results()

    def _choose_fixture(self) -> None:
        path = filedialog.askdirectory(title="选择离线 fixture 目录")
        if path:
            self.vars["fixture_dir"].set(path)

    def _on_close(self) -> None:
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno("正在采集", "当前仍有采集任务，确定要关闭窗口吗？"):
                return
        self.root.destroy()


def main() -> int:
    app = AmazonReleaseApp()
    app.root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
