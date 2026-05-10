"""
mootdx 数据源 - 通达信底层协议
核心优势：不封IP，实时盘口数据，完整K线数据
"""

import asyncio
from typing import Optional
import random

try:
    from mootdx.quotes import Quotes
except ImportError:
    Quotes = None

BACKUP_SERVERS = [
    ("218.85.139.19", 7709),
    ("218.85.139.20", 7709),
    ("180.153.18.170", 7709),
    ("180.153.18.171", 7709),
    ("60.191.117.167", 7709),
    ("115.238.56.198", 7709),
    ("218.75.126.9", 7709),
    ("114.80.63.12", 7709),
    ("119.147.212.81", 7709),
    ("124.70.176.52", 7709),
    ("47.100.236.28", 7709),
    ("110.41.147.114", 7709),
]


class MootdxSource:
    def __init__(self):
        self._client = None
        self._last_server = None

    def _connect(self, host, port):
        if Quotes is None:
            return None
        try:
            return Quotes.factory(market="std", server=(host, port), timeout=8)
        except Exception:
            return None

    def _get_client(self):
        if self._client is not None:
            return self._client

        if Quotes is None:
            return None

        servers = random.sample(BACKUP_SERVERS, len(BACKUP_SERVERS))
        for host, port in servers:
            client = self._connect(host, port)
            if client is not None:
                self._client = client
                self._last_server = (host, port)
                return client
        return None

    async def _call(self, func, *args, **kwargs):
        if Quotes is None:
            return {"status": "error", "source": "mootdx", "message": "mootdx 未安装"}
        loop = asyncio.get_event_loop()
        client = self._get_client()
        if not client:
            return {"status": "error", "source": "mootdx", "message": "所有通达信服务器连接失败，请稍后重试"}

        try:
            result = await loop.run_in_executor(None, func, client, *args)
            return result
        except Exception:
            # 连接失效，重置并在下一个可用服务器上重试一次
            self._client = None
            client = self._get_client()
            if not client:
                return {"status": "error", "source": "mootdx", "message": "服务器连接中断，重试失败"}
            try:
                result = await loop.run_in_executor(None, func, client, *args)
                return result
            except Exception as e:
                self._client = None
                return {"status": "error", "source": "mootdx", "message": str(e)}

    async def get_realtime_quote(self, symbols: list[str]) -> dict:
        """获取实时盘口数据"""
        def _do(client):
            data = client.quotes(symbols)
            return {"status": "success", "source": "mootdx", "data": data.to_dict("records") if hasattr(data, "to_dict") else data}
        return await self._call(_do)

    async def get_kline(self, symbol: str, period: int = 0, count: int = 100) -> dict:
        """获取K线数据
        period: 0=日线, 1=周线, 2=月线, 5=5分钟, 6=15分钟, 7=30分钟, 8=60分钟, 9=1分钟
        """
        def _do(client):
            data = client.bars(symbol=symbol.strip(), frequency=period, offset=count)
            if data is None or len(data) == 0:
                return {"status": "success", "source": "mootdx", "symbol": symbol, "data": []}
            records = data.to_dict("records")
            index_values = [str(i) for i in data.index]
            result = []
            for i, r in enumerate(records):
                item = {"date": index_values[i] if i < len(index_values) else ""}
                for k, v in r.items():
                    if k == 'vol':
                        item['volume'] = v
                    else:
                        item[k] = v
                result.append(item)
            return {"status": "success", "source": "mootdx", "symbol": symbol, "data": result}
        return await self._call(_do)

    async def get_stock_list(self, market: int = 0) -> dict:
        """获取股票列表"""
        def _do(client):
            data = client.market(market)
            return {"status": "success", "source": "mootdx", "data": data.to_dict("records") if hasattr(data, "to_dict") else data}
        return await self._call(_do)


mootdx_source = MootdxSource()
