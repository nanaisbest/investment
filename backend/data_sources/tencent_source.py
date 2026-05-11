"""
腾讯财经数据源
核心优势：公开API无需认证，指标数据秒回
提供技术指标和财务指标
"""

import httpx
from typing import Optional


class TencentSource:
    BASE_URL = "https://qt.gtimg.cn"

    async def get_realtime_quote(self, symbols: list[str]) -> dict:
        """获取实时行情（秒级响应）"""
        codes = ",".join(symbols)
        url = f"{self.BASE_URL}/q={codes}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                text = resp.content.decode("gbk", errors="replace")
                return {
                    "status": "success",
                    "source": "tencent",
                    "data": self._parse_batch_quote(text),
                    "symbols": symbols,
                }
        except Exception as e:
            return {"status": "error", "source": "tencent", "message": str(e)}

    async def get_batch_indicators(self, codes: list[str]) -> dict:
        """批量获取技术指标：KDJ、MACD、RSI、WR、CCI、BOLL等"""
        results = {}
        async with httpx.AsyncClient(timeout=15) as client:
            for code in codes:
                try:
                    prefix = "sh" if code.startswith("6") else "sz"
                    url = f"https://web.ifzq.gtimg.cn/appstock/app/minute/query?_var=min_data&code={prefix}{code}"
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        results[code] = resp.json()
                except Exception:
                    results[code] = None
        return {"status": "success", "source": "tencent", "data": results}

    # 周期映射：前端值 -> 腾讯API周期key
    PERIOD_MAP = {
        0: "m5",      # 5分钟
        1: "m15",     # 15分钟
        2: "m30",     # 30分钟
        3: "m60",     # 60分钟
        4: "day",     # 日线
        5: "week",    # 周线
        6: "month",   # 月线
        8: "m1",      # 1分钟
    }

    async def get_kline(self, code: str, period: int = 4, count: int = 100) -> dict:
        """获取K线数据"""
        prefix = "sh" if code.startswith("6") else "sz"
        period_key = self.PERIOD_MAP.get(period, "day")
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={prefix}{code},{period_key},,,{count},qfq"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                result = resp.json()
                if result.get("code") != 0:
                    return {"status": "error", "source": "tencent", "message": "腾讯接口返回异常"}
                stock_data = result.get("data", {}).get(f"{prefix}{code}")
                if not stock_data:
                    return {"status": "success", "source": "tencent", "symbol": code, "data": []}
                # 根据周期获取对应的数据key
                if period_key in ("day", "week", "month"):
                    data_key = f"qfq{period_key}"
                else:
                    data_key = period_key
                raw_data = stock_data.get(data_key, [])
                if not raw_data:
                    return {"status": "success", "source": "tencent", "symbol": code, "data": []}
                parsed = []
                for row in raw_data:
                    if len(row) >= 6:
                        parsed.append({
                            "date": str(row[0]),
                            "open": float(row[1]),
                            "close": float(row[2]),
                            "high": float(row[3]),
                            "low": float(row[4]),
                            "volume": float(row[5]),
                        })
                return {"status": "success", "source": "tencent", "symbol": code, "data": parsed}
        except Exception as e:
            return {"status": "error", "source": "tencent", "message": str(e)}

    async def get_financial_indicator(self, code: str) -> dict:
        """获取财务指标"""
        prefix = "sh" if code.startswith("6") else "sz"
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={prefix}{code},day,,,60,qfq"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                return {"status": "success", "source": "tencent", "symbol": code, "data": resp.json()}
        except Exception as e:
            return {"status": "error", "source": "tencent", "message": str(e)}

    def _parse_batch_quote(self, raw: str) -> list[dict]:
        """解析腾讯批量行情数据 - 88字段标准格式"""
        results = []
        lines = raw.strip().split("\n")
        for line in lines:
            if '="' not in line:
                continue
            try:
                raw_data = line.split('="')[1].rstrip('";\n\r')
                fields = raw_data.split("~")
                if len(fields) < 40:
                    continue
                change_pct = float(fields[32]) if fields[32] else 0
                current = float(fields[3]) if fields[3] else 0
                results.append({
                    "name": fields[1],
                    "code": fields[2],
                    "current": current,
                    "prev_close": float(fields[4]) if fields[4] else 0,
                    "open": float(fields[5]) if fields[5] else 0,
                    "volume": int(float(fields[6])) if fields[6] else 0,
                    "high": float(fields[33]) if fields[33] else 0,
                    "low": float(fields[34]) if fields[34] else 0,
                    "change_pct": change_pct,
                    "change_amount": float(fields[31]) if fields[31] else 0,
                    "turnover": float(fields[38]) if fields[38] else 0,
                    "pe": float(fields[39]) if fields[39] else 0,
                })
            except (ValueError, IndexError):
                continue
        return results


tencent_source = TencentSource()
