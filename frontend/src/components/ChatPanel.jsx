import { useState, useRef, useEffect, useCallback } from 'react'

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

  const sendMessage = useCallback(async (text) => {
    const msg = text || input.trim()
    if (!msg || loading) return

    setInput('')
    const userMsg = { role: 'user', content: msg }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const history = messages
        .filter(m => m.role === 'user' || m.role === 'assistant')
        .map(m => ({ role: m.role, content: m.content }))

      // 尝试 SSE 流式
      const resp = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, history }),
      })

      if (!resp.ok || !resp.body) {
        // fallback 到非流式
        const resp2 = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: msg, history }),
        })
        const data = await resp2.json()
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.answer,
          data: data.data,
          toolCalls: data.tool_calls,
        }])
        return
      }

      // SSE 流式处理
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let streamingContent = ''
      let streamToolCalls = []
      let streamData = []
      let msgIndex = -1

      // 先插入一个空的 assistant 消息用于流式更新
      setMessages(prev => {
        msgIndex = prev.length
        return [...prev, { role: 'assistant', content: '', streaming: true }]
      })

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const dataStr = line.slice(6).trim()
          if (dataStr === '[DONE]') continue

          try {
            const event = JSON.parse(dataStr)

            if (event.type === 'tool_call') {
              streamToolCalls.push(event)
              // 更新消息显示查询状态
              setMessages(prev => {
                const updated = [...prev]
                updated[msgIndex] = {
                  ...updated[msgIndex],
                  content: streamingContent || `正在查询: ${event.function}...`,
                  toolCalls: [...streamToolCalls],
                }
                return updated
              })
            } else if (event.type === 'tool_result') {
              // 查询完成
            } else if (event.type === 'token') {
              streamingContent += event.content
              setMessages(prev => {
                const updated = [...prev]
                updated[msgIndex] = {
                  ...updated[msgIndex],
                  content: streamingContent,
                  toolCalls: [...streamToolCalls],
                  streaming: true,
                }
                return updated
              })
            } else if (event.type === 'done') {
              streamingContent = event.answer || streamingContent
              streamData = event.data || []
              streamToolCalls = event.tool_calls || streamToolCalls
              setMessages(prev => {
                const updated = [...prev]
                updated[msgIndex] = {
                  ...updated[msgIndex],
                  content: streamingContent,
                  data: streamData,
                  toolCalls: streamToolCalls,
                  streaming: false,
                }
                return updated
              })
            } else if (event.type === 'error') {
              setMessages(prev => {
                const updated = [...prev]
                updated[msgIndex] = {
                  ...updated[msgIndex],
                  content: event.message,
                  streaming: false,
                }
                return updated
              })
            }
          } catch (e) {
            // ignore parse errors
          }
        }
      }

      // 确保最终状态正确
      setMessages(prev => {
        const updated = [...prev]
        if (updated[msgIndex]) {
          updated[msgIndex] = {
            ...updated[msgIndex],
            content: streamingContent || updated[msgIndex].content,
            data: streamData.length > 0 ? streamData : updated[msgIndex].data,
            toolCalls: streamToolCalls.length > 0 ? streamToolCalls : updated[msgIndex].toolCalls,
            streaming: false,
          }
        }
        return updated
      })

    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `请求失败：${err.message}。请确认后端服务已启动。`,
      }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }, [input, loading, messages])

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
          所有数字来自数据库真实查询 · 支持流式输出
        </span>
      </div>

      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            {msg.content}
            {msg.streaming && <span className="streaming-cursor">▊</span>}
            {msg.data && msg.data.length > 0 && !msg.streaming && (
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
            {msg.toolCalls && msg.toolCalls.length > 0 && !msg.streaming && (
              <div className="message-data" style={{ marginTop: 4 }}>
                🔧 调用了: {msg.toolCalls.map((tc, idx) =>
                  `${tc.function}(${Object.entries(tc.arguments || {}).map(([k,v]) => `${k}=${v}`).join(', ')})`
                ).join(' → ')}
              </div>
            )}
          </div>
        ))}
        {loading && !messages[messages.length - 1]?.streaming && (
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
