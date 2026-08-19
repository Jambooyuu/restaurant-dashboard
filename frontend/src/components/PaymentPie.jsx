import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

export default function PaymentPie({ data }) {
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

    const colors = {
      '微信': '#07c160',
      '支付宝': '#1677ff',
      '现金': '#f59e0b',
      '银行卡': '#8b5cf6',
      '会员储值': '#ef4444',
    }

    chart.setOption({
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(255,255,255,0.95)',
        borderColor: '#e2e8f0',
        textStyle: { color: '#1e293b' },
        formatter: p => `<b>${p.name}</b><br/>
          订单数: ${p.data.count}<br/>
          营业额: ¥${p.value.toLocaleString()}<br/>
          占比: ${p.percent}%`
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'center',
        textStyle: { fontSize: 12, color: '#64748b' },
      },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 14, fontWeight: 'bold' },
        },
        data: data.map(d => ({
          name: d.payment,
          value: d.total,
          count: d.count,
          itemStyle: { color: colors[d.payment] || '#94a3b8' },
        }))
      }]
    }, true)

    const handleResize = () => chart.resize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [data])

  return <div ref={chartRef} style={{ width: '100%', height: 260 }} />
}
