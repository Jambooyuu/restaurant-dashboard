import { useState, useRef, useEffect } from 'react'

const QUICK_QUESTIONS = [
  '七月总营业额多少？',
  '哪个门店营业额最高？',
  '哪个品类卖得最好？',
  '客单价最近是涨了还是跌了？',
  '牛肉poke六月卖了多少钱？',
]

export default function ChatPanel() {
  const [messages, setMessages] = useState([
    { role: 'system', content: '你好！我是餐饮数据分析助手，可以回答你关于销售数据的任何问题。试试下面的快捷问题，或者直接输入你的问题。' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text) => {
    const msg = text || input.trim()
    if (!msg || loading) return

    setInput('')
    const userMsg = { role: 'user', content: msg }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      // 构建 history（不含 system 消息和最后的 user 消息）
      const history = messages
        .filter(m => m.role === 'user' || m.role === 'assistant')
        .map(m => ({ role: m.role, content: m.content }))

      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, history }),
      })

      const data = await resp.json()

      const assistantMsg = {
        role: 'assistant',
        content: data.answer,
        data: data.data,
        toolCalls: data.tool_calls,
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `请求失败：${err.message}。请确认后端服务已启动。`,
      }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">
        🤖 AI 数据问答
        <span style={{ fontSize: 12, color: '#94a3b8', fontWeight: 400, marginLeft: 8 }}>
          所有数字来自数据库真实查询
        </span>
      </div>

      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            {msg.content}
            {msg.data && msg.data.length > 0 && (
              <div className="message-data">
                📊 查询结果 ({msg.data.length} 条):<br />
                {msg.data.slice(0, 10).map((d, j) => (
                  <div key={j}>
                    {Object.entries(d).map(([k, v]) => `${k}: ${v}`).join(' | ')}
                  </div>
                ))}
                {msg.data.length > 10 && <div>... 共 {msg.data.length} 条</div>}
              </div>
            )}
            {msg.toolCalls && msg.toolCalls.length > 0 && (
              <div className="message-data" style={{ marginTop: 4 }}>
                🔧 调用了: {msg.toolCalls.map(tc =>
                  `${tc.function}(${Object.entries(tc.arguments).map(([k,v]) => `${k}=${v}`).join(', ')})`
                ).join(' → ')}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <div className="loading">
              <div className="spinner" /> 正在查询数据库并生成回答…
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="quick-questions">
        {QUICK_QUESTIONS.map((q, i) => (
          <button key={i} className="quick-q" onClick={() => sendMessage(q)}>
            {q}
          </button>
        ))}
      </div>

      <div className="chat-input-area">
        <input
          ref={inputRef}
          className="chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入你的数据问题，例如：七月份哪个门店业绩最好？"
          disabled={loading}
        />
        <button
          className="chat-send-btn"
          onClick={() => sendMessage()}
          disabled={loading || !input.trim()}
        >
          发送
        </button>
      </div>
    </div>
  )
}
