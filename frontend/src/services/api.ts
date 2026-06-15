const API_BASE = '/api/v1'

export async function ingestFile(userId: string, file?: File | null, text?: string, password?: string) {
  const form = new FormData()
  form.append('user_id', userId)
  if (file) form.append('file', file)
  if (text) form.append('text', text)
  if (password) form.append('password', password)
  const res = await fetch(`${API_BASE}/ingest`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || `Upload failed (${res.status})`)
  }
  return res.json()
}

export async function getAdvice(userId: string) {
  const res = await fetch(`${API_BASE}/advice/${userId}`)
  return res.json()
}

export function createChatSocket(): WebSocket {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return new WebSocket(`${proto}://${location.host}/api/v1/ws`)
}
