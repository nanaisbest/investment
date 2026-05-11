"""
巴菲特先知分析器 — 交互式对话
基于 LangChain + 大模型，按巴菲特价值投资框架进行全维度分析
支持多轮对话与股票上下文切换
"""

import os
import re
import json
import time
import uuid
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI


# ===== SYSTEM PROMPT 加载 =====

def _load_system_prompt() -> str:
    skill_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skill")

    def _read(filename: str) -> str:
        try:
            with open(os.path.join(skill_dir, filename), "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    principles = _read("buffett-principles.md")
    valuation = _read("valuation-methods.md")

    return f"""你是一位资深的巴菲特式价值投资分析师，精通价值投资理念和估值方法。

## 巴菲特投资原则
{principles}

## 估值方法参考
{valuation}

## 对话规则
1. 你是交互式分析助手，根据用户的具体问题灵活回答，不一定每次都要输出完整报告。
2. 如果用户要求"分析某只股票"，请运用巴菲特原则和估值方法进行全维度分析。
3. 报告中应包含：公司概览、护城河分析（四道过滤器）、财务健康度（ROE/负债/FCF）、估值分析（至少2种方法）、风险提示、综合评分。
4. 支持追问和深入探讨，例如"再详细解释DCF假设"或"ROE为什么这么低"。
5. 如果用户提供的数据有限，诚实说明并基于公开信息给出观点。
6. 评分时给出明确理由，使用 1-10 分制。
7. 回复使用 Markdown 格式，结构清晰，便于阅读。
8. 如果用户想切换分析的股票，告诉他们新代码，你会自动收集相关数据。
"""


# ===== 数据收集（同原版） =====

async def _get_financial_summary(code: str) -> str:
    prefix = "sh" if code.startswith("6") else "sz"
    url = f"https://qt.gtimg.cn/q={prefix}{code}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            text = resp.content.decode("gbk", errors="replace")
            if '="' not in text:
                return "财务数据暂不可用"
            raw = text.split('="')[1].rstrip('";\n\r')
            fields = raw.split("~")
            if len(fields) < 50:
                return "财务数据暂不可用"
            return (
                f"名称: {fields[1]}\n现价: {fields[3]}\n昨收: {fields[4]}\n"
                f"今开: {fields[5]}\n最高: {fields[33]}\n最低: {fields[34]}\n"
                f"成交量(手): {fields[6]}\n成交额(万): {fields[37]}\n换手率: {fields[38]}%\n"
                f"市盈率(PE): {fields[39]}\n市净率(PB): {fields[46]}\n涨跌幅: {fields[32]}%\n"
                f"总市值(亿): {fields[45]}\n52周最高: {fields[47]}\n52周最低: {fields[48]}\n"
            )
    except Exception as e:
        return f"财务数据获取失败: {e}"


async def _get_kline_summary(code: str) -> str:
    prefix = "sh" if code.startswith("6") else "sz"
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={prefix}{code},day,,,20,qfq"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            result = resp.json()
            stock_data = result.get("data", {}).get(f"{prefix}{code}")
            if not stock_data:
                return "K线数据暂不可用"
            raw = stock_data.get("qfqday", [])
            if len(raw) < 2:
                return "K线数据不足"
            closes = [float(r[2]) for r in raw if len(r) >= 6]
            if len(closes) < 2:
                return "K线数据不足"
            first_close = closes[0]
            last_close = closes[-1]
            highest = max(closes)
            lowest = min(closes)
            change = (last_close - first_close) / first_close * 100
            trend = "上涨" if last_close > first_close else "下跌"
            volatility = (highest - lowest) / first_close * 100
            return (
                f"近20日趋势: {trend} ({change:+.2f}%)\n"
                f"区间最高: {highest:.2f}\n区间最低: {lowest:.2f}\n"
                f"波动幅度: {volatility:.1f}%\n最新收盘: {last_close:.2f}"
            )
    except Exception as e:
        return f"K线数据获取失败: {e}"


async def _get_sentiment() -> str:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://push2.eastmoney.com/api/qt/clist/get",
                params={
                    "pn": "1", "pz": "5", "po": "1", "np": "1",
                    "fltt": "2", "invt": "2", "fid": "f3",
                    "fs": "m:0+t:6,m:0+t:80", "fields": "f2,f3,f12,f14",
                },
            )
            data = resp.json()
            items = data.get("data", {}).get("diff", [])
            if not items:
                return "市场情绪数据暂不可用"
            ups = [item for item in items if item.get("f3", 0) > 0]
            hot = len(ups) / len(items) if items else 0.5
            label = "偏热" if hot > 0.6 else ("中性" if hot > 0.3 else "偏冷")
            return f"涨停板热点数: {len(items)}\n涨幅为正: {len(ups)}个\n市场情绪: {label}"
    except Exception as e:
        return f"市场情绪获取失败: {e}"


