import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

export default function StoreComparison({ data }) {
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

    const colors = ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(255,255,255,0.95)',
        borderColor: '#e2e8f0',
        textStyle: { color: '#1e293b', fontSize: 13 },
        axisPointer: { type: 'shadow' },
        formatter(params) {
          const d = data.find(s => s.store_name === params[0].name)
          if (!d) return ''
          return `<b>${d.store_name}</b><br/>
            ${d.district} · ${d.category}<br/>
            营业额: <b>¥${d.total_revenue.toLocaleString()}</b><br/>
            订单数: ${d.order_count}<br/>
            客单价: ¥${d.avg_order_value.toFixed(2)}`
        }
      },
      grid: { left: 100, right: 30, top: 10, bottom: 20 },
      xAxis: {
        type: 'value',
        axisLabel: {
          formatter: v => v >= 10000 ? (v/10000).toFixed(1) + '万' : v,
          color: '#64748b',
          fontSize: 11,
        },
        splitLine: { lineStyle: { color: '#f1f5f9' } },
      },
      yAxis: {
        type: 'category',
        data: data.map(d => d.store_name).reverse(),
        axisLabel: { color: '#1e293b', fontSize: 12, fontWeight: 500 },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      series: [{
        type: 'bar',
        data: data.map((d, i) => ({
          value: d.total_revenue,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: colors[i % colors.length] },
              { offset: 1, color: colors[i % colors.length] + '80' },
            ]),
            borderRadius: [0, 6, 6, 0],
          }
        })).reverse(),
        barWidth: '50%',
        label: {
          show: true,
          position: 'right',
          formatter: p => '¥' + p.value.toLocaleString(),
          fontSize: 11,
          color: '#64748b',
        }
      }]
    }, true)

    const handleResize = () => chart.resize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [data])

  return <div ref={chartRef} style={{ width: '100%', height: 260 }} />
}
