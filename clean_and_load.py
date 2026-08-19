"""
数据清洗 + SQLite 入库脚本
读取三张 CSV → 按清洗规则处理 → 核对关键指标 → 写入 data/restaurant.db
"""
import csv, re, sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8')
from collections import Counter
from datetime import datetime

SALES_CSV = r'C:\Users\y\Downloads\sales.csv'
STORES_CSV = r'C:\Users\y\Downloads\stores.csv'
PRODUCTS_CSV = r'C:\Users\y\Downloads\products.csv'
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'restaurant.db')

# ── 1. 读取原始数据 ──────────────────────────────────────────────
def read_csv(path):
    with open(path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))

raw_sales = read_csv(SALES_CSV)
stores = read_csv(STORES_CSV)
products = read_csv(PRODUCTS_CSV)

print(f"原始 sales: {len(raw_sales)} 行")
print(f"stores: {len(stores)} 行")
print(f"products: {len(products)} 行")

# ── 2. 构建查找表 ────────────────────────────────────────────────
valid_stores = {s['store_id'] for s in stores}
valid_products = {p['product_id'] for p in products}
price_map = {p['product_id']: float(p['unit_price']) for p in products}

# ── 3. 逐行清洗 ──────────────────────────────────────────────────
seen_order_ids = set()
cleaned = []
drop_reasons = Counter()

for r in raw_sales:
    oid = r['order_id'].strip()
    store_id = r['store_id'].strip()
    product_id = r['product_id'].strip()
    date_raw = r['date'].strip()
    qty_raw = r['qty'].strip()
    amount_raw = r['amount'].strip()
    payment = r['payment'].strip()

    # ── 规则1: 重复 order_id 去重 ──
    if oid in seen_order_ids:
        drop_reasons['duplicate_order_id'] += 1
        continue
    seen_order_ids.add(oid)

    # ── 规则2+3: 日期格式统一 → YYYY-MM-DD ──
    date_clean = None
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_raw):
        date_clean = date_raw
    elif re.match(r'^\d{4}/\d{2}/\d{2}$', date_raw):
        date_clean = date_raw.replace('/', '-')
    elif re.match(r'^\d{2}-\d{2}-\d{4}$', date_raw):
        # DD-MM-YYYY
        parts = date_raw.split('-')
        date_clean = f"{parts[2]}-{parts[1]}-{parts[0]}"
    else:
        drop_reasons['bad_date'] += 1
        continue  # 无法解析的日期，丢弃

    # ── 规则4: amount 去除 ¥ 前缀 ──
    amount_str = amount_raw.replace('¥', '').replace('\xa5', '').strip()

    # ── 规则8: store_id 大写标准化 ──
    store_id = store_id.upper()

    # ── 规则9: 无效 store_id → 删除 ──
    if store_id not in valid_stores:
        drop_reasons['invalid_store'] += 1
        continue

    # ── 规则10: 无效 product_id → 删除 ──
    if product_id not in valid_products:
        drop_reasons['invalid_product'] += 1
        continue

    # ── 解析 qty ──
    try:
        qty = int(qty_raw)
    except (ValueError, TypeError):
        drop_reasons['bad_qty'] += 1
        continue

    # ── 规则7: qty=0 删除，qty<0 保留（退货） ──
    if qty == 0:
        drop_reasons['qty_zero'] += 1
        continue

    # ── 解析 amount ──
    if amount_str == '':
        # ── 规则6: 空 amount 用 qty × unit_price 回填 ──
        amount = abs(qty) * price_map[product_id]
        drop_reasons['amount_backfilled'] += 1
    else:
        try:
            amount = float(amount_str)
        except (ValueError, TypeError):
            drop_reasons['bad_amount'] += 1
            continue

    # ── 规则5: 负金额保留（退款） ──
    # ── 规则11: 保留原始 amount，不覆写 ──

    cleaned.append({
        'order_id': oid,
        'date': date_clean,
        'store_id': store_id,
        'product_id': product_id,
        'qty': qty,
        'amount': amount,
        'payment': payment,
    })

