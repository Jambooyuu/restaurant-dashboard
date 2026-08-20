import { useState, useEffect, useCallback, useRef } from 'react'
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

// ── KPI Card (Stripe style: icon left + value + delta) ──
function KPICard({ label, value, delta, deltaType, icon, color }) {
  return (
    <div className="kpi-card">
      <div className="kpi-header">
        <span className="kpi-label">{label}</span>
        <div className="kpi-icon-wrap" style={{ background: color + '12', color }}>
          {icon}
        </div>
      </div>
      <div className="kpi-value">{value}</div>
      {delta && (
        <div className={`kpi-delta ${deltaType}`}>
          {deltaType === 'up' ? '↑' : deltaType === 'down' ? '↓' : '→'} {delta}
          <span className="vs">vs 上月</span>
        </div>
      )}
    </div>
  )
}

// ── Section Card ──
function Section({ title, subtitle, children, className, action }) {
  return (
    <div className={`section-card ${className || ''}`}>
      <div className="section-header">
        <div>
          <div className="section-title">{title}</div>
          {subtitle && <div className="section-subtitle">{subtitle}</div>}
        </div>
        {action}
      </div>
      <div className="section-body">{children}</div>
    </div>
  )
}

// ── Filter Bar ──
function FilterBar({ startDate, endDate, setStartDate, setEndDate, onQuery }) {
  return (
    <div className="filter-bar">
      <div className="filter-group">
        <label>开始</label>
        <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />
      </div>
      <div className="filter-group">
        <label>结束</label>
        <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} />
      </div>
      <button className="filter-btn" onClick={onQuery}>查询</button>
      <div className="filter-sep" />
      {['5月', '6月', '7月'].map(m => {
        const mm = { '5月': '05', '6月': '06', '7月': '07' }[m]
        return (
          <button key={m} className="filter-chip"
            onClick={() => { setStartDate(`2026-${mm}-01`); setEndDate(`2026-${mm}-31`) }}>
            {m}
          </button>
        )
      })}
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
  const contentRef = useRef(null)

  const scrollTop = () => contentRef.current?.scrollTo({ top: 0, behavior: 'smooth' })
  const scrollToAi = () => document.getElementById('ai-section')?.scrollIntoView({ behavior: 'smooth' })

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
          <button className="nav-item active" onClick={scrollTop}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
            数据看板
          </button>
          <button className="nav-item" onClick={scrollToAi}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
            AI 问答
          </button>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-label">门店</div>
          <button className={`nav-item ${!storeFilter ? 'active' : ''}`}
            onClick={() => { setStoreFilter(''); scrollTop() }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/></svg>
            全部门店
          </button>
          {stores.map(s => (
            <button key={s.store_id} className={`nav-item ${storeFilter === s.store_id ? 'active' : ''}`}
              onClick={() => { setStoreFilter(storeFilter === s.store_id ? '' : s.store_id); scrollTop() }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/></svg>
              {s.store_name}
              <span className="nav-badge">{s.district?.split('·')[1] || s.store_id}</span>
            </button>
          ))}
        </div>

        <div className="sidebar-footer">
          <button className="nav-item" onClick={() => { setStoreFilter(''); setStartDate('2026-05-01'); setEndDate('2026-07-31'); scrollTop() }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M3 12a9 9 0 109-9"/><polyline points="3 3 3 9 9 9"/></svg>
            重置筛选
          </button>
        </div>
      </aside>

      {/* ── Main ── */}
      <div className="main-area">
        <header className="topbar">
          <div className="breadcrumb">
            <span className="par">连锁餐饮</span>
            <span className="sep">/</span>
            <span className="cur">经营数据看板</span>
          </div>
          <div className="topbar-spacer" />
          {loading && <div className="loading"><div className="spinner" /></div>}
          <FilterBar {...{ startDate, endDate, setStartDate, setEndDate, onQuery: load }} />
          <div className="topbar-avatar">JD</div>
        </header>

        <div className="content" ref={contentRef}>
          {/* ── KPI Row ── */}
          <div className="kpi-grid">
            <KPICard label="总营业额" value={`¥${fmtMoney(sum.total_revenue || 0)}`}
              delta="12.4%" deltaType="up" color="var(--accent)"
              icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 6v12M8 10h8M8 14h8"/></svg>} />
            <KPICard label="订单总数" value={`${(sum.total_orders || 0).toLocaleString()}`}
              delta="8.2%" deltaType="up" color="var(--green)"
              icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/></svg>} />
            <KPICard label="客单价" value={`¥${(sum.avg_order_value || 0).toFixed(2)}`}
              delta="3.1%" deltaType="up" color="var(--amber)"
              icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 100 7h5a3.5 3.5 0 010 7H6"/></svg>} />
            <KPICard label="日均营业额" value={`¥${fmtMoney((sum.total_revenue || 0) / dailyCount)}`}
              delta="0.8%" deltaType="neutral" color="var(--red)"
              icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/></svg>} />
          </div>

          {/* ── 主趋势图 + 门店对比（2:1） ── */}
          <div className="grid-main">
            <Section title="营业额趋势" subtitle={`${startDate} 至 ${endDate}`} className="span-2">
              <RevenueChart data={dash?.daily_stats || []} />
            </Section>
            <Section title="门店排名">
              <StoreComparison data={storeComp} />
            </Section>
          </div>

          {/* ── 中层：品类 + 支付 + Top10（三栏） ── */}
          <div className="grid-3">
            <Section title="品类分布">
              <CategoryPie data={catPerf} />
            </Section>
            <Section title="支付方式">
              <PaymentPie data={payData} />
            </Section>
            <Section title="Top 10 商品">
              <TopProductsTable data={dash?.top_products || []} />
            </Section>
          </div>

          {/* ── 雷达图 ── */}
          <Section title="门店多维度对比" subtitle="营业额 · 订单数 · 客单价 · 日均营收">
            <StoreRadar data={storeComp} startDate={startDate} endDate={endDate} />
          </Section>

          {/* ── AI 问答（全宽独立区域） ── */}
          <div id="ai-section">
            <ChatPanel />
          </div>
        </div>
      </div>
    </div>
  )
}
