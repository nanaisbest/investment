"""
同花顺热点数据源
核心优势：提供当日强势股和题材归因分析
"""

import httpx
import asyncio

try:
    import akshare as ak
except ImportError:
    ak = None


class TonghuashunSource:
    CONCEPT_URL = "http://zx.10jqka.com.cn/hotblock/proxy/block/platerankinfo"

    async def get_hot_concepts(self) -> dict:
        """获取当日热门概念板块"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://data.10jqka.com.cn/",
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(self.CONCEPT_URL, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    concepts = []
                    for item in data.get("result", [])[:50]:
                        concepts.append({
                            "name": item.get("platename", ""),
                            "code": str(item.get("platecode", "")),
                            "change_pct": item.get("increase", 0),
                        })
                    return {"status": "success", "source": "tonghuashun", "data": concepts}
                return {"status": "error", "source": "tonghuashun", "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"status": "error", "source": "tonghuashun", "message": str(e)}

    async def get_strong_stocks(self) -> dict:
        """获取当日强势股/涨停股（通过akshare）"""
        if ak is None:
            return {"status": "error", "source": "tonghuashun", "message": "akshare 未安装"}
        loop = asyncio.get_event_loop()
        try:
            df = await loop.run_in_executor(None, ak.stock_zt_pool_em, None)
            if df is None or len(df) == 0:
                return {"status": "success", "source": "tonghuashun", "data": [], "message": "当日无涨停数据"}
            result = []
            for _, row in df.head(50).iterrows():
                result.append({
                    "code": str(row.get("代码", "")),
                    "name": str(row.get("名称", "")),
                    "price": float(row.get("最新价", 0) or 0),
                    "change_pct": float(row.get("涨跌幅", 0) or 0),
                    "turnover": float(row.get("换手率", 0) or 0),
                    "volume": float(row.get("成交额", 0) or 0),
                })
            return {"status": "success", "source": "tonghuashun", "data": result}
        except Exception as e:
            return {"status": "error", "source": "tonghuashun", "message": str(e)}

    async def get_sector_attribution(self, stock_code: str) -> dict:
        """获取个股题材归因"""
        if ak is None:
            return {"status": "error", "source": "tonghuashun", "message": "akshare 未安装"}
        loop = asyncio.get_event_loop()
        try:
            df = await loop.run_in_executor(None, ak.stock_board_concept_cons_em, stock_code.strip())
            if df is not None and len(df) > 0:
                return {"status": "success", "source": "tonghuashun", "symbol": stock_code, "data": df.head(20).to_dict("records")}
            return {"status": "success", "source": "tonghuashun", "symbol": stock_code, "data": [], "message": "未找到题材信息"}
        except Exception as e:
            return {"status": "error", "source": "tonghuashun", "message": str(e)}


tonghuashun_source = TonghuashunSource()
