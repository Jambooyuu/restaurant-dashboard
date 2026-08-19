import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

export default function RevenueChart({ data }) {
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

    const dates = data.map(d => d.date)
    const revenues = data.map(d => d.revenue)
    const orders = data.map(d => d.order_count)
    const avgValues = data.map(d => d.avg_order_value)

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(255,255,255,0.95)',
        borderColor: '#e2e8f0',
        textStyle: { color: '#1e293b', fontSize: 13 },
        formatter(params) {
          const date = params[0].axisValue
          let html = `<div style="font-weight:600;margin-bottom:4px">${date}</div>`
          params.forEach(p => {
            const dot = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:6px"></span>`
            let val = p.value
            if (p.seriesName === '营业额') val = '¥' + val.toLocaleString()
            else if (p.seriesName === '客单价') val = '¥' + val.toFixed(2)
            html += `<div>${dot}${p.seriesName}: <b>${val}</b></div>`
          })
          return html
        }
      },
      legend: {
        data: ['营业额', '订单数', '客单价'],
        top: 0,
        right: 0,
        textStyle: { fontSize: 12, color: '#64748b' }
      },
      grid: { left: 60, right: 60, top: 40, bottom: 30 },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: {
          formatter: v => v.slice(5), // MM-DD
          color: '#64748b',
          fontSize: 11,
        },
        axisLine: { lineStyle: { color: '#e2e8f0' } },
      },
      yAxis: [
        {
          type: 'value',
          name: '营业额 (¥)',
          axisLabel: {
            formatter: v => v >= 10000 ? (v/10000).toFixed(1) + 'w' : v,
            color: '#64748b',
            fontSize: 11,
          },
          splitLine: { lineStyle: { color: '#f1f5f9' } },
          nameTextStyle: { color: '#94a3b8', fontSize: 11 },
        },
        {
          type: 'value',
          name: '订单数',
          axisLabel: { color: '#64748b', fontSize: 11 },
          splitLine: { show: false },
          nameTextStyle: { color: '#94a3b8', fontSize: 11 },
        }
      ],
      series: [
        {
          name: '营业额',
          type: 'line',
          data: revenues,
          smooth: true,
          symbol: 'circle',
          symbolSize: 4,
          lineStyle: { width: 2.5, color: '#4f46e5' },
          itemStyle: { color: '#4f46e5' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(79,70,229,0.15)' },
              { offset: 1, color: 'rgba(79,70,229,0.02)' },
            ])
          },
        },
        {
          name: '订单数',
          type: 'bar',
          yAxisIndex: 1,
          data: orders,
          barWidth: '40%',
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(16,185,129,0.6)' },
              { offset: 1, color: 'rgba(16,185,129,0.15)' },
            ]),
            borderRadius: [4, 4, 0, 0],
          },
        },
        {
          name: '客单价',
          type: 'line',
          data: avgValues,
          smooth: true,
          symbol: 'diamond',
          symbolSize: 5,
          lineStyle: { width: 1.5, color: '#f59e0b', type: 'dashed' },
          itemStyle: { color: '#f59e0b' },
        }
      ],
      dataZoom: [
        {
          type: 'inside',
          start: 0,
          end: 100,
        }
      ],
    }, true)

    const handleResize = () => chart.resize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [data])

  return <div ref={chartRef} style={{ width: '100%', height: 350 }} />
}
