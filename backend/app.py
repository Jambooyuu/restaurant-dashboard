"""
FastAPI 后端 — 连锁餐饮数据分析看板
所有数字来自 SQLite 真实查询，禁止大模型编数
"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import date
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ── 数据库路径 ──────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "restaurant.db")


@contextmanager
def get_db():
    """数据库连接上下文管理器"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ── FastAPI 应用 ────────────────────────────────────────────────
app = FastAPI(
    title="连锁餐饮数据分析 API",
    description="5 门店销售数据看板 + AI 问答，所有数字来自数据库真实查询",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic 模型 ──────────────────────────────────────────────
class DailyStats(BaseModel):
    date: str
    revenue: float
    order_count: int
    avg_order_value: float


class TopProduct(BaseModel):
    product_id: str
    product_name: str
    product_category: str
    total_qty: int
    total_revenue: float


class StoreSummary(BaseModel):
    store_id: str
    store_name: str
    district: str
    category: str
    total_revenue: float
    order_count: int
    avg_order_value: float


class PaymentBreakdown(BaseModel):
    payment: str
    count: int
    total: float


class DashboardResponse(BaseModel):
    daily_stats: list[DailyStats]
    top_products: list[TopProduct]
    summary: dict


# ── API 路由 ────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "连锁餐饮数据分析 API", "docs": "/docs"}


@app.get("/api/dashboard", response_model=DashboardResponse)
def get_dashboard(
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    store_id: Optional[str] = Query(None, description="门店ID筛选"),
):
    """
    核心看板接口：按日期区间返回每日营业额、订单数、客单价 + Top10 商品
    """
    with get_db() as conn:
        cur = conn.cursor()

        # ── 每日统计 ──
        where_clauses = ["date BETWEEN ? AND ?"]
        params: list = [start_date, end_date]
        if store_id:
            where_clauses.append("s.store_id = ?")
            params.append(store_id)
        where_sql = " AND ".join(where_clauses)

        daily_rows = cur.execute(f"""
            SELECT date,
                   SUM(amount) as revenue,
                   COUNT(*) as order_count,
                   ROUND(SUM(amount) / COUNT(*), 2) as avg_order_value
            FROM sales s
            WHERE {where_sql}
            GROUP BY date
            ORDER BY date
        """, params).fetchall()

        daily_stats = [
            DailyStats(
                date=r["date"],
                revenue=round(r["revenue"], 2),
                order_count=r["order_count"],
                avg_order_value=r["avg_order_value"],
            )
            for r in daily_rows
        ]

        # ── Top 10 商品 ──
        top_rows = cur.execute(f"""
            SELECT s.product_id,
                   p.product_name,
                   p.product_category,
                   SUM(s.qty) as total_qty,
                   ROUND(SUM(s.amount), 2) as total_revenue
            FROM sales s
            JOIN products p ON s.product_id = p.product_id
            WHERE {where_sql}
            GROUP BY s.product_id
            ORDER BY total_revenue DESC
            LIMIT 10
        """, params).fetchall()

        top_products = [
            TopProduct(
                product_id=r["product_id"],
                product_name=r["product_name"],
                product_category=r["product_category"],
                total_qty=r["total_qty"],
                total_revenue=r["total_revenue"],
            )
            for r in top_rows
        ]

        # ── 汇总指标 ──
        summary_row = cur.execute(f"""
            SELECT SUM(amount) as total_revenue,
                   COUNT(*) as total_orders,
                   ROUND(SUM(amount) / COUNT(*), 2) as avg_order_value
            FROM sales s
            WHERE {where_sql}
        """, params).fetchone()

        return DashboardResponse(
            daily_stats=daily_stats,
            top_products=top_products,
            summary={
                "total_revenue": round(summary_row["total_revenue"] or 0, 2),
                "total_orders": summary_row["total_orders"] or 0,
                "avg_order_value": summary_row["avg_order_value"] or 0,
                "start_date": start_date,
                "end_date": end_date,
            },
        )


@app.get("/api/stores")
def get_stores():
    """获取所有门店列表"""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM stores ORDER BY store_id").fetchall()
        return [dict(r) for r in rows]


@app.get("/api/products")
def get_products():
    """获取所有商品列表"""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM products ORDER BY product_id").fetchall()
        return [dict(r) for r in rows]


@app.get("/api/store-comparison")
def store_comparison(
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    """门店对比数据"""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT s.store_id,
                   st.store_name,
                   st.district,
                   st.category,
                   SUM(s.amount) as total_revenue,
                   COUNT(*) as order_count,
                   ROUND(SUM(s.amount) / COUNT(*), 2) as avg_order_value
            FROM sales s
            JOIN stores st ON s.store_id = st.store_id
            WHERE s.date BETWEEN ? AND ?
            GROUP BY s.store_id
            ORDER BY total_revenue DESC
        """, (start_date, end_date)).fetchall()
        return [dict(r) for r in rows]


@app.get("/api/payment-breakdown")
def payment_breakdown(
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    """支付方式分布"""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT payment,
                   COUNT(*) as count,
                   ROUND(SUM(amount), 2) as total
            FROM sales
            WHERE date BETWEEN ? AND ?
            GROUP BY payment
            ORDER BY total DESC
        """, (start_date, end_date)).fetchall()
        return [dict(r) for r in rows]


@app.get("/api/category-performance")
def category_performance(
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    """品类销售表现"""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT p.product_category,
                   SUM(s.qty) as total_qty,
                   ROUND(SUM(s.amount), 2) as total_revenue,
                   COUNT(*) as order_count
            FROM sales s
            JOIN products p ON s.product_id = p.product_id
            WHERE s.date BETWEEN ? AND ?
            GROUP BY p.product_category
            ORDER BY total_revenue DESC
        """, (start_date, end_date)).fetchall()
        return [dict(r) for r in rows]


# ── AI 查询专用函数（被 function calling 调用）──────────────────
def query_sales_data(
    start_date: str,
    end_date: str,
    store_id: Optional[str] = None,
    product_id: Optional[str] = None,
    group_by: str = "date",
) -> list[dict]:
    """
    通用查询函数 —— AI function calling 的唯一数据出口
    所有返回的数字都来自这条 SQL
    """
    with get_db() as conn:
        where = ["s.date BETWEEN ? AND ?"]
        params: list = [start_date, end_date]
        if store_id:
            where.append("s.store_id = ?")
            params.append(store_id)
        if product_id:
            where.append("s.product_id = ?")
            params.append(product_id)
        where_sql = " AND ".join(where)

        if group_by == "date":
            rows = conn.execute(f"""
                SELECT s.date as label,
                       SUM(s.amount) as revenue,
                       COUNT(*) as order_count,
                       ROUND(SUM(s.amount)/COUNT(*),2) as avg_order_value
                FROM sales s WHERE {where_sql}
                GROUP BY s.date ORDER BY s.date
            """, params).fetchall()
        elif group_by == "store":
            rows = conn.execute(f"""
                SELECT st.store_name as label,
                       SUM(s.amount) as revenue,
                       COUNT(*) as order_count,
                       ROUND(SUM(s.amount)/COUNT(*),2) as avg_order_value
                FROM sales s JOIN stores st ON s.store_id=st.store_id
                WHERE {where_sql}
                GROUP BY s.store_id ORDER BY revenue DESC
            """, params).fetchall()
        elif group_by == "product":
            rows = conn.execute(f"""
                SELECT p.product_name as label,
                       SUM(s.qty) as total_qty,
                       SUM(s.amount) as revenue,
                       COUNT(*) as order_count
                FROM sales s JOIN products p ON s.product_id=p.product_id
                WHERE {where_sql}
                GROUP BY s.product_id ORDER BY revenue DESC
            """, params).fetchall()
        elif group_by == "category":
            rows = conn.execute(f"""
                SELECT p.product_category as label,
                       SUM(s.qty) as total_qty,
                       SUM(s.amount) as revenue,
                       COUNT(*) as order_count
                FROM sales s JOIN products p ON s.product_id=p.product_id
                WHERE {where_sql}
                GROUP BY p.product_category ORDER BY revenue DESC
            """, params).fetchall()
        elif group_by == "payment":
            rows = conn.execute(f"""
                SELECT s.payment as label,
                       COUNT(*) as order_count,
                       SUM(s.amount) as revenue
                FROM sales s WHERE {where_sql}
                GROUP BY s.payment ORDER BY revenue DESC
            """, params).fetchall()
        else:
            raise ValueError(f"Unknown group_by: {group_by}")

        return [dict(r) for r in rows]


# ── AI 问答接口 ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []  # [{role, content}, ...]


class ChatResponse(BaseModel):
    answer: str
    data: list[dict]
    tool_calls: list[dict]


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """
    AI 问答入口（非流式）。DeepSeek 理解问题 → function calling 查数据库 → 基于真实数据回答。
    """
    from backend.ai_service import chat_with_ai

    result = await chat_with_ai(
        user_message=req.message,
        history=req.history,
        execute_query_fn=query_sales_data,
    )
    return ChatResponse(**result)


@app.post("/api/chat/stream")
async def chat_stream_endpoint(req: ChatRequest):
    """
    AI 问答入口（SSE 流式）。逐步返回 AI 回答，支持前端实时渲染。
    """
    from backend.ai_service import chat_with_ai_stream
    import json

    async def event_generator():
        async for chunk in chat_with_ai_stream(
            user_message=req.message,
            history=req.history,
            execute_query_fn=query_sales_data,
        ):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── 门店名/商品名映射查询（供 AI 或前端使用）────────────────────
@app.get("/api/lookup/store")
def lookup_store(name: str = Query(..., description="门店名关键词")):
    """按名称模糊查找门店"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM stores WHERE store_name LIKE ? OR store_id = ?",
            (f"%{name}%", name.upper()),
        ).fetchall()
        return [dict(r) for r in rows]


@app.get("/api/lookup/product")
def lookup_product(name: str = Query(..., description="商品名关键词")):
    """按名称模糊查找商品"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM products WHERE product_name LIKE ?",
            (f"%{name}%",),
        ).fetchall()
        return [dict(r) for r in rows]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
