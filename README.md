# 投资数据平台

一站式 A 股量化数据接入平台，整合五大免费数据源。

## 数据源

| 数据源 | 特点 |
|--------|------|
| **腾讯财经** | 实时行情、秒级响应、无需认证 |
| **mootdx** | K线数据、实时盘口、通达信协议 |
| **akshare** | 市场情绪、研报新闻、涨停板 |
| **同花顺热点** | 热点概念、强势股排行 |
| **问财** | 自然语言语义搜索选股 |

## 技术栈

- **前端**：Vue 3 + Element Plus + ECharts（红黑主题）
- **后端**：Python FastAPI + 五大免费数据源

## 启动

```bash
# 后端
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn main:app --port 8000 --reload

# 前端
cd frontend
npm install
npm run dev
```
