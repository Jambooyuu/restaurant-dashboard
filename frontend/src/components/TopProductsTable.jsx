export default function TopProductsTable({ data }) {
  if (!data || data.length === 0) {
    return <div style={{ padding: 40, color: 'var(--subtle)', textAlign: 'center', fontSize: 13 }}>暂无数据</div>
  }

  return (
    <table className="data-table">
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
              <span className={`rank ${i === 0 ? 'rank-1' : i === 1 ? 'rank-2' : i === 2 ? 'rank-3' : 'rank-n'}`}>
                {i + 1}
              </span>
            </td>
            <td style={{ fontWeight: 500 }}>{item.product_name}</td>
            <td><span className="tag">{item.product_category}</span></td>
            <td style={{ textAlign: 'right' }}>{item.total_qty}</td>
            <td style={{ textAlign: 'right', fontWeight: 500 }}>
              ¥{item.total_revenue.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
