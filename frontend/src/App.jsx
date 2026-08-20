import { useState, useEffect, useCallback } from 'react'
import RevenueChart from './components/RevenueChart'
import TopProductsTable from './components/TopProductsTable'
import StoreComparison from './components/StoreComparison'
import CategoryPie from './components/CategoryPie'
import PaymentPie from './components/PaymentPie'
import StoreRadar from './components/StoreRadar'
import ChatPanel from './components/ChatPanel'

const API = '/api'

function fmtMoney(n) {
  if (n >= 10000) return (n / 10000).toFixed(2) + ' 万'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ── KPI Card ──
function KPICard({ label, value, icon }) {
  return (
    <div className="kpi-card">
      <div className="kpi-header">
        <span className="kpi-label">{label}</span>
        <span className="kpi-icon">{icon}</span>
      </div>
      <div className="kpi-value">{value}</div>
    </div>
  )
}

// ── Section Card ──
function Section({ title, subtitle, children, fullWidth }) {
  return (
    <div className="section-card" style={fullWidth ? { gridColumn: '1 / -1' } : undefined}>
      <div className="section-header">
        <div>
          <div className="section-title">{title}</div>
          {subtitle && <div className="section-subtitle">{subtitle}</div>}
        </div>
      </div>
      <div className="section-body">{children}</div>
    </div>
  )
}

export default function App() {
  const [startDate, setStartDate] = useState('2026-05-01')
  const [endDate, setEndDate] = useState('2026-07-31')
  const [storeFilter, setStoreFilter] = useState('')
  const [stores, setStores] = useState([])
  const [dash, setDash] = useState(null)
  const [storeComp, setStoreComp] = useState([])
  const [catPerf, setCatPerf] = useState([])
  const [payData, setPayData] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => { fetch(`${API}/stores`).then(r => r.json()).then(setStores) }, [])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const p = new URLSearchParams({ start_date: startDate, end_date: endDate })
      if (storeFilter) p.set('store_id', storeFilter)
      const [d, s, c, pay] = await Promise.all([
        fetch(`${API}/dashboard?${p}`).then(r => r.json()),
        fetch(`${API}/store-comparison?start_date=${startDate}&end_date=${endDate}`).then(r => r.json()),
        fetch(`${API}/category-performance?start_date=${startDate}&end_date=${endDate}`).then(r => r.json()),
        fetch(`${API}/payment-breakdown?start_date=${startDate}&end_date=${endDate}`).then(r => r.json()),
      ])
      setDash(d); setStoreComp(s); setCatPerf(c); setPayData(pay)
    } finally { setLoading(false) }
  }, [startDate, endDate, storeFilter])

  useEffect(() => { load() }, [load])

  const sum = dash?.summary || {}
  const dailyCount = dash?.daily_stats?.length || 1

  return (
    <div className="shell">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="sidebar-logo"><span>🍜</span> 餐饮数据</div>

        <div className="sidebar-section">
          <div className="sidebar-label">概览</div>
          <button className="nav-item active">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
            数据看板
          </button>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-label">门店</div>
          {stores.map(s => (
            <button key={s.store_id} className={`nav-item ${storeFilter === s.store_id ? 'active' : ''}`}
              onClick={() => setStoreFilter(storeFilter === s.store_id ? '' : s.store_id)}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/></svg>
              {s.store_name}
              <span className="nav-badge">{s.store_id}</span>
            </button>
          ))}
        </div>

        <div className="sidebar-section" style={{ marginTop: 'auto', paddingTop: 8, borderTop: '1px solid var(--border)' }}>
          <button className="nav-item" onClick={() => { setStoreFilter(''); setStartDate('2026-05-01'); setEndDate('2026-07-31') }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
            重置筛选
          </button>
        </div>
      </aside>

      {/* ── Main ── */}
      <div className="main-area">
        {/* Topbar */}
        <header className="topbar">
          <div className="breadcrumb">
            <span className="par">餐饮数据</span>
            <span className="sep">/</span>
            <span className="cur">数据看板</span>
          </div>
          <div className="topbar-spacer" />
          {loading && <div className="loading"><div className="spinner" /> 加载中</div>}
          <div className="topbar-avatar">YN</div>
        </header>

        {/* Content */}
        <div className="content">
          {/* Filters */}
          <div style={{ display: 'flex', gap: 12, marginBottom: 24, alignItems: 'center' }}>
            <label style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 500 }}>日期</label>
            <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)}
              style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 6, height: 32, padding: '0 10px', fontSize: 13, color: 'var(--fg)', outline: 'none' }} />
            <span style={{ color: 'var(--subtle)', fontSize: 12 }}>至</span>
            <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)}
              style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 6, height: 32, padding: '0 10px', fontSize: 13, color: 'var(--fg)', outline: 'none' }} />
            <button className="send-btn" onClick={load} style={{ height: 32, padding: '0 16px' }}>查询</button>
            <div style={{ flex: 1 }} />
            {['7月', '6月', '5月'].map(m => {
              const mm = { '5月': '05', '6月': '06', '7月': '07' }[m]
              return (
                <button key={m} className="quick-btn" onClick={() => { setStartDate(`2026-${mm}-01`); setEndDate(`2026-${mm}-31`) }}>{m}</button>
              )
            })}
          </div>

          {/* KPI Row */}
          <div className="kpi-grid">
            <KPICard label="总营业额" value={`¥${fmtMoney(sum.total_revenue || 0)}`}
              icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 6v12M8 10h8M8 14h8"/></svg>} />
            <KPICard label="订单总数" value={`${(sum.total_orders || 0).toLocaleString()}`}
              icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/></svg>} />
            <KPICard label="客单价" value={`¥${(sum.avg_order_value || 0).toFixed(2)}`}
              icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 100 7h5a3.5 3.5 0 010 7H6"/></svg>} />
            <KPICard label="日均营业额" value={`¥${fmtMoney((sum.total_revenue || 0) / dailyCount)}`}
              icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/></svg>} />
          </div>

          {/* Revenue Trend (full width) */}
          <Section title="📈 每日营业额趋势" subtitle={`${startDate} 至 ${endDate}`} fullWidth>
            <RevenueChart data={dash?.daily_stats || []} />
          </Section>

          {/* Two columns */}
          <div className="grid-2">
            <Section title="🏪 门店营业额对比">
              <StoreComparison data={storeComp} />
            </Section>
            <Section title="🍱 品类销售分布">
              <CategoryPie data={catPerf} />
            </Section>
          </div>

          <div className="grid-2">
            <Section title="🏆 Top 10 商品">
              <TopProductsTable data={dash?.top_products || []} />
            </Section>
            <Section title="💳 支付方式分布">
              <PaymentPie data={payData} />
            </Section>
          </div>

          {/* Radar + AI Chat side by side */}
          <div className="grid-2">
            <Section title="🎯 门店多维度雷达对比" subtitle="营业额 · 订单数 · 客单价 · 日均营收">
              <StoreRadar data={storeComp} startDate={startDate} endDate={endDate} />
            </Section>
            <ChatPanel />
          </div>
        </div>
      </div>
    </div>
  )
}
