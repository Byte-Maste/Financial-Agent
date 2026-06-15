import { useState } from 'react'
import { ingestFile } from '../services/api'

export default function Upload() {
  const [userId, setUserId] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [password, setPassword] = useState('')
  const [text, setText] = useState('')
  const [result, setResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleUpload = async () => {
    if (!userId) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await ingestFile(userId, file, text, password)
      setResult(JSON.stringify(res, null, 2))
    } catch (e: any) {
      setError(e.message || 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <h2 className="text-2xl font-semibold">Upload Financial Data</h2>
      <div>
        <label className="block text-sm text-gray-400 mb-1">User ID</label>
        <input
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm w-full"
          value={userId}
          onChange={e => setUserId(e.target.value)}
          placeholder="Enter your user ID"
        />
      </div>
      <div>
        <label className="block text-sm text-gray-400 mb-1">File (PDF or CSV)</label>
        <input
          type="file"
          accept=".pdf,.csv"
          onChange={e => setFile(e.target.files?.[0] || null)}
          className="text-sm"
        />
      </div>
      {file && file.name.endsWith('.pdf') && (
        <div>
          <label className="block text-sm text-gray-400 mb-1">PDF Password (if protected)</label>
          <input
            type="password"
            className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm w-full"
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="Enter PDF password"
          />
        </div>
      )}
      <div>
        <label className="block text-sm text-gray-400 mb-1">Or paste UPI text</label>
        <textarea
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm w-full h-24"
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Paste UPI transaction messages here..."
        />
      </div>
      <button
        onClick={handleUpload}
        disabled={!userId || loading}
        className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium"
      >
        {loading ? 'Uploading...' : 'Upload & Ingest'}
      </button>
      {error && (
        <div className="bg-red-900/50 border border-red-700 rounded-lg p-4 text-sm text-red-200">
          {error}
        </div>
      )}
      {result && (
        <pre className="bg-gray-800 border border-gray-700 rounded-lg p-4 text-xs overflow-auto">
          {result}
        </pre>
      )}
    </div>
  )
}
