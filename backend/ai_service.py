"""
AI 问答服务 — DeepSeek function calling
核心原则：数字只来自数据库查询，AI 负责理解问题 + 生成 SQL 参数

工具拆分为 8 个细粒度函数，每个函数对应一种业务查询场景。
"""
import json
import os
import httpx
from datetime import datetime, timedelta

# 加载 .env 文件（支持 UTF-8 BOM 和 UTF-16）
try:
    from dotenv import load_dotenv
    import pathlib
    _env_path = pathlib.Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path, encoding="utf-8-sig")
except Exception:
    pass

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# 当前数据年份（用于"今年""六月"等相对日期解析）
DATA_YEAR = 2026
DATA_START = f"{DATA_YEAR}-05-01"
DATA_END = f"{DATA_YEAR}-07-31"

# ── 8 个细粒度 Function Calling 工具定义 ─────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_daily_trend",
            "description": "查询指定日期区间的每日营业额、订单数、客单价趋势",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": f"开始日期 YYYY-MM-DD，数据范围 {DATA_START}~{DATA_END}"},
                    "end_date": {"type": "string", "description": "结束日期 YYYY-MM-DD"},
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_top_products",
            "description": "查询指定日期区间内营业额最高的 Top N 商品",
            "parameters": {
                "type": "object",
                "properties": {
                    "n": {"type": "integer", "description": "返回前N个商品，默认10"},
                    "start_date": {"type": "string", "description": "开始日期 YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "结束日期 YYYY-MM-DD"},
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_revenue_by_store",
            "description": "查询指定日期区间内各门店的营业额排名",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "开始日期 YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "结束日期 YYYY-MM-DD"},
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_revenue_by_category",
            "description": "查询指定日期区间内各品类的营业额（需要JOIN商品表）",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "开始日期 YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "结束日期 YYYY-MM-DD"},
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_store_category_rank",
            "description": "查询某个品类在各门店的营业额排名，用于'某品类哪个门店卖得最好'",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "商品品类，如：主食、点心、小食、饮料"},
                    "start_date": {"type": "string", "description": "开始日期 YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "结束日期 YYYY-MM-DD"},
                },
                "required": ["category", "start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_product_sales",
            "description": "查询某个商品名称在指定日期区间的销售额、销量。用于'XX卖了多少钱'",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string", "description": "商品名称关键词，如：牛肉poke、豚骨拉面、小笼包"},
                    "start_date": {"type": "string", "description": "开始日期 YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "结束日期 YYYY-MM-DD"},
                },
                "required": ["product_name", "start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_product_category_sales",
            "description": "查询某个品类在指定日期区间的总销售额、总销量",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "商品品类，如：主食、点心、小食、饮料"},
                    "start_date": {"type": "string", "description": "开始日期 YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "结束日期 YYYY-MM-DD"},
                },
                "required": ["category", "start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_avg_order_value_trend",
            "description": "查询指定日期区间的客单价趋势，用于判断客单价涨跌",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "开始日期 YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "结束日期 YYYY-MM-DD"},
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
]

SYSTEM_PROMPT = f"""你是连锁餐饮经营数据分析助手，用户用中文问数据问题，你必须用真实查询结果回答。

【可用工具】(只能调用这些，禁止编造数字)
- query_daily_trend(start, end)                 每日营业额/订单数/客单价
- query_top_products(n, start, end)             Top N 商品
- query_revenue_by_store(start, end)            各门店营业额
- query_revenue_by_category(start, end)         各品类营业额(需要JOIN商品表)
- query_store_category_rank(category, start, end) 某品类各门店营业额
- query_product_sales(name, start, end)         某商品销售额
- query_product_category_sales(category, start, end) 某品类销售额
- query_avg_order_value_trend(start, end)       客单价趋势

【硬性规则】
1. 所有数字必须来自工具返回结果，原样引用，禁止估算、推测、编造。
2. 用户问题无法用工具回答时，明确回复"这个问题我查不到"并建议可问方向，禁止编造。
3. 日期默认{DATA_YEAR}年；"最近"默认最近7天（{DATA_END}往前7天）；"六月"解析为{DATA_YEAR}年6月。
4. 先调用工具拿到真实名称再回答，不要凭记忆说商品/门店名。
5. 回答格式：先给结论数字，再给一句解释，最后标注数据来源区间。
6. 金额保留两位小数，用¥符号。

【门店信息】
- S01 Super Souper（拉面，上海·徐汇）
- S02 Makai Poke（轻食，上海·静安）
- S03 Juicy Bao Bao（点心，上海·浦东）
- S04 Arigato Sando（三明治，上海·长宁）
- S05 Super Tetsudo（日料，上海·黄浦）

【商品品类】主食、点心、小食、饮料
【数据时间范围】{DATA_START} 至 {DATA_END}
"""


def _resolve_dates(start_date: str, end_date: str) -> tuple[str, str]:
    """日期解析辅助：处理相对日期"""
    today = datetime(DATA_YEAR, 7, 31)  # 数据最新日期
    if start_date == "最近":
        start_date = (today - timedelta(days=6)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    return start_date, end_date


# ── 工具路由：根据函数名分发到对应的 SQL 查询 ─────────────────────
def execute_tool(fn_name: str, fn_args: dict, db_conn_fn) -> list[dict]:
    """
    统一工具执行入口。
    db_conn_fn: 返回 sqlite3.Connection 的上下文管理器
    """
    from backend.app import get_db

    with get_db() as conn:
        conn.row_factory = None  # 返回 tuple
        cur = conn.cursor()

        start, end = _resolve_dates(fn_args.get("start_date", DATA_START), fn_args.get("end_date", DATA_END))

        if fn_name == "query_daily_trend":
            rows = cur.execute("""
                SELECT date, SUM(amount) as revenue, COUNT(*) as order_count,
                       ROUND(SUM(amount)/COUNT(*), 2) as avg_order_value
                FROM sales WHERE date BETWEEN ? AND ?
                GROUP BY date ORDER BY date
            """, (start, end)).fetchall()
            return [{"date": r[0], "revenue": r[1], "order_count": r[2], "avg_order_value": r[3]} for r in rows]

        elif fn_name == "query_top_products":
            n = fn_args.get("n", 10)
            rows = cur.execute("""
                SELECT p.product_name, p.product_category, SUM(s.qty) as total_qty,
                       ROUND(SUM(s.amount), 2) as total_revenue
                FROM sales s JOIN products p ON s.product_id = p.product_id
                WHERE s.date BETWEEN ? AND ?
                GROUP BY s.product_id ORDER BY total_revenue DESC LIMIT ?
            """, (start, end, n)).fetchall()
            return [{"product_name": r[0], "category": r[1], "total_qty": r[2], "total_revenue": r[3]} for r in rows]

        elif fn_name == "query_revenue_by_store":
            rows = cur.execute("""
                SELECT st.store_name, st.district, st.category,
                       SUM(s.amount) as total_revenue, COUNT(*) as order_count,
                       ROUND(SUM(s.amount)/COUNT(*), 2) as avg_order_value
                FROM sales s JOIN stores st ON s.store_id = st.store_id
                WHERE s.date BETWEEN ? AND ?
                GROUP BY s.store_id ORDER BY total_revenue DESC
            """, (start, end)).fetchall()
            return [{"store_name": r[0], "district": r[1], "store_category": r[2],
                     "total_revenue": r[3], "order_count": r[4], "avg_order_value": r[5]} for r in rows]

        elif fn_name == "query_revenue_by_category":
            rows = cur.execute("""
                SELECT p.product_category, SUM(s.qty) as total_qty,
                       ROUND(SUM(s.amount), 2) as total_revenue, COUNT(*) as order_count
                FROM sales s JOIN products p ON s.product_id = p.product_id
                WHERE s.date BETWEEN ? AND ?
                GROUP BY p.product_category ORDER BY total_revenue DESC
            """, (start, end)).fetchall()
            return [{"category": r[0], "total_qty": r[1], "total_revenue": r[2], "order_count": r[3]} for r in rows]

        elif fn_name == "query_store_category_rank":
            category = fn_args["category"]
            rows = cur.execute("""
                SELECT st.store_name, SUM(s.qty) as total_qty,
                       ROUND(SUM(s.amount), 2) as total_revenue
                FROM sales s
                JOIN stores st ON s.store_id = st.store_id
                JOIN products p ON s.product_id = p.product_id
                WHERE p.product_category = ? AND s.date BETWEEN ? AND ?
                GROUP BY s.store_id ORDER BY total_revenue DESC
            """, (category, start, end)).fetchall()
            return [{"store_name": r[0], "total_qty": r[1], "total_revenue": r[2]} for r in rows]

        elif fn_name == "query_product_sales":
            name = fn_args["product_name"]
            rows = cur.execute("""
                SELECT p.product_name, p.product_category, p.unit_price,
                       SUM(s.qty) as total_qty, ROUND(SUM(s.amount), 2) as total_revenue
                FROM sales s JOIN products p ON s.product_id = p.product_id
                WHERE p.product_name LIKE ? AND s.date BETWEEN ? AND ?
                GROUP BY s.product_id
            """, (f"%{name}%", start, end)).fetchall()
            return [{"product_name": r[0], "category": r[1], "unit_price": r[2],
                     "total_qty": r[3], "total_revenue": r[4]} for r in rows]

        elif fn_name == "query_product_category_sales":
            category = fn_args["category"]
            rows = cur.execute("""
                SELECT p.product_category, SUM(s.qty) as total_qty,
                       ROUND(SUM(s.amount), 2) as total_revenue, COUNT(*) as order_count
                FROM sales s JOIN products p ON s.product_id = p.product_id
                WHERE p.product_category = ? AND s.date BETWEEN ? AND ?
                GROUP BY p.product_category
            """, (category, start, end)).fetchall()
            return [{"category": r[0], "total_qty": r[1], "total_revenue": r[2], "order_count": r[3]} for r in rows]

        elif fn_name == "query_avg_order_value_trend":
            rows = cur.execute("""
                SELECT date, ROUND(SUM(amount)/COUNT(*), 2) as avg_order_value,
                       COUNT(*) as order_count
                FROM sales WHERE date BETWEEN ? AND ?
                GROUP BY date ORDER BY date
            """, (start, end)).fetchall()
            return [{"date": r[0], "avg_order_value": r[1], "order_count": r[2]} for r in rows]

        else:
            return [{"error": f"未知工具: {fn_name}"}]


# ── 非流式问答 ──────────────────────────────────────────────────
async def chat_with_ai(
    user_message: str,
    history: list[dict],
    execute_query_fn,  # 保留兼容，但内部用 execute_tool
) -> dict:
    if not DEEPSEEK_API_KEY:
        return {
            "answer": "⚠️ 未配置 DEEPSEEK_API_KEY，请在项目根目录创建 .env 文件：\n```\nDEEPSEEK_API_KEY=sk-xxx\n```",
            "data": [],
            "tool_calls": [],
        }

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    tool_calls_log = []
    all_query_data = []

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "tools": TOOLS,
                "tool_choice": "auto",
                "temperature": 0.1,
                "max_tokens": 2000,
            },
        )

        if resp.status_code != 200:
            return {"answer": f"AI 服务错误 (HTTP {resp.status_code})", "data": [], "tool_calls": []}

        result = resp.json()
        message = result["choices"][0]["message"]

        if message.get("tool_calls"):
            messages.append(message)

            for tc in message["tool_calls"]:
                fn_name = tc["function"]["name"]
                fn_args = json.loads(tc["function"]["arguments"])

                tool_calls_log.append({"function": fn_name, "arguments": fn_args})

                # 执行真实数据库查询
                query_result = execute_tool(fn_name, fn_args, None)
                all_query_data.extend(query_result)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(query_result, ensure_ascii=False),
                })

            # 第二轮：AI 根据真实数据回答
            resp2 = await client.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                json={"model": "deepseek-chat", "messages": messages, "temperature": 0.1, "max_tokens": 2000},
            )

            if resp2.status_code != 200:
                return {"answer": f"AI 二次调用错误", "data": all_query_data, "tool_calls": tool_calls_log}

            answer = resp2.json()["choices"][0]["message"]["content"]
        else:
            answer = message.get("content", "无法生成回答")

    return {"answer": answer, "data": all_query_data, "tool_calls": tool_calls_log}


