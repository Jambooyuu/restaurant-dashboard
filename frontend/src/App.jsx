import { useState, useEffect, useCallback } from 'react'
import dayjs from 'dayjs'
import RevenueChart from './components/RevenueChart'
import TopProductsTable from './components/TopProductsTable'
import StoreComparison from './components/StoreComparison'
import CategoryPie from './components/CategoryPie'
import PaymentPie from './components/PaymentPie'
import StoreRadar from './components/StoreRadar'
import ChatPanel from './components/ChatPanel'

const API_BASE = '/api'

function fmtMoney(n) {
  if (n >= 10000) return (n / 10000).toFixed(2) + ' 万'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function App() {
  // ── 日期默认值：整个数据范围 ──
  const [startDate, setStartDate] = useState('2026-05-01')
  const [endDate, setEndDate] = useState('2026-07-31')
  const [storeFilter, setStoreFilter] = useState('')
  const [stores, setStores] = useState([])

  // ── 数据状态 ──
  const [dashboard, setDashboard] = useState(null)
  const [storeComp, setStoreComp] = useState([])
  const [categoryPerf, setCategoryPerf] = useState([])
  const [paymentData, setPaymentData] = useState([])
  const [loading, setLoading] = useState(false)

  // ── 加载门店列表 ──
  useEffect(() => {
    fetch(`${API_BASE}/stores`).then(r => r.json()).then(setStores)
  }, [])

  // ── 加载数据 ──
  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ start_date: startDate, end_date: endDate })
      if (storeFilter) params.set('store_id', storeFilter)

      const [dashRes, storeRes, catRes, payRes] = await Promise.all([
        fetch(`${API_BASE}/dashboard?${params}`).then(r => r.json()),
        fetch(`${API_BASE}/store-comparison?start_date=${startDate}&end_date=${endDate}`).then(r => r.json()),
        fetch(`${API_BASE}/category-performance?start_date=${startDate}&end_date=${endDate}`).then(r => r.json()),
        fetch(`${API_BASE}/payment-breakdown?start_date=${startDate}&end_date=${endDate}`).then(r => r.json()),
      ])

      setDashboard(dashRes)
      setStoreComp(storeRes)
      setCategoryPerf(catRes)
      setPaymentData(payRes)
    } catch (err) {
      console.error('Failed to load data:', err)
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, storeFilter])

  useEffect(() => { loadData() }, [loadData])

  // ── 快捷日期选择 ──
  const setQuickRange = (start, end) => {
    setStartDate(start)
    setEndDate(end)
  }

  const summary = dashboard?.summary || {}

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="header">
        <h1><span>🍜</span> 连锁餐饮数据分析看板</h1>
        <div className="header-actions">
          {loading && <div className="loading"><div className="spinner" /> 加载中…</div>}
        </div>
      </header>

      <main className="main">
        {/* ── 筛选栏 ── */}
        <div className="filters">
          <div className="filter-group">
            <label>开始日期</label>
            <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />
          </div>
          <div className="filter-group">
            <label>结束日期</label>
            <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} />
          </div>
          <div className="filter-group">
            <label>门店</label>
            <select value={storeFilter} onChange={e => setStoreFilter(e.target.value)}>
              <option value="">全部门店</option>
              {stores.map(s => (
                <option key={s.store_id} value={s.store_id}>
                  {s.store_name} ({s.district})
                </option>
              ))}
            </select>
          </div>
          <button className="btn btn-primary" onClick={loadData}>查询</button>
          <button className="btn btn-outline" onClick={() => setQuickRange('2026-07-01', '2026-07-31')}>7月</button>
          <button className="btn btn-outline" onClick={() => setQuickRange('2026-06-01', '2026-06-30')}>6月</button>
          <button className="btn btn-outline" onClick={() => setQuickRange('2026-05-01', '2026-05-31')}>5月</button>
        </div>

        {/* ── KPI 卡片 ── */}
        <div className="kpi-row">
          <div className="kpi-card">
            <div className="kpi-label">总营业额</div>
            <div className="kpi-value">¥{fmtMoney(summary.total_revenue || 0)}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">订单总数</div>
            <div className="kpi-value">{(summary.total_orders || 0).toLocaleString()}<span className="kpi-unit">单</span></div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">客单价</div>
            <div className="kpi-value">¥{(summary.avg_order_value || 0).toFixed(2)}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">日均营业额</div>
            <div className="kpi-value">
              ¥{dashboard?.daily_stats?.length
                ? (summary.total_revenue / dashboard.daily_stats.length).toFixed(2)
                : '0.00'}
            </div>
          </div>
        </div>

        {/* ── 营业额趋势（全宽） ── */}
        <div className="charts-grid">
          <div className="chart-card full-width">
            <div className="chart-title">📈 每日营业额趋势</div>
            <RevenueChart data={dashboard?.daily_stats || []} />
          </div>
        </div>

        {/* ── 双栏图表 ── */}
        <div className="charts-grid">
          <div className="chart-card">
            <div className="chart-title">🏪 门店营业额对比</div>
            <StoreComparison data={storeComp} />
          </div>
          <div className="chart-card">
            <div className="chart-title">🍱 品类销售分布</div>
            <CategoryPie data={categoryPerf} />
          </div>
        </div>

        {/* ── Top 10 商品 + 支付方式 ── */}
        <div className="charts-grid">
          <div className="chart-card">
            <div className="chart-title">🏆 Top 10 商品（按营业额）</div>
            <TopProductsTable data={dashboard?.top_products || []} />
          </div>
          <div className="chart-card">
            <div className="chart-title">💳 支付方式分布</div>
            <PaymentPie data={paymentData} />
          </div>
        </div>

        {/* ── 门店雷达图（第三关创新） ── */}
        <div className="charts-grid">
          <div className="chart-card full-width">
            <div className="chart-title">🎯 门店多维度雷达对比</div>
            <p style={{ fontSize: 12, color: '#94a3b8', marginBottom: 12 }}>
              从营业额、订单数、客单价、日均营收四个维度对比各门店综合实力
            </p>
            <StoreRadar data={storeComp} startDate={startDate} endDate={endDate} />
          </div>
        </div>

        {/* ── AI 对话 ── */}
        <ChatPanel />
      </main>
    </div>
  )
}
