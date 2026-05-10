"""
akshare 数据源
核心优势：覆盖研报、新闻、公告等非结构化数据
"""

import asyncio
from typing import Optional

try:
    import akshare as ak
except ImportError:
    ak = None


class AkshareSource:
    async def get_stock_news(self, symbol: str = "") -> dict:
        """获取个股新闻或市场要闻"""
        if ak is None:
            return {"error": "akshare 未安装，请运行 pip install akshare"}
        loop = asyncio.get_event_loop()
        try:
            df = await loop.run_in_executor(None, lambda: ak.stock_news_em(symbol=symbol) if symbol else ak.stock_news_em())
            return {"status": "success", "source": "akshare", "data": df.head(50).to_dict("records")}
        except Exception as e:
            return {"status": "error", "source": "akshare", "message": str(e)}

    async def get_research_report(self, symbol: str) -> dict:
        """获取个股研报"""
        if ak is None:
            return {"error": "akshare 未安装，请运行 pip install akshare"}
        loop = asyncio.get_event_loop()
        try:
            df = await loop.run_in_executor(None, lambda: ak.stock_research_report_em(symbol=symbol))
            return {"status": "success", "source": "akshare", "symbol": symbol, "data": df.head(30).to_dict("records")}
        except Exception as e:
            return {"status": "error", "source": "akshare", "message": str(e)}

    async def get_stock_announcement(self, symbol: str) -> dict:
        """获取个股公告"""
        if ak is None:
            return {"error": "akshare 未安装，请运行 pip install akshare"}
        loop = asyncio.get_event_loop()
        try:
            df = await loop.run_in_executor(None, lambda: ak.stock_notice_report(symbol=symbol))
            return {"status": "success", "source": "akshare", "symbol": symbol, "data": df.head(30).to_dict("records")}
        except Exception as e:
            return {"status": "error", "source": "akshare", "message": str(e)}

    async def get_market_sentiment(self, date: str = "") -> dict:
        """获取市场情绪指标 - 涨跌停统计。date不传时自动取最近交易日"""
        if ak is None:
            return {"error": "akshare 未安装，请运行 pip install akshare"}
        loop = asyncio.get_event_loop()
        try:
            target_date = date if date else None
            df = await loop.run_in_executor(None, ak.stock_zt_pool_em, target_date)
            if df is not None and len(df) > 0:
                return {"status": "success", "source": "akshare", "data": df.head(100).to_dict("records")}
            return {"status": "success", "source": "akshare", "data": [], "message": "当日无涨停数据（非交易日或盘前）"}
        except Exception as e:
            return {"status": "error", "source": "akshare", "message": str(e)}


akshare_source = AkshareSource()
