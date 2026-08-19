"""
AI 问答服务 — DeepSeek function calling
核心原则：数字只来自数据库查询，AI 负责理解问题 + 生成 SQL 参数
"""
import json
import os
import httpx
from typing import Optional

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# ── Function Calling 工具定义 ────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_sales_data",
            "description": "查询销售数据。返回的数字来自数据库真实查询。可按日期/门店/商品/品类/支付方式分组。",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "开始日期，格式 YYYY-MM-DD"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "结束日期，格式 YYYY-MM-DD"
                    },
                    "store_id": {
                        "type": "string",
                        "description": "门店ID，如 S01。不填则查全部门店",
                        "enum": ["S01", "S02", "S03", "S04", "S05"]
                    },
                    "product_id": {
                        "type": "string",
                        "description": "商品ID，如 P01。不填则查全部商品"
                    },
                    "group_by": {
                        "type": "string",
                        "description": "分组维度",
                        "enum": ["date", "store", "product", "category", "payment"]
                    }
                },
                "required": ["start_date", "end_date", "group_by"]
            }
        }
    }
]

SYSTEM_PROMPT = """你是一个连锁餐饮数据分析助手。你服务的公司有5家门店：
- S01 Super Souper（拉面，上海·徐汇）
- S02 Makai Poke（轻食，上海·静安）
- S03 Juicy Bao Bao（点心，上海·浦东）
- S04 Arigato Sando（三明治，上海·长宁）
- S05 Super Tetsudo（日料，上海·黄浦）

商品品类：主食、点心、小食、饮料
数据时间范围：2026-05-01 至 2026-07-31

你的回答规则：
1. 每个数字必须来自 query_sales_data 函数的返回结果，绝不编造数字
2. 如果用户的问题无法用现有数据回答，明确告知
3. 回答要简洁专业，用中文，数字保留两位小数
4. 如果用户问的是趋势，指出涨跌方向和具体数值
5. 如果用户没有指定时间范围，默认查最近一个月（2026-07-01 至 2026-07-31）
"""


async def chat_with_ai(
    user_message: str,
    history: list[dict],
    execute_query_fn,
) -> dict:
    """
    AI 问答主流程：
    1. 发送消息给 DeepSeek
    2. 如果 AI 调用 function → 执行查询 → 将结果回传
    3. AI 根据真实数据生成最终回答

    返回: {"answer": str, "data": list[dict], "tool_calls": list}
    """
    if not DEEPSEEK_API_KEY:
        return {
            "answer": "⚠️ 未配置 DEEPSEEK_API_KEY，请设置环境变量后重启服务。\n\n你可以在 .env 文件中写入：\n```\nDEEPSEEK_API_KEY=sk-xxx\n```",
            "data": [],
            "tool_calls": [],
        }

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    tool_calls_log = []
    all_query_data = []

    async with httpx.AsyncClient(timeout=60) as client:
        # 第一轮：发送给 DeepSeek，可能触发 function calling
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "tools": TOOLS,
                "tool_choice": "auto",
                "temperature": 0.1,  # 低温度减少编造
                "max_tokens": 2000,
            },
        )

        if resp.status_code != 200:
            return {
                "answer": f"AI 服务错误 (HTTP {resp.status_code}): {resp.text}",
                "data": [],
                "tool_calls": [],
            }

        result = resp.json()
        choice = result["choices"][0]
        message = choice["message"]

        # 如果 AI 调用了工具
        if message.get("tool_calls"):
            messages.append(message)  # 追加 assistant 消息

            for tc in message["tool_calls"]:
                fn_name = tc["function"]["name"]
                fn_args = json.loads(tc["function"]["arguments"])

                tool_calls_log.append({
                    "function": fn_name,
                    "arguments": fn_args,
                })

                # 执行真实数据库查询
                query_result = execute_query_fn(**fn_args)
                all_query_data.extend(query_result)

                # 将查询结果回传给 AI
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(query_result, ensure_ascii=False),
                })

            # 第二轮：AI 根据查询结果生成最终回答
            resp2 = await client.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 2000,
                },
            )

            if resp2.status_code != 200:
                return {
                    "answer": f"AI 二次调用错误 (HTTP {resp2.status_code})",
                    "data": all_query_data,
                    "tool_calls": tool_calls_log,
                }

            final = resp2.json()
            answer = final["choices"][0]["message"]["content"]
        else:
            # AI 直接回答（未调用工具）
            answer = message.get("content", "无法生成回答")

    return {
        "answer": answer,
        "data": all_query_data,
        "tool_calls": tool_calls_log,
    }
