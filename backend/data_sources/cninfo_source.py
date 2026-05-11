"""
巨潮资讯网数据源 - 官方信息披露平台
核心优势：官方公告/年报/季报原文，无需认证
"""

import math
import re
import time
import json
import os
import base64
import httpx


def _load_stock_map() -> dict[str, str]:
    """加载代码→名称映射"""
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stock_list.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {item["code"]: item["name"] for item in data if item.get("code") and item.get("name")}
    except Exception:
        return {}


class CninfoSource:
    BASE_URL = "http://www.cninfo.com.cn"
    STATIC_BASE = "http://static.cninfo.com.cn"
    WEBAPI_BASE = "http://webapi.cninfo.com.cn"

    CATEGORY_MAP = {
        "年度报告": "category_ndbg_szsh",
        "半年度报告": "category_bndbg_szsh",
        "一季度报告": "category_yjdbg_szsh",
        "三季度报告": "category_sjdbg_szsh",
    }

    def __init__(self):
        self._stock_map = _load_stock_map()

    @staticmethod
    def _strip_tags(text: str) -> str:
        return re.sub(r"<[^>]+>", "", text)

    @staticmethod
    def _make_mcode() -> str:
        ts = str(math.floor(time.time()))
        return base64.b64encode(ts.encode()).decode()

    async def search_announcements(
        self,
        stock_code: str = "",
        keyword: str = "",
        start_date: str = "",
        end_date: str = "",
        category: str = "",
        page_num: int = 1,
        page_size: int = 30,
    ) -> dict:
        """搜索公告/年报/季报"""
        url = f"{self.BASE_URL}/new/hisAnnouncement/query"
        # 用股票名称做搜索关键词（stock 参数无效），然后本地精确过滤
        search_name = self._stock_map.get(stock_code, "") if stock_code else ""
        search_terms = []
        if search_name:
            search_terms.append(search_name)
        elif stock_code:
            search_terms.append(stock_code)
        if keyword:
            search_terms.append(keyword)

        form_data = {
            "pageNum": 1,
            "pageSize": 100,
            "column": "szse",
            "tabName": "fulltext",
            "plate": "sz;sh",
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        }
        if search_terms:
            form_data["searchkey"] = " ".join(search_terms)
        if start_date and end_date:
            form_data["seDate"] = f"{start_date}~{end_date}"
        if category:
            form_data["category"] = category

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "http://www.cninfo.com.cn/",
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(url, data=form_data, headers=headers)
                resp.raise_for_status()
                result = resp.json()
        except Exception as e:
            return {"status": "error", "source": "cninfo", "message": str(e)}

        raw_list = result.get("announcements") or []

        parsed = []
        for item in raw_list:
            adjunct = item.get("adjunctUrl", "")
            parsed.append({
                "code": item.get("secCode", ""),
                "name": self._strip_tags((item.get("secName", "") or "").strip()),
                "title": self._strip_tags(item.get("announcementTitle", "")),
                "time": item.get("announcementTime", 0),
                "pdf_url": f"{self.STATIC_BASE}/{adjunct}" if adjunct else "",
                "pdf_type": item.get("adjunctType", ""),
            })

        # 精确过滤：只保留匹配 stock_code 的结果
        if stock_code:
            parsed = [item for item in parsed if item["code"] == stock_code]

        total = len(parsed)
        # 本地分页
        start = (page_num - 1) * page_size
        paged = parsed[start:start + page_size]

        return {
            "status": "success",
            "source": "cninfo",
            "data": paged,
            "total": total,
            "page": page_num,
            "page_size": page_size,
            "stock_code": stock_code,
            "keyword": keyword,
            "category": category,
        }

    async def get_stock_list(self) -> dict:
        """获取深市股票列表"""
        url = f"{self.BASE_URL}/new/data/szse_stock.json"
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
            stock_list = data.get("stockList") or data if isinstance(data, list) else []
            return {"status": "success", "source": "cninfo", "data": stock_list}
        except Exception as e:
            return {"status": "error", "source": "cninfo", "message": str(e)}

    async def get_daily_quotes(self, code: str = "") -> dict:
        """获取每日行情 (webapi.cninfo.com.cn)"""
        if not code:
            return {"status": "error", "source": "cninfo", "message": "股票代码不能为空"}

        mcode = self._make_mcode()
        url = f"{self.WEBAPI_BASE}/api/sysapi/p_sysapi1015"
        headers = {
            "mcode": mcode,
            "Referer": "http://webapi.cninfo.com.cn/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        form_data = {
            "tdate": time.strftime("%Y-%m-%d"),
            "scode": code,
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(url, data=form_data, headers=headers)
                resp.raise_for_status()
                result = resp.json()
            records = result.get("records") or []
            return {"status": "success", "source": "cninfo", "data": records, "symbol": code}
        except Exception as e:
            return {"status": "error", "source": "cninfo", "message": str(e)}


cninfo_source = CninfoSource()
