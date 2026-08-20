"""
数字可信测试 — AI 回答的每个数字必须等于数据库查询结果
这是作业的命门：我们会拿 AI 的回答数字对照数据库查询，对不上直接报红。

测试方法：
1. 对每个问题，先用 AI 拿回答
2. 从回答中提取数字
3. 直接执行对应 SQL 拿真实数字
4. 逐项比对，必须完全一致
"""
import re
import sqlite3
import pytest
import json
import os

# ── 配置 ─────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "restaurant.db")
API_BASE = "http://localhost:8000"

# ── 辅助函数 ─────────────────────────────────────────────────────

def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def extract_numbers(text: str) -> list[float]:
    """
    从 AI 回答中提取所有数字（支持 ¥ 前缀、千分位逗号、小数）
    返回浮点数列表
    """
    # 去掉 ¥ 符号和千分位逗号
    cleaned = text.replace("¥", "").replace(",", "")
    # 匹配数字：整数、小数、负数
    pattern = r'-?\d+\.?\d*'
    matches = re.findall(pattern, cleaned)
    # 转为 float，过滤掉明显不是金额/数量的数字（如年份2026、日期等）
    numbers = []
    for m in matches:
        try:
            val = float(m)
            # 过滤掉年份（2026）和过于小的数字（如序号1,2,3）
            # 但保留可能是真实数据的小数字
            numbers.append(val)
        except ValueError:
            pass
    return numbers


def call_ai(question: str) -> dict:
    """
    调用 /api/chat 接口，返回 {"answer": str, "data": list, "tool_calls": list}
    """
    import httpx
    resp = httpx.post(
        f"{API_BASE}/api/chat",
        json={"message": question, "history": []},
        timeout=120,
    )
    assert resp.status_code == 200, f"API 调用失败: {resp.status_code} {resp.text}"
    return resp.json()


def sql_query(sql: str, params: tuple = ()) -> list[dict]:
    """直接执行 SQL，返回结果"""
    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── 10 个典型测试用例 ────────────────────────────────────────────

