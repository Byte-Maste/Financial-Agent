import { useState } from 'react'
import { getAdvice } from '../services/api'

export default function Dashboard() {
  const [userId, setUserId] = useState('')
  const [advice, setAdvice] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleGetAdvice = async () => {
    if (!userId) return
    setLoading(true)
    const res = await getAdvice(userId)
    const msg = res?.messages?.[res.messages.length - 1]?.content || 'No advice generated.'
    setAdvice(msg)
    setLoading(false)
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Financial Dashboard</h2>
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
          onClick={handleGetAdvice}
          disabled={loading || !userId}
          className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium"
        >
          {loading ? 'Analyzing...' : 'Get Advice'}
        </button>
      </div>
      {advice && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
          <p className="text-sm leading-relaxed">{advice}</p>
        </div>
      )}
    </div>
  )
}
