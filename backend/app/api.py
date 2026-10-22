from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from .config import DEFAULT_MARKETPLACES, get_marketplace
from .domain import ProductSnapshot
from .adapters.csv_import import parse_product_csv
from .services import calculate_profit, score_product


app = FastAPI(title="AmazonRelease MVP API", version="0.1.0")
_RESEARCH_TASKS: dict[UUID, dict[str, object]] = {}


class ProfitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    price: Decimal = Field(gt=0)
    purchase_cost: Decimal = Field(ge=0)
    inbound_shipping: Decimal = Field(default=Decimal("0"), ge=0)
    platform_fee: Decimal = Field(default=Decimal("0"), ge=0)
    fba_fee: Decimal = Field(default=Decimal("0"), ge=0)
    packaging_cost: Decimal = Field(default=Decimal("0"), ge=0)
    ad_cost: Decimal = Field(default=Decimal("0"), ge=0)
    return_reserve: Decimal = Field(default=Decimal("0"), ge=0)
    tax_cost: Decimal = Field(default=Decimal("0"), ge=0)


class ScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot: ProductSnapshot
    components: dict[str, Optional[Decimal]]


class ResearchTaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    marketplace: str
    category_id: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    asin_list: list[str] = Field(default_factory=list)
    filters: dict[str, object] = Field(default_factory=dict)


def _decimal(value: Decimal) -> str:
    return format(value, "f")


@app.get("/api/marketplaces")
def list_marketplaces() -> list[dict[str, object]]:
    return [
        {
            "code": config.code,
            "amazon_marketplace_id": config.amazon_marketplace_id,
            "frontend_domain": config.frontend_domain,
            "seller_central_domain": config.seller_central_domain,
            "sp_api_endpoint": config.sp_api_endpoint,
            "sp_api_region": config.sp_api_region,
            "currency": config.currency,
            "locale": config.locale,
            "timezone": config.timezone,
            "enabled": config.enabled,
        }
        for config in DEFAULT_MARKETPLACES.values()
        if config.enabled
    ]


@app.get("/api/products")
def list_products(
    marketplace: Optional[str] = Query(default=None),
    asin: Optional[str] = Query(default=None),
) -> dict[str, object]:
    # M3 skeleton: persistence is intentionally not wired until the data-source
    # contract and PostgreSQL migration are frozen in M2.
    return {
        "items": [],
        "total": 0,
        "filters": {"marketplace": marketplace, "asin": asin},
        "notice": "暂无已验证商品数据；请先完成数据源验证或导入 CSV。",
    }


@app.get("/api/products/{marketplace}/{asin}")
def get_product(marketplace: str, asin: str) -> dict[str, object]:
    raise HTTPException(status_code=404, detail="商品尚未进入已验证数据集")


@app.post("/api/research/tasks", status_code=202)
def create_research_task(request: ResearchTaskRequest) -> dict[str, object]:
    marketplace = get_marketplace(request.marketplace)
    task_id = uuid4()
    task = {
        "task_id": str(task_id),
        "marketplace": marketplace.code,
        "category_id": request.category_id,
        "keywords": request.keywords,
        "asin_list": request.asin_list,
        "filters": request.filters,
        "status": "queued",
        "notice": "M3 仅登记任务；后台数据源同步将在 M2 授权与字段验证后启用。",
    }
    _RESEARCH_TASKS[task_id] = task
    return task


@app.get("/api/research/tasks/{task_id}")
def get_research_task(task_id: UUID) -> dict[str, object]:
    task = _RESEARCH_TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@app.post("/api/products/import")
async def import_products(marketplace: str, file: UploadFile = File(...)) -> dict[str, object]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="当前 MVP 先支持 CSV；XLSX 入口将在字段冻结后接入")
    result = parse_product_csv(await file.read(), marketplace_code=marketplace)
    return {
        "imported": len(result.items),
        "rejected": len(result.errors),
        "items": result.items,
        "errors": result.errors,
        "notice": "导入结果仅进入验证预览；未完成数据源验证前不会被标记为生产销量。",
    }


@app.post("/api/profit/calculate")
def calculate_profit_endpoint(request: ProfitRequest) -> dict[str, object]:
    result = calculate_profit(**request.model_dump())
    return {
        "revenue": _decimal(result.revenue),
        "total_cost": _decimal(result.total_cost),
        "profit": _decimal(result.profit),
        "profit_margin": _decimal(result.profit_margin),
        "roi": _decimal(result.roi),
        "is_scenario": result.is_scenario,
        "notice": "情景利润：基于用户输入成本参数，不代表竞品真实净利润。",
    }


@app.post("/api/scoring/evaluate")
def evaluate_score(request: ScoreRequest) -> dict[str, object]:
    result = score_product(request.snapshot, **request.components)
    return {
        "score": _decimal(result.score),
        "confidence": _decimal(result.confidence),
        "known_components": list(result.known_components),
        "missing_components": list(result.missing_components),
        "notice": "缺失字段已按已知权重重归一化，置信度同步下降。",
    }


@app.get("/api/system/source-status")
def source_status() -> list[dict[str, object]]:
    return [
        {"source": "keepa", "configured": False, "status": "按项目决策跳过"},
        {"source": "sp_api", "configured": False, "status": "待卖家授权与角色确认"},
        {"source": "csv", "configured": True, "status": "可作为兜底入口"},
    ]
