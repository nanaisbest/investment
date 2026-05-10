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