print(f"\n清洗后: {len(cleaned)} 行")
print(f"丢弃原因统计:")
for reason, cnt in drop_reasons.most_common():
    print(f"  {reason}: {cnt}")

# ── 4. 核对关键指标 ──────────────────────────────────────────────
total_revenue = sum(r['amount'] for r in cleaned)
total_orders = len(set(r['order_id'] for r in cleaned))
total_rows = len(cleaned)
avg_per_row = total_revenue / total_rows if total_rows else 0

print(f"\n{'='*50}")
print(f"清洗后核对指标:")
print(f"  总行数:          {total_rows}")
print(f"  唯一订单数:      {total_orders}")
print(f"  总营业额:        {total_revenue:.2f}")
print(f"  行均金额:        {avg_per_row:.2f}")
print(f"{'='*50}")

# 按门店统计
store_rev = {}
for r in cleaned:
    store_rev.setdefault(r['store_id'], 0)
    store_rev[r['store_id']] += r['amount']
print(f"\n门店营业额:")
for sid in sorted(store_rev):
    print(f"  {sid}: {store_rev[sid]:.2f}")

# 按日期统计（检查日期范围）
dates = sorted(set(r['date'] for r in cleaned))
print(f"\n日期范围: {dates[0]} ~ {dates[-1]} ({len(dates)} 天)")

# ── 5. 入库 SQLite ──────────────────────────────────────────────
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 建表
cur.executescript("""
CREATE TABLE stores (
    store_id TEXT PRIMARY KEY,
    store_name TEXT NOT NULL,
    category TEXT NOT NULL,
    district TEXT NOT NULL
);

CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    product_category TEXT NOT NULL,
    unit_price REAL NOT NULL
);

CREATE TABLE sales (
    order_id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    store_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    qty INTEGER NOT NULL,
    amount REAL NOT NULL,
    payment TEXT NOT NULL,
    FOREIGN KEY (store_id) REFERENCES stores(store_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE INDEX idx_sales_date ON sales(date);
CREATE INDEX idx_sales_store ON sales(store_id);
CREATE INDEX idx_sales_product ON sales(product_id);
CREATE INDEX idx_sales_date_store ON sales(date, store_id);
""")

# 插入 stores
for s in stores:
    cur.execute("INSERT INTO stores VALUES (?,?,?,?)",
                (s['store_id'], s['store_name'], s['category'], s['district']))

# 插入 products
for p in products:
    cur.execute("INSERT INTO products VALUES (?,?,?,?)",
                (p['product_id'], p['product_name'], p['product_category'], float(p['unit_price'])))

# 插入 sales
cur.executemany(
    "INSERT INTO sales VALUES (?,?,?,?,?,?,?)",
    [(r['order_id'], r['date'], r['store_id'], r['product_id'], r['qty'], r['amount'], r['payment'])
     for r in cleaned]
)

conn.commit()

# ── 6. 从 DB 读回验证 ──────────────────────────────────────────
print(f"\n{'='*50}")
print(f"数据库回读验证:")

db_total = cur.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
db_revenue = cur.execute("SELECT SUM(amount) FROM sales").fetchone()[0]
db_orders = cur.execute("SELECT COUNT(DISTINCT order_id) FROM sales").fetchone()[0]
db_avg = cur.execute("SELECT AVG(amount) FROM sales").fetchone()[0]

print(f"  DB 总行数:       {db_total}  (清洗: {total_rows})")
print(f"  DB 总营业额:     {db_revenue:.2f}  (清洗: {total_revenue:.2f})")
print(f"  DB 唯一订单数:   {db_orders}  (清洗: {total_orders})")
print(f"  DB 行均金额:     {db_avg:.2f}  (清洗: {avg_per_row:.2f})")

assert db_total == total_rows, "行数不一致!"
assert abs(db_revenue - total_revenue) < 0.01, "营业额不一致!"
assert db_orders == total_orders, "订单数不一致!"

print(f"\n[OK] 核对通过！数据库已写入: {DB_PATH}")
conn.close()
