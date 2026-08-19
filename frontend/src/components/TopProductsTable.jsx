export default function TopProductsTable({ data }) {
  if (!data || data.length === 0) {
    return <div style={{ padding: 20, color: '#94a3b8', textAlign: 'center' }}>暂无数据</div>
  }

  return (
    <table>
      <thead>
        <tr>
          <th style={{ width: 40 }}>#</th>
          <th>商品</th>
          <th>品类</th>
          <th style={{ textAlign: 'right' }}>销量</th>
          <th style={{ textAlign: 'right' }}>营业额</th>
        </tr>
      </thead>
      <tbody>
        {data.map((item, i) => (
          <tr key={item.product_id}>
            <td>
              <span className={`rank-badge ${i < 3 ? `rank-${i+1}` : 'rank-other'}`}>
                {i + 1}
              </span>
            </td>
            <td style={{ fontWeight: 500 }}>{item.product_name}</td>
            <td>
              <span style={{
                padding: '2px 8px',
                borderRadius: 4,
                fontSize: 12,
                background: '#f1f5f9',
                color: '#64748b',
              }}>
                {item.product_category}
              </span>
            </td>
            <td style={{ textAlign: 'right' }}>{item.total_qty}</td>
            <td style={{ textAlign: 'right', fontWeight: 600 }}>
              ¥{item.total_revenue.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
