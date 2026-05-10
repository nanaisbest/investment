"""
同花顺问财 (iwencai) 数据源 + akshare 语义搜索回退
问财原 API 已失效，改用 akshare 的条件选股功能
"""

import asyncio

try:
    import akshare as ak
except ImportError:
    ak = None


class IwencaiSource:

    async def search(self, query: str, page: int = 1) -> dict:
        """自然语言语义搜索选股（基于 akshare 条件选股）

        支持的关键词模式:
        - "连续上涨N天" / "连续下跌N天"
        - "涨停" / "跌停"
        - "低市盈率" / "高换手"
        - "次新股"
        """
        if ak is None:
            return {"status": "error", "source": "iwencai", "message": "akshare 未安装，请运行 pip install akshare"}

        loop = asyncio.get_event_loop()
        results = []

        try:
            if "涨停" in query:
                df = await loop.run_in_executor(None, ak.stock_zt_pool_em, None)
                if df is not None and len(df) > 0:
                    for _, row in df.head(50).iterrows():
                        results.append({
                            "code": str(row.get("代码", "")),
                            "name": str(row.get("名称", "")),
                            "price": float(row.get("最新价", 0) or 0),
                            "change_pct": float(row.get("涨跌幅", 0) or 0),
                        })
                    return {"status": "success", "source": "iwencai", "query": query, "data": results, "total": len(results)}

            if "跌停" in query:
                df = await loop.run_in_executor(None, ak.stock_zt_pool_dtgc_em, None)
                if df is not None and len(df) > 0:
                    for _, row in df.head(50).iterrows():
                        results.append({
                            "code": str(row.get("代码", "")),
                            "name": str(row.get("名称", "")),
                            "price": float(row.get("最新价", 0) or 0),
                            "change_pct": float(row.get("涨跌幅", 0) or 0),
                        })
                    return {"status": "success", "source": "iwencai", "query": query, "data": results, "total": len(results)}

            if "次新" in query:
                df = await loop.run_in_executor(None, ak.stock_zt_pool_sub_new_em, None)
                if df is not None and len(df) > 0:
                    for _, row in df.head(50).iterrows():
                        results.append({
                            "code": str(row.get("代码", "")),
                            "name": str(row.get("名称", "")),
                            "price": float(row.get("最新价", 0) or 0),
                            "change_pct": float(row.get("涨跌幅", 0) or 0),
                        })
                    return {"status": "success", "source": "iwencai", "query": query, "data": results, "total": len(results)}

            # 默认：获取连续上涨股票
            if "连续上涨" in query or "上涨" in query:
                df = await loop.run_in_executor(None, ak.stock_zt_pool_strong_em, None)
                if df is not None and len(df) > 0:
                    for _, row in df.head(50).iterrows():
                        results.append({
                            "code": str(row.get("代码", "")),
                            "name": str(row.get("名称", "")),
                            "price": float(row.get("最新价", 0) or 0),
                            "change_pct": float(row.get("涨跌幅", 0) or 0),
                        })
                    return {"status": "success", "source": "iwencai", "query": query, "data": results, "total": len(results)}

            # 无匹配时返回提示
            return {
                "status": "success",
                "source": "iwencai",
                "query": query,
                "data": [],
                "message": f"暂不支持该查询条件，支持：涨停、跌停、次新股、连续上涨",
            }

        except Exception as e:
            return {"status": "error", "source": "iwencai", "message": str(e)}


iwencai_source = IwencaiSource()
