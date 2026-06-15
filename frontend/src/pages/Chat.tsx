import { useState, useRef, useEffect, useCallback } from 'react'
import { createChatSocket } from '../services/api'

interface Message {
  role: 'user' | 'agent'
  content: string
}

export default function Chat() {
  const [userId, setUserId] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const connect = useCallback(() => {
    if (!userId) return
    const ws = createChatSocket()
    ws.onopen = () => setConnected(true)
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      setMessages(prev => [...prev, { role: 'agent', content: data.response }])
    }
    ws.onclose = () => setConnected(false)
    wsRef.current = ws
  }, [userId])

  const sendMessage = () => {
    if (!input.trim() || !wsRef.current) return
    wsRef.current.send(JSON.stringify({ user_id: userId, message: input }))
    setMessages(prev => [...prev, { role: 'user', content: input }])
    setInput('')
  }

  return (
    <div className="space-y-4 max-w-3xl">
      <h2 className="text-2xl font-semibold">Chat with Your Financial Agent</h2>
      <div className="flex gap-3 items-end">
        <div>
          <label className="block text-sm text-gray-400 mb-1">User ID</label>
          <input
            className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm w-64"
            value={userId}
            onChange={e => setUserId(e.target.value)}
            placeholder="Enter your user ID"
          />
        </div>
        <button
          onClick={connect}
          disabled={!userId || connected}
          className={`px-4 py-2 rounded text-sm font-medium ${
            connected ? 'bg-green-700' : 'bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50'
          }`}
        >
          {connected ? 'Connected' : 'Connect'}
        </button>
      </div>
      <div className="bg-gray-800 border border-gray-700 rounded-lg h-96 overflow-y-auto p-4 space-y-3">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-md rounded-lg px-3 py-2 text-sm ${
                msg.role === 'user'
                  ? 'bg-emerald-700 text-white'
                  : 'bg-gray-700 text-gray-100'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="flex gap-2">
        <input
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm flex-1"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendMessage()}
          placeholder="Ask about your finances..."
          disabled={!connected}
        />
        <button
          onClick={sendMessage}
          disabled={!connected || !input.trim()}
          className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium"
        >
          Send
        </button>
      </div>
    </div>
  )
}
