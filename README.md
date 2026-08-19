# 🍜 连锁餐饮数据分析看板 + AI 智能问答

5 家门店销售数据可视化看板，支持自然语言数据问答。

## 快速启动（3 步）

```bash
# 1. 安装依赖
pip install -r requirements.txt
cd frontend && pnpm install && cd ..

# 2. 初始化数据库（从 CSV 清洗入库）
python clean_and_load.py

# 3. 启动服务
# 终端 1：后端
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload

# 终端 2：前端
cd frontend && pnpm dev
```

- 前端看板：http://localhost:5173
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

### AI 问答配置

```bash
# 在项目根目录创建 .env 文件
echo DEEPSEEK_API_KEY=sk-your-key-here > .env
```

没有 API Key 时，AI 问答会提示配置，看板功能不受影响。

---

## 架构图

```
┌─────────────────────────────────────────────────────┐
│                    浏览器 (React)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │
│  │ 趋势图   │ │ 门店对比 │ │ 品类/支付│ │AI 对话 │  │
│  │ ECharts  │ │ ECharts  │ │ ECharts  │ │ChatPanel│  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘  │
│       │            │            │            │       │
│       └────────────┴─────┬──────┴────────────┘       │
│                          │ fetch                     │
└──────────────────────────┼───────────────────────────┘
                           │
┌──────────────────────────┼───────────────────────────┐
│               FastAPI 后端 (Python)                    │
│                          │                            │
│  /api/dashboard ─────────┤                            │
│  /api/store-comparison ──┤                            │
│  /api/category-performance                            │
│  /api/payment-breakdown ─┤                            │
│  /api/chat ──────────────┤                            │
│         │                │                            │
│    ┌────┴────┐     ┌─────┴─────┐                      │
│    │ SQL 查询 │     │ DeepSeek  │                      │
│    │ (SQLite) │     │ Function  │                      │
│    │         │     │ Calling   │                      │
│    └────┬────┘     └─────┬─────┘                      │
│         │                │                            │
│         └───────┬────────┘                            │
│                 │                                     │
│  ┌──────────────┴──────────────┐                      │
│  │      SQLite (restaurant.db) │                      │
│  │  sales / stores / products  │                      │
│  └─────────────────────────────┘                      │
└───────────────────────────────────────────────────────┘
```

### 防幻觉方案（AI 问答核心设计）

```
用户提问 → DeepSeek 理解意图 → 生成 function call 参数
    → query_sales_data() 执行真实 SQL → 返回数字给 AI
    → AI 基于真实数字生成自然语言回答
```

**关键约束：**
1. AI **不能直接访问数据库**，只能通过 `query_sales_data()` 函数
2. 该函数是**唯一数据出口**，所有数字都有对应 SQL
3. 回答中的每个数字都能追溯到一条 `SELECT ... GROUP BY` 的执行结果
4. 无法回答的问题（超出数据范围），AI 会明确告知而非编造

---

## 选型理由

| 组件 | 选择 | 理由 |
|------|------|------|
| 后端 | **FastAPI** | 贴 Python 栈、原生 async、自带 OpenAPI 文档、支持 SSE |
| 数据库 | **SQLite** | 零配置秒启动，作业友好；DAO 层已抽象，生产可换 Postgres |
| 前端 | **React + Vite** | 生态成熟、HMR 快速 |
| 图表 | **ECharts** | 专业级图表、交互丰富、中文支持好 |
| AI | **DeepSeek** | 几块钱跑完全程、中文好、支持 function calling |

---

## 数据清洗规则

原始 CSV 含 12,131 行，清洗后入库 12,003 行。

| 脏数据类型 | 行数 | 处理策略 |
|-----------|------|---------|
| 重复 order_id | 160 行 | 去重保留一行 |
| 日期格式不一 | 150 行 | 统一转 YYYY-MM-DD |
| amount 带 ¥ 前缀 | 40 行 | 去除符号保留数值 |
| 负金额（退款） | 49 行 | 保留在流水，自然纳入统计 |
| amount 为空 | 120 行 | 用 qty × unit_price 回填 |
| qty = 0 | 11 行 | 删除 |
| store_id 小写 s01 | 9 行 | 大写标准化 |
| 无效门店 S99 | 7 行 | 删除 |
| 无效商品 P99 | 30 行 | 删除 |

**核对结果：** 清洗后总营业额 ¥428,257.00，12,003 单，客单价 ¥35.68

---

## 项目结构

```
D:\DSWorkS\
├── README.md              # 本文件
├── AI_USAGE.md            # AI 工具使用说明
├── DEMO.md                # 演示说明
├── requirements.txt       # Python 依赖
├── .env.example           # 环境变量模板
├── clean_and_load.py      # 数据清洗 + 入库脚本
├── data/
│   └── restaurant.db      # SQLite 数据库（清洗后）
├── backend/
│   ├── __init__.py
│   ├── app.py             # FastAPI 主应用（API 路由）
│   └── ai_service.py      # DeepSeek AI 问答服务
└── frontend/
    ├── package.json
    ├── vite.config.mjs     # Vite 配置（含 API 代理）
    ├── index.html
    └── src/
        ├── main.jsx
        ├── index.css        # 全局样式
        ├── App.jsx          # 主页面（看板）
        └── components/
            ├── RevenueChart.jsx      # 营业额趋势图
            ├── StoreComparison.jsx   # 门店对比
            ├── CategoryPie.jsx       # 品类分布
            ├── PaymentPie.jsx        # 支付方式分布
            ├── TopProductsTable.jsx  # Top10 商品表
            └── ChatPanel.jsx         # AI 对话面板
```

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/dashboard` | 看板数据（每日统计 + Top10 商品） |
| GET | `/api/stores` | 门店列表 |
| GET | `/api/products` | 商品列表 |
| GET | `/api/store-comparison` | 门店对比 |
| GET | `/api/category-performance` | 品类表现 |
| GET | `/api/payment-breakdown` | 支付方式分布 |
| POST | `/api/chat` | AI 问答（DeepSeek + function calling） |
| GET | `/api/lookup/store` | 门店模糊查找 |
| GET | `/api/lookup/product` | 商品模糊查找 |
