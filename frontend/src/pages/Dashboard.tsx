import { useState, useEffect } from 'react'
import { getDashboard, getAdvice } from '../services/api'

function cls(...classes: string[]) { return classes.filter(Boolean).join(' ') }

export default function Dashboard() {
  const [userId, setUserId] = useState('')
  const [data, setData] = useState<any>(null)
  const [coach, setCoach] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const load = async () => {
    if (!userId) return
    setLoading(true)
    try {
      const [dash, advice] = await Promise.all([
        getDashboard(userId),
        getAdvice(userId),
      ])
      setData(dash)
      const msg = advice?.messages?.[advice.messages.length - 1]?.content || ''
      setCoach(msg)
    } catch (e: any) {
      alert(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { if (data) load() }, [])

  const fhs = data?.financial_health_score ?? 0
  const fhsColor = fhs >= 80 ? 'text-emerald-400' : fhs >= 50 ? 'text-yellow-400' : 'text-red-400'
  const savingsRate = data?.savings_rate != null ? (data.savings_rate * 100).toFixed(0) : '--'
  const efMonths = data?.emergency_fund_months != null ? data.emergency_fund_months.toFixed(1) : '--'
  const budget = data?.budget
  const forecast = data?.cash_flow_forecast
  const alerts = data?.active_alerts ?? []
  const bills = data?.upcoming_bills ?? []

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">AI CFO Dashboard</h2>

      <div className="flex gap-3 items-end flex-wrap">
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
          onClick={load}
          disabled={loading || !userId}
          className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium"
        >
          {loading ? 'Loading...' : 'Load Dashboard'}
        </button>
      </div>

      {data && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* FHS Card */}
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <p className="text-xs text-gray-400 uppercase tracking-wide">Financial Health Score</p>
            <p className={cls('text-4xl font-bold mt-1', fhsColor)}>{fhs}</p>
            <p className="text-sm text-gray-400 mt-1">out of 100</p>
          </div>

          {/* Savings Rate Card */}
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <p className="text-xs text-gray-400 uppercase tracking-wide">Savings Rate</p>
            <p className="text-3xl font-bold text-emerald-400 mt-1">{savingsRate}%</p>
            <p className="text-sm text-gray-400 mt-1">Target: 20%</p>
          </div>

          {/* Emergency Fund Card */}
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <p className="text-xs text-gray-400 uppercase tracking-wide">Emergency Fund</p>
            <p className="text-3xl font-bold text-blue-400 mt-1">{efMonths}m</p>
            <p className="text-sm text-gray-400 mt-1">of expenses covered</p>
          </div>

          {/* Budget Card */}
          {budget && (
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 md:col-span-2">
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">50/30/20 Budget</p>
              <Bar label="Needs" spent={budget.needs_spent} target={budget.needs_target} color="bg-rose-500" />
              <Bar label="Wants" spent={budget.wants_spent} target={budget.wants_target} color="bg-amber-500" />
              <Bar label="Savings" spent={budget.savings_actual} target={budget.savings_target} color="bg-emerald-500" />
            </div>
          )}

          {/* Forecast Card */}
          {forecast && (
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
              <p className="text-xs text-gray-400 uppercase tracking-wide">Cash Flow Forecast</p>
              <p className="text-sm mt-2">
                <span className="text-gray-400">Balance:</span>{' '}
                <span className="font-medium">₹{forecast.current_balance?.toLocaleString() ?? 0}</span>
              </p>
              <p className="text-sm">
                <span className="text-gray-400">Projected (30d):</span>{' '}
                <span className={cls('font-medium', (forecast.projected_balance_day_30 ?? 0) < 0 ? 'text-red-400' : 'text-green-400')}>
                  ₹{forecast.projected_balance_day_30?.toLocaleString() ?? 0}
                </span>
              </p>
            </div>
          )}

          {/* Alerts Card */}
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <p className="text-xs text-gray-400 uppercase tracking-wide">Active Alerts ({alerts.length})</p>
            <div className="space-y-2 mt-2 max-h-48 overflow-y-auto">
              {alerts.length === 0 && <p className="text-sm text-gray-500">No alerts</p>}
              {alerts.map((a: any, i: number) => (
                <div key={i} className="text-sm border-l-2 pl-2 border-current"
                  style={{ borderColor: a.severity === 'high' ? '#ef4444' : a.severity === 'medium' ? '#f59e0b' : '#6ee7b7' }}
                >
                  <p className="text-gray-300">{a.message}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Upcoming Bills Card */}
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <p className="text-xs text-gray-400 uppercase tracking-wide">Upcoming Bills ({bills.length})</p>
            <div className="space-y-1 mt-2 max-h-48 overflow-y-auto">
              {bills.length === 0 && <p className="text-sm text-gray-500">No upcoming bills</p>}
              {bills.map((b: any, i: number) => (
                <div key={i} className="flex justify-between text-sm">
                  <span className="text-gray-300">{b.merchant}</span>
                  <span className={b.due_in_days != null && b.due_in_days <= 3 ? 'text-red-400 font-medium' : 'text-gray-400'}>
                    ₹{b.amount?.toLocaleString()} {b.due_in_days != null ? `(${b.due_in_days}d)` : ''}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Coach's Note */}
          {coach && (
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 md:col-span-3">
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Coach's Note</p>
              <p className="text-sm leading-relaxed">{coach}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Bar({ label, spent, target, color }: { label: string; spent: number; target: number; color: string }) {
  const pct = target > 0 ? Math.min((spent / target) * 100, 100) : 0
  const over = spent > target
  return (
    <div className="mb-2">
      <div className="flex justify-between text-sm mb-1">
        <span>{label}</span>
        <span className={over ? 'text-red-400' : 'text-gray-300'}>
          ₹{spent?.toLocaleString()} / ₹{target?.toLocaleString()}
        </span>
      </div>
      <div className="w-full bg-gray-700 rounded-full h-2.5">
        <div className={cls('h-2.5 rounded-full', color, over ? 'opacity-80' : '')}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