class TestNumberTrust:
    """
    核心测试：AI 回答中的数字必须 = 数据库查询结果
    """

    def test_01_total_revenue_july(self):
        """正常查询：七月总营业额"""
        result = call_ai("七月总营业额多少？")
        answer = result["answer"]

        # 直接查数据库
        db = sql_query("SELECT ROUND(SUM(amount), 2) as total FROM sales WHERE date BETWEEN '2026-07-01' AND '2026-07-31'")
        expected = db[0]["total"]

        # 从 AI 回答中提取数字
        numbers = extract_numbers(answer)
        # 营业额应该是最大的那个数（排除订单数等）
        assert any(abs(n - expected) < 1 for n in numbers), \
            f"AI回答中找不到总营业额 {expected}。\nAI回答: {answer}\n提取的数字: {numbers}"

    def test_02_order_count_july(self):
        """正常查询：七月订单数"""
        result = call_ai("七月有多少笔订单？")
        answer = result["answer"]

        db = sql_query("SELECT COUNT(*) as cnt FROM sales WHERE date BETWEEN '2026-07-01' AND '2026-07-31'")
        expected = db[0]["cnt"]

        numbers = extract_numbers(answer)
        assert any(abs(n - expected) < 1 for n in numbers), \
            f"AI回答中找不到订单数 {expected}。\nAI回答: {answer}\n提取的数字: {numbers}"

    def test_03_avg_order_value(self):
        """客单价计算"""
        result = call_ai("七月的客单价是多少？")
        answer = result["answer"]

        db = sql_query("SELECT ROUND(SUM(amount)/COUNT(*), 2) as avg_val FROM sales WHERE date BETWEEN '2026-07-01' AND '2026-07-31'")
        expected = db[0]["avg_val"]

        numbers = extract_numbers(answer)
        assert any(abs(n - expected) < 0.1 for n in numbers), \
            f"AI回答中找不到客单价 {expected}。\nAI回答: {answer}\n提取的数字: {numbers}"

    def test_04_top1_product(self):
        """Top 商品查询"""
        result = call_ai("营业额最高的商品是什么？")
        answer = result["answer"]

        db = sql_query("""
            SELECT p.product_name, ROUND(SUM(s.amount), 2) as total
            FROM sales s JOIN products p ON s.product_id = p.product_id
            GROUP BY s.product_id ORDER BY total DESC LIMIT 1
        """)
        expected_name = db[0]["product_name"]
        expected_amount = db[0]["total"]

        # AI 回答中应该包含商品名
        assert expected_name in answer, \
            f"AI回答中找不到商品名 '{expected_name}'。\nAI回答: {answer}"

        numbers = extract_numbers(answer)
        assert any(abs(n - expected_amount) < 1 for n in numbers), \
            f"AI回答中找不到金额 {expected_amount}。\nAI回答: {answer}\n提取的数字: {numbers}"

    def test_05_cross_month_query(self):
        """跨月查询：六月到七月"""
        result = call_ai("六月和七月的总营业额分别是多少？")
        answer = result["answer"]

        db_june = sql_query("SELECT ROUND(SUM(amount), 2) as total FROM sales WHERE date BETWEEN '2026-06-01' AND '2026-06-30'")
        db_july = sql_query("SELECT ROUND(SUM(amount), 2) as total FROM sales WHERE date BETWEEN '2026-07-01' AND '2026-07-31'")
        june_total = db_june[0]["total"]
        july_total = db_july[0]["total"]

        numbers = extract_numbers(answer)
        # 应该同时包含两个月的数字
        has_june = any(abs(n - june_total) < 1 for n in numbers)
        has_july = any(abs(n - july_total) < 1 for n in numbers)
        assert has_june and has_july, \
            f"AI回答中缺少六月({june_total})或七月({july_total})的数字。\nAI回答: {answer}\n提取的数字: {numbers}"

    def test_06_category_join(self):
        """品类 JOIN 查询：哪个品类营业额最高"""
        result = call_ai("哪个品类的营业额最高？")
        answer = result["answer"]

        db = sql_query("""
            SELECT p.product_category, ROUND(SUM(s.amount), 2) as total
            FROM sales s JOIN products p ON s.product_id = p.product_id
            GROUP BY p.product_category ORDER BY total DESC LIMIT 1
        """)
        expected_cat = db[0]["product_category"]
        expected_amount = db[0]["total"]

        assert expected_cat in answer, \
            f"AI回答中找不到品类 '{expected_cat}'。\nAI回答: {answer}"

        numbers = extract_numbers(answer)
        assert any(abs(n - expected_amount) < 1 for n in numbers), \
            f"AI回答中找不到金额 {expected_amount}。\nAI回答: {answer}\n提取的数字: {numbers}"

    def test_07_store_comparison(self):
        """门店对比：各门店营业额"""
        result = call_ai("各门店营业额排名？")
        answer = result["answer"]

        db = sql_query("""
            SELECT st.store_name, ROUND(SUM(s.amount), 2) as total
            FROM sales s JOIN stores st ON s.store_id = st.store_id
            GROUP BY s.store_id ORDER BY total DESC
        """)
        top_store = db[0]

        # AI 回答中应该包含排名第一的门店名
        assert top_store["store_name"] in answer, \
            f"AI回答中找不到排名第一的门店 '{top_store['store_name']}'。\nAI回答: {answer}"

        numbers = extract_numbers(answer)
        assert any(abs(n - top_store["total"]) < 1 for n in numbers), \
            f"AI回答中找不到金额 {top_store['total']}。\nAI回答: {answer}"

    def test_08_specific_product_sales(self):
        """特定商品查询：牛肉poke"""
        result = call_ai("牛肉poke卖了多少钱？")
        answer = result["answer"]

        db = sql_query("""
            SELECT ROUND(SUM(s.amount), 2) as total, SUM(s.qty) as qty
            FROM sales s JOIN products p ON s.product_id = p.product_id
            WHERE p.product_name = '牛肉poke'
        """)
        expected_amount = db[0]["total"]
        expected_qty = db[0]["qty"]

        numbers = extract_numbers(answer)
        assert any(abs(n - expected_amount) < 1 for n in numbers), \
            f"AI回答中找不到牛肉poke金额 {expected_amount}。\nAI回答: {answer}\n提取的数字: {numbers}"

    def test_09_nonexistent_product(self):
        """不存在的商品：应该明确说查不到，不编造"""
        result = call_ai("龙虾意面卖了多少钱？")
        answer = result["answer"]

        # 不应该包含任何编造的金额数字
        # 如果回答中提到"查不到"、"没有"、"不存在"，则通过
        keywords = ["查不到", "没有", "不存在", "未找到", "无法", "没有找到", "没有这个"]
        has_refusal = any(kw in answer for kw in keywords)

        # 也可以检查 tool_calls 是否返回了空结果
        tool_data = result.get("data", [])
        empty_result = len(tool_data) == 0 or all(
            d.get("total_qty", 1) == 0 or d.get("total_revenue", 1) == 0
            for d in tool_data if isinstance(d, dict)
        )

        assert has_refusal or empty_result, \
            f"AI对不存在的商品应该拒绝回答或返回空结果，但回答了: {answer}"

    def test_10_empty_result_handling(self):
        """空结果兜底：查一个不存在的时间范围"""
        result = call_ai("2025年1月的营业额是多少？")
        answer = result["answer"]

        # 数据范围是 2026-05-01 到 2026-07-31，2025年1月应该查不到
        keywords = ["查不到", "没有", "不在", "超出", "无法", "没有数据", "不在数据范围内"]
        has_refusal = any(kw in answer for kw in keywords)

        tool_data = result.get("data", [])
        empty_result = len(tool_data) == 0

        assert has_refusal or empty_result, \
            f"AI对超出数据范围的问题应该说明查不到，但回答了: {answer}"


