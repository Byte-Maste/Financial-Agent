import { Routes, Route, Link } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import Chat from './pages/Chat'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <nav className="border-b border-gray-800 px-6 py-3 flex items-center gap-6">
        <h1 className="text-lg font-bold text-emerald-400">FinAgent</h1>
        <Link to="/" className="text-sm hover:text-emerald-300 transition">Dashboard</Link>
        <Link to="/upload" className="text-sm hover:text-emerald-300 transition">Upload</Link>
        <Link to="/chat" className="text-sm hover:text-emerald-300 transition">Chat</Link>
      </nav>
      <main className="p-6 max-w-6xl mx-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/chat" element={<Chat />} />
        </Routes>
      </main>
    </div>
  )
}