# ── SSE 流式版本 ─────────────────────────────────────────────────
async def chat_with_ai_stream(
    user_message: str,
    history: list[dict],
    execute_query_fn,
):
    if not DEEPSEEK_API_KEY:
        yield {"type": "error", "message": "未配置 DEEPSEEK_API_KEY，请在项目根目录创建 .env 文件。"}
        return

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    tool_calls_log = []
    all_query_data = []

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "tools": TOOLS,
                "tool_choice": "auto",
                "temperature": 0.1,
                "max_tokens": 2000,
            },
        )

        if resp.status_code != 200:
            yield {"type": "error", "message": f"AI 服务错误 (HTTP {resp.status_code})"}
            return

        result = resp.json()
        message = result["choices"][0]["message"]

        if message.get("tool_calls"):
            messages.append(message)

            for tc in message["tool_calls"]:
                fn_name = tc["function"]["name"]
                fn_args = json.loads(tc["function"]["arguments"])

                tool_call_info = {"function": fn_name, "arguments": fn_args}
                tool_calls_log.append(tool_call_info)
                yield {"type": "tool_call", **tool_call_info}

                query_result = execute_tool(fn_name, fn_args, None)
                all_query_data.extend(query_result)
                yield {"type": "tool_result", "function": fn_name, "count": len(query_result)}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(query_result, ensure_ascii=False),
                })

            # 流式回答
            full_answer = ""
            async with client.stream(
                "POST",
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                json={"model": "deepseek-chat", "messages": messages, "temperature": 0.1, "max_tokens": 2000, "stream": True},
            ) as resp2:
                if resp2.status_code != 200:
                    yield {"type": "error", "message": f"AI 二次调用错误 (HTTP {resp2.status_code})"}
                    return

                async for line in resp2.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    token = chunk["choices"][0].get("delta", {}).get("content", "")
                    if token:
                        full_answer += token
                        yield {"type": "token", "content": token}
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue

            yield {"type": "done", "answer": full_answer, "data": all_query_data, "tool_calls": tool_calls_log}
        else:
            answer = message.get("content", "")
            if answer:
                for char in answer:
                    yield {"type": "token", "content": char}
            yield {"type": "done", "answer": answer, "data": [], "tool_calls": []}