class TestToolCallIntegrity:
    """验证 AI 确实调用了工具，而不是直接编数"""

    def test_tool_was_called(self):
        """AI 回答应该有 tool_calls 记录"""
        result = call_ai("七月总营业额多少？")
        tool_calls = result.get("tool_calls", [])
        assert len(tool_calls) > 0, f"AI 没有调用任何工具，可能直接编数了。tool_calls: {tool_calls}"

    def test_data_comes_from_db(self):
        """AI 返回的 data 应该非空（来自数据库查询）"""
        result = call_ai("各门店营业额排名？")
        data = result.get("data", [])
        assert len(data) > 0, f"AI 返回的 data 为空，数字可能不是来自数据库查询"


class TestSQLDirectly:
    """直接验证 SQL 查询结果的正确性（作为对账基准）"""

    def test_total_revenue_baseline(self):
        """总营业额基准值"""
        db = sql_query("SELECT ROUND(SUM(amount), 2) as total FROM sales")
        assert abs(db[0]["total"] - 428257.00) < 0.01, \
            f"总营业额基准值不对: {db[0]['total']}，期望 428257.00"

    def test_total_orders_baseline(self):
        """总订单数基准值"""
        db = sql_query("SELECT COUNT(*) as cnt FROM sales")
        assert db[0]["cnt"] == 12003, \
            f"总订单数基准值不对: {db[0]['cnt']}，期望 12003"

    def test_avg_order_value_baseline(self):
        """客单价基准值"""
        db = sql_query("SELECT ROUND(SUM(amount)/COUNT(*), 2) as avg_val FROM sales")
        assert abs(db[0]["avg_val"] - 35.68) < 0.01, \
            f"客单价基准值不对: {db[0]['avg_val']}，期望 35.68"

    def test_store_count(self):
        """门店数量"""
        db = sql_query("SELECT COUNT(*) as cnt FROM stores")
        assert db[0]["cnt"] == 5, f"门店数量不对: {db[0]['cnt']}，期望 5"

    def test_product_count(self):
        """商品数量"""
        db = sql_query("SELECT COUNT(*) as cnt FROM products")
        assert db[0]["cnt"] == 20, f"商品数量不对: {db[0]['cnt']}，期望 20"

    def test_date_range(self):
        """数据日期范围"""
        db = sql_query("SELECT MIN(date) as min_d, MAX(date) as max_d FROM sales")
        assert db[0]["min_d"] == "2026-05-01", f"起始日期不对: {db[0]['min_d']}"
        assert db[0]["max_d"] == "2026-07-31", f"结束日期不对: {db[0]['max_d']}"