async def _get_announcement_summary(code: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "http://www.cninfo.com.cn/new/hisAnnouncement/query",
                data={
                    "pageNum": 1, "pageSize": 10, "column": "szse",
                    "tabName": "fulltext", "plate": "sz;sh", "searchkey": code,
                    "seDate": "", "isHLtitle": "true",
                },
                headers={"User-Agent": "Mozilla/5.0", "Referer": "http://www.cninfo.com.cn/"},
            )
            result = resp.json()
            anns = result.get("announcements", [])
            if not anns:
                return "近期无重要公告"
            filtered = [a for a in anns if a.get("secCode") == code] or anns[:5]
            lines = []
            from datetime import datetime
            for a in filtered[:8]:
                title = re.sub(r"<[^>]+>", "", a.get("announcementTitle", ""))
                t = a.get("announcementTime", 0)
                date_str = datetime.fromtimestamp(t / 1000).strftime("%Y-%m-%d") if t else ""
                lines.append(f"- {date_str} {title}")
            return "\n".join(lines) if lines else "近期无重要公告"
    except Exception as e:
        return f"公告获取失败: {e}"


async def _collect_all_data(code: str) -> dict:
    financial, kline, sentiment, announcements = await asyncio.gather(
        _get_financial_summary(code),
        _get_kline_summary(code),
        _get_sentiment(),
        _get_announcement_summary(code),
    )
    return {"stock_code": code, "financial": financial, "kline": kline, "sentiment": sentiment, "announcements": announcements}


def _build_stock_context(data: dict) -> str:
    """构建数据上下文消息"""
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        f"[系统已自动获取 {data['stock_code']} 的实时数据，当前时间: {now}]\n"
        f"注意：以上数据是实时获取的最新数据，请基于此数据回答，不要基于你的训练截止日期。\n\n"
        f"【财务数据】\n{data['financial']}\n\n"
        f"【K线趋势】\n{data['kline']}\n\n"
        f"【市场情绪】\n{data['sentiment']}\n\n"
        f"【近期公告】\n{data['announcements']}"
    )


# ===== 会话管理 =====

class ChatSession:
    def __init__(self, session_id: str):
        self.id = session_id
        self.messages: list = []  # [{role, content}]
        self.stock_code: str = ""
        self.stock_data: dict = {}
        self.created_at = time.time()
        self.last_active = time.time()

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        self.last_active = time.time()

    def is_expired(self, timeout_minutes: int = 30) -> bool:
        return (time.time() - self.last_active) > timeout_minutes * 60


# ===== 核心分析器 =====

