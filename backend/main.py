"""
投资数据平台 - 后端 API 服务
整合 5 大数据源：mootdx、腾讯财经、akshare、同花顺问财、同花顺热点
"""

import json
import os
import time
import asyncio
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from data_sources import (
    MootdxSource,
    TencentSource,
    AkshareSource,
    IwencaiSource,
    TonghuashunSource,
)

app = FastAPI(title="投资数据平台 API", version="1.0.0", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化各数据源
mootdx = MootdxSource()
tencent = TencentSource()
akshare = AkshareSource()
iwencai = IwencaiSource()
tonghuashun = TonghuashunSource()

# 加载全量股票列表
_stock_list = []
_stock_list_path = os.path.join(os.path.dirname(__file__), "stock_list.json")
try:
    with open(_stock_list_path, encoding="utf-8") as f:
        _stock_list = json.load(f)
except FileNotFoundError:
    pass


# ==================== 综合数据接口 ====================

@app.get("/api/overview")
async def overview():
    """获取市场总览数据"""
    symbols = ["sh000001", "sz399001", "sz399006", "sh000688"]
    result = await tencent.get_realtime_quote(symbols)
    return result


@app.get("/api/realtime")
async def realtime_quote(codes: str = Query(default="000001,600519", description="股票代码逗号分隔")):
    """获取实时行情 - 腾讯财经（最快）"""
    symbols = [f"sh{code}" if code.startswith("6") else f"sz{code}" for code in codes.split(",")]
    return await tencent.get_realtime_quote(symbols)


# 全量股票行情缓存
_stock_cache = {"data": [], "ts": 0, "lock": asyncio.Lock()}
_CACHE_TTL = 300  # 5分钟缓存


async def _load_all_stocks():
    """批量加载全量A股行情到缓存"""
    all_data = []
    batch_size = 80
    for i in range(0, len(_stock_list), batch_size):
        batch = _stock_list[i : i + batch_size]
        codes = [item["full_code"] for item in batch]
        result = await tencent.get_realtime_quote(codes)
        if result.get("data"):
            all_data.extend(result["data"])
    _stock_cache["data"] = all_data
    _stock_cache["ts"] = time.time()


@app.get("/api/stocks/all")
async def all_stocks(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=10, le=100),
    sort_by: str = Query(default="code", description="code/name/current/change_pct/open/high/low/volume/turnover/pe"),
    order: str = Query(default="asc", description="asc / desc"),
):
    """分页获取全量A股实时行情，支持全局排序"""
    if not _stock_list:
        return {"status": "error", "message": "股票列表未生成，请先运行 akshare 生成 stock_list.json"}

    cache_age = time.time() - _stock_cache["ts"]
    # 缓存过期则同步刷新（首次需等待约30秒）
    if cache_age > _CACHE_TTL or not _stock_cache["data"]:
        async with _stock_cache["lock"]:
            if time.time() - _stock_cache["ts"] > _CACHE_TTL or not _stock_cache["data"]:
                await _load_all_stocks()

    all_data = _stock_cache["data"]
    if not all_data:
        return {"status": "success", "data": [], "total": len(_stock_list), "page": page, "size": size, "total_pages": 0, "cached": False}

    # 全局排序
    reverse = order == "desc"
    key_map = {
        "code": lambda d: str(d.get("code", "")),
        "name": lambda d: str(d.get("name", "")),
        "current": lambda d: float(d.get("current", 0) or 0),
        "change_pct": lambda d: float(d.get("change_pct", 0) or 0),
        "open": lambda d: float(d.get("open", 0) or 0),
        "high": lambda d: float(d.get("high", 0) or 0),
        "low": lambda d: float(d.get("low", 0) or 0),
        "volume": lambda d: int(d.get("volume", 0) or 0),
        "turnover": lambda d: float(d.get("turnover", 0) or 0),
        "pe": lambda d: float(d.get("pe", 0) or 0),
    }
    key_func = key_map.get(sort_by, key_map["code"])
    try:
        sorted_data = sorted(all_data, key=key_func, reverse=reverse)
    except TypeError:
        sorted_data = all_data

    total = len(sorted_data)
    start = (page - 1) * size
    end = start + size
    page_data = sorted_data[start:end]

    return {
        "status": "success",
        "source": "tencent",
        "data": page_data,
        "total": total,
        "page": page,
        "size": size,
        "total_pages": max(1, (total + size - 1) // size),
        "cached": time.time() - _stock_cache["ts"] < _CACHE_TTL,
        "sort_by": sort_by,
        "order": order,
    }


# ==================== mootdx 接口 ====================

@app.get("/api/mootdx/quote")
async def mootdx_quote(codes: str = Query(default="000001", description="股票代码逗号分隔")):
    """mootdx 实时盘口数据"""
    symbols = []
    for code in codes.split(","):
        code = code.strip()
        prefix = "sh" if code.startswith("6") else "sz"
        symbols.append(f"{prefix}{code}")
    return await mootdx.get_realtime_quote(symbols)


@app.get("/api/mootdx/kline")
async def mootdx_kline(
    symbol: str = Query(default="000001", description="股票代码"),
    period: int = Query(default=4, description="周期: 4=日线 5=周线 6=月线 0=5分钟 1=15分钟 2=30分钟 3=60分钟 8=1分钟"),
    count: int = Query(default=100, description="数据条数"),
):
    """mootdx K线数据"""
    return await mootdx.get_kline(symbol=symbol.strip(), period=period, count=count)


@app.get("/api/mootdx/stock-list")
async def mootdx_stock_list(market: int = Query(default=0, description="市场: 0=深圳 1=上海")):
    """mootdx 股票列表"""
    return await mootdx.get_stock_list(market=market)


# ==================== 腾讯财经接口 ====================

@app.get("/api/tencent/quote")
async def tencent_quote(codes: str = Query(default="000001,600519")):
    """腾讯财经实时行情"""
    symbols = [f"sh{code}" if code.startswith("6") else f"sz{code}" for code in codes.split(",")]
    return await tencent.get_realtime_quote(symbols)


@app.get("/api/tencent/indicators")
async def tencent_indicators(codes: str = Query(default="000001")):
    """腾讯财经技术指标"""
    return await tencent.get_batch_indicators(codes.split(","))


@app.get("/api/tencent/financial")
async def tencent_financial(code: str = Query(default="000001")):
    """腾讯财经财务数据"""
    return await tencent.get_financial_indicator(code.strip())


# ==================== akshare 接口 ====================

@app.get("/api/akshare/news")
async def akshare_news(symbol: str = Query(default="")):
    """akshare 新闻/公告"""
    return await akshare.get_stock_news(symbol.strip())


@app.get("/api/akshare/research")
async def akshare_research(symbol: str = Query(default="000001")):
    """akshare 研报"""
    return await akshare.get_research_report(symbol.strip())


@app.get("/api/akshare/announcement")
async def akshare_announcement(symbol: str = Query(default="000001")):
    """akshare 个股公告"""
    return await akshare.get_stock_announcement(symbol.strip())


@app.get("/api/akshare/sentiment")
async def akshare_sentiment(date: str = Query(default="")):
    """akshare 市场情绪 - 涨停板数据（date格式: 20260508）"""
    return await akshare.get_market_sentiment(date)


# ==================== 同花顺问财接口 ====================

@app.get("/api/iwencai/search")
async def iwencai_search(q: str = Query(default="连续上涨3天", description="自然语言选股条件")):
    """同花顺问财 - 自然语言语义搜索"""
    return await iwencai.search(q)


# ==================== 同花顺热点接口 ====================

@app.get("/api/tonghuashun/hot-concepts")
async def tonghuashun_hot_concepts():
    """同花顺热门概念板块"""
    return await tonghuashun.get_hot_concepts()


@app.get("/api/tonghuashun/strong-stocks")
async def tonghuashun_strong_stocks():
    """同花顺强势股/涨停股"""
    return await tonghuashun.get_strong_stocks()


@app.get("/api/tonghuashun/attribution")
async def tonghuashun_attribution(code: str = Query(default="000001")):
    """同花顺个股题材归因"""
    return await tonghuashun.get_sector_attribution(code.strip())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
