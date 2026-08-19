import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

/**
 * 门店雷达图 — 多维度对比（营业额/订单数/客单价/日均）
 * 第三关创新功能：一眼看出各门店的优势和短板
 */
export default function StoreRadar({ data, startDate, endDate }) {
  const chartRef = useRef(null)
  const instanceRef = useRef(null)

  useEffect(() => {
    if (!chartRef.current) return
    if (!instanceRef.current) {
      instanceRef.current = echarts.init(chartRef.current)
    }
    const chart = instanceRef.current

    if (!data || data.length === 0) {
      chart.clear()
      return
    }

    // 计算天数
    const start = new Date(startDate)
    const end = new Date(endDate)
    const days = Math.max(1, Math.ceil((end - start) / 86400000) + 1)

    // 归一化各维度到 0-100
    const maxRevenue = Math.max(...data.map(d => d.total_revenue))
    const maxOrders = Math.max(...data.map(d => d.order_count))
    const maxAvg = Math.max(...data.map(d => d.avg_order_value))
    const maxDailyAvg = Math.max(...data.map(d => d.total_revenue / days))

    const colors = ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

    chart.setOption({
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(255,255,255,0.95)',
        borderColor: '#e2e8f0',
        textStyle: { color: '#1e293b', fontSize: 13 },
      },
      legend: {
        data: data.map(d => d.store_name),
        bottom: 0,
        textStyle: { fontSize: 11, color: '#64748b' },
      },
      radar: {
        indicator: [
          { name: '营业额', max: 100 },
          { name: '订单数', max: 100 },
          { name: '客单价', max: 100 },
          { name: '日均营收', max: 100 },
        ],
        shape: 'polygon',
        splitNumber: 4,
        axisName: { color: '#64748b', fontSize: 11 },
        splitLine: { lineStyle: { color: '#f1f5f9' } },
        splitArea: { show: false },
        axisLine: { lineStyle: { color: '#e2e8f0' } },
      },
      series: [{
        type: 'radar',
        data: data.map((d, i) => ({
          name: d.store_name,
          value: [
            Math.round((d.total_revenue / maxRevenue) * 100),
            Math.round((d.order_count / maxOrders) * 100),
            Math.round((d.avg_order_value / maxAvg) * 100),
            Math.round(((d.total_revenue / days) / maxDailyAvg) * 100),
          ],
          lineStyle: { color: colors[i], width: 2 },
          itemStyle: { color: colors[i] },
          areaStyle: { color: colors[i] + '20' },
        })),
      }]
    }, true)

    const handleResize = () => chart.resize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [data, startDate, endDate])

  return <div ref={chartRef} style={{ width: '100%', height: 320 }} />
}