class BuffettOracleAnalyzer:
    def __init__(self):
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

        self._api_key = api_key
        self._llm = None
        self._sessions: dict[str, ChatSession] = {}
        if api_key:
            self._llm = ChatOpenAI(
                model=model,
                openai_api_key=api_key,
                openai_api_base=base_url,
                temperature=0.3,
                max_tokens=4096,
                timeout=120,
            )

    def _get_or_create_session(self, session_id: str) -> ChatSession:
        if not session_id or session_id not in self._sessions:
            session_id = session_id or uuid.uuid4().hex
            self._sessions[session_id] = ChatSession(session_id)
        # 清理过期会话
        expired = [sid for sid, s in self._sessions.items() if s.is_expired()]
        for sid in expired:
            del self._sessions[sid]
        return self._sessions.get(session_id) or self._get_or_create_session("")

    async def chat(self, message: str, session_id: str = "", stock_code: str = "") -> dict:
        """多轮对话"""
        if not self._api_key:
            return {"status": "error", "session_id": session_id, "message": "API Key 未配置"}

        session = self._get_or_create_session(session_id)

        # 股票代码：首次全量收集，后续追问只刷新实时行情
        if stock_code and stock_code.isdigit() and len(stock_code) == 6:
            if stock_code != session.stock_code:
                session.stock_code = stock_code
                session.stock_data = await _collect_all_data(stock_code)
            elif session.stock_data:
                fresh = await _get_financial_summary(stock_code)
                if fresh and "失败" not in fresh:
                    session.stock_data["financial"] = fresh

        # 构建消息列表
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

        lc_messages = [SystemMessage(content=SYSTEM_PROMPT)]
        if session.stock_data:
            lc_messages.append(SystemMessage(content=f"[实时数据] 当前分析股票: {session.stock_code}"))
            lc_messages.append(SystemMessage(content=_build_stock_context(session.stock_data)))

        # 追加历史消息（最近20条，约10轮对话）
        recent = session.messages[-20:]
        for msg in recent:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            else:
                lc_messages.append(AIMessage(content=msg["content"]))

        # 追加当前用户消息
        lc_messages.append(HumanMessage(content=message))

        # 调用 LLM
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, self._llm.invoke, lc_messages)
            raw = response.content if hasattr(response, "content") else str(response)
            if isinstance(raw, list):
                report = "".join(b.text if hasattr(b, "text") else str(b) for b in raw)
            else:
                report = str(raw)
        except Exception as e:
            error_msg = str(e)
            hint = "超时" if "time" in error_msg.lower() else "失败"
            return {"status": "error", "session_id": session.id, "message": f"AI 响应{hint}: {error_msg}"}

        # 更新会话
        session.add_message("user", message)
        session.add_message("assistant", report)

        # 提取评分
        score = None
        for pat in [
            r"\*\*综合评分?\*\*\s*\|\s*\*?\*?(\d+\.?\d*)/10",
            r"\*\*综合\*\*\s*\|\s*\*?\*?(\d+\.?\d*)/10",
            r"综合评分[：:]\s*\*?\*?(\d+\.?\d*)/10",
            r"综合[：:]\s*\*?\*?(\d+\.?\d*)/10",
        ]:
            m = re.search(pat, report)
            if m:
                score = float(m.group(1))
                score = int(score) if score == int(score) else score
                break

        return {
            "status": "success",
            "session_id": session.id,
            "reply": report,
            "score": score,
            "stock_code": session.stock_code,
        }

    async def chat_stream(self, message: str, session_id: str = "", stock_code: str = ""):
        """多轮对话 - SSE 流式输出"""
        if not self._api_key:
            yield f"data: {json.dumps({'type': 'error', 'message': 'API Key 未配置'})}\n\n"
            return

        session = self._get_or_create_session(session_id)

        # 股票代码：首次全量收集，后续追问只刷新实时行情
        if stock_code and stock_code.isdigit() and len(stock_code) == 6:
            if stock_code != session.stock_code:
                session.stock_code = stock_code
                session.stock_data = await _collect_all_data(stock_code)
                yield f"data: {json.dumps({'type': 'context', 'stock_code': stock_code, 'session_id': session.id})}\n\n"
            elif session.stock_data:
                fresh = await _get_financial_summary(stock_code)
                if fresh and "失败" not in fresh:
                    session.stock_data["financial"] = fresh

        # 构建消息
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
        lc_messages = [SystemMessage(content=SYSTEM_PROMPT)]
        if session.stock_data:
            lc_messages.append(SystemMessage(content=f"[实时数据] 当前分析股票: {session.stock_code}"))
            lc_messages.append(SystemMessage(content=_build_stock_context(session.stock_data)))
        for msg in session.messages[-20:]:
            role_cls = HumanMessage if msg["role"] == "user" else AIMessage
            lc_messages.append(role_cls(content=msg["content"]))
        lc_messages.append(HumanMessage(content=message))

        # 记录用户消息
        session.add_message("user", message)

        # 流式调用 LLM
        full_reply = ""
        try:
            loop = asyncio.get_event_loop()
            stream = await loop.run_in_executor(None, self._llm.stream, lc_messages)
            for chunk in stream:
                delta = chunk.content if hasattr(chunk, "content") else ""
                if isinstance(delta, list):
                    delta = "".join(b.text if hasattr(b, "text") else str(b) for b in delta)
                if delta:
                    full_reply += delta
                    yield f"data: {json.dumps({'type': 'token', 'content': delta})}\n\n"
        except Exception as e:
            error_msg = str(e)
            hint = "超时" if "time" in error_msg.lower() else "失败"
            yield f"data: {json.dumps({'type': 'error', 'message': f'AI 响应{hint}: {error_msg}'})}\n\n"
            return

        # 更新会话
        session.add_message("assistant", full_reply)

        # 提取评分
        score = None
        for pat in [
            r"\*\*综合评分?\*\*\s*\|\s*\*?\*?(\d+\.?\d*)/10",
            r"\*\*综合\*\*\s*\|\s*\*?\*?(\d+\.?\d*)/10",
            r"综合评分[：:]\s*\*?\*?(\d+\.?\d*)/10",
            r"综合[：:]\s*\*?\*?(\d+\.?\d*)/10",
        ]:
            m = re.search(pat, full_reply)
            if m:
                score = float(m.group(1))
                score = int(score) if score == int(score) else score
                break

        # 发送完成事件
        yield f"data: {json.dumps({'type': 'done', 'session_id': session.id, 'score': score, 'stock_code': session.stock_code})}\n\n"

    async def analyze(self, stock_code: str) -> dict:
        """单次全维度分析（向后兼容）"""
        if not stock_code or not stock_code.isdigit() or len(stock_code) != 6:
            return {"status": "error", "message": "无效的股票代码"}
        if not self._api_key:
            return {"status": "error", "message": "API Key 未配置"}

        data = await _collect_all_data(stock_code)
        from langchain_core.messages import SystemMessage, HumanMessage

        user_prompt = f"""请分析 A 股股票（代码: {stock_code}）：

{_build_stock_context(data)}

请按巴菲特价值投资框架进行全面分析，给出各维度评分和最终投资结论。"""

        try:
            messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, self._llm.invoke, messages)
            raw = response.content if hasattr(response, "content") else str(response)
            if isinstance(raw, list):
                report = "".join(b.text if hasattr(b, "text") else str(b) for b in raw)
            else:
                report = str(raw)
        except Exception as e:
            return {"status": "error", "message": f"AI 分析失败: {e}"}

        score = None
        for pat in [
            r"\*\*综合评分?\*\*\s*\|\s*\*?\*?(\d+\.?\d*)/10",
            r"\*\*综合\*\*\s*\|\s*\*?\*?(\d+\.?\d*)/10",
            r"综合评分[：:]\s*\*?\*?(\d+\.?\d*)/10",
            r"综合[：:]\s*\*?\*?(\d+\.?\d*)/10",
        ]:
            m = re.search(pat, report)
            if m:
                score = float(m.group(1))
                score = int(score) if score == int(score) else score
                break

        return {"status": "success", "stock_code": stock_code, "report": report, "score": score, "source_data": data}


SYSTEM_PROMPT = _load_system_prompt()
buffett_oracle = BuffettOracleAnalyzer()
