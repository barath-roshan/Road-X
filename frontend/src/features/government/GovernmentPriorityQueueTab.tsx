import React, { useEffect, useState } from 'react'
import {
  RefreshCw,
  Clock,
  ArrowUpRight,
  MapPin,
} from 'lucide-react'
import { Card, CardContent } from '../../components/Card'
import { Button } from '../../components/Button'
import { Alert } from '../../components/Alert'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { EmptyState } from '../../components/EmptyState'
import { governmentService } from '../../services/governmentService'
import { GovernmentGrievanceDetailModal } from './GovernmentGrievanceDetailModal'
import type { GovernmentDashboardPriorityItem } from '../../types/government'

export const GovernmentPriorityQueueTab: React.FC = () => {
  const [items, setItems] = useState<GovernmentDashboardPriorityItem[]>([])
  const [minPriority, setMinPriority] = useState<string>('')
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedGrievanceId, setSelectedGrievanceId] = useState<string | null>(null)

  const fetchPriorityQueue = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await governmentService.getPriorityQueue({
        min_priority: minPriority || undefined,
      })
      setItems(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load priority queue.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchPriorityQueue()
  }, [minPriority])

  const getPriorityBadgeClass = (level: string) => {
    switch (level) {
      case 'CRITICAL':
        return 'bg-rose-100 text-rose-800 border-rose-200'
      case 'HIGH':
        return 'bg-amber-100 text-amber-800 border-amber-200'
      case 'MEDIUM':
        return 'bg-blue-100 text-blue-800 border-blue-200'
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            Prioritized Maintenance Queue
          </h2>
          <p className="text-xs text-slate-500">
            Road hazards ranked by the RoadX ML Maintenance Priority engine based on severity, traffic risk, and time-to-failure.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={minPriority}
            onChange={(e) => setMinPriority(e.target.value)}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs bg-white text-slate-700 focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Priority Levels</option>
            <option value="CRITICAL">Critical Only</option>
            <option value="HIGH">High & Above</option>
            <option value="MEDIUM">Medium & Above</option>
            <option value="LOW">Low</option>
          </select>

          <Button
            variant="outline"
            size="sm"
            onClick={fetchPriorityQueue}
            className="flex items-center gap-1.5 text-slate-600"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="error" title="Queue Error" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      {isLoading ? (
        <div className="py-16 flex justify-center">
          <LoadingSpinner size="lg" message="Computing predictive priority ordering..." />
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          title="No Priority Items"
          description="There are currently no road maintenance hazards requiring urgent dispatch in this priority tier."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {items.map((item, index) => {
            const scorePct = Math.min(100, Math.max(0, Math.round(item.priority_score || 0)))

            return (
              <Card
                key={item.grievance_id}
                className="hover:border-slate-300 transition-all border-l-4 shadow-2xs"
                style={{
                  borderLeftColor:
                    item.priority_level === 'CRITICAL'
                      ? '#e11d48'
                      : item.priority_level === 'HIGH'
                      ? '#d97706'
                      : item.priority_level === 'MEDIUM'
                      ? '#2563eb'
                      : '#94a3b8',
                }}
              >
                <CardContent className="p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-5">
                  {/* Left Column: Rank + Case Info */}
                  <div className="flex items-start gap-4 flex-1">
                    <div className="flex flex-col items-center justify-center h-12 w-12 rounded-xl bg-slate-100 text-slate-700 shrink-0 font-bold font-mono text-sm">
                      <span className="text-[10px] text-slate-400 font-sans font-medium uppercase">RANK</span>
                      #{index + 1}
                    </div>

                    <div className="space-y-1.5 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${getPriorityBadgeClass(
                            item.priority_level
                          )}`}
                        >
                          {item.priority_level}
                        </span>
                        <h4 className="text-sm font-bold text-slate-900">{item.issue_category}</h4>
                        <span className="text-xs text-slate-400">•</span>
                        <span className="text-xs font-medium text-slate-700 flex items-center gap-1">
                          <MapPin className="h-3 w-3 text-slate-400" />
                          {item.road_name || 'Unassigned Road'}
                        </span>
                      </div>

                      <p className="text-xs text-slate-600 line-clamp-2">{item.description}</p>

                      {/* ML Reason Tags */}
                      {item.reasons.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {item.reasons.map((r, rIdx) => (
                            <span
                              key={rIdx}
                              className="inline-flex items-center px-2 py-0.5 rounded text-[10px] bg-slate-100 text-slate-600 border border-slate-200"
                            >
                              {r}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Middle Column: Predictive Stats */}
                  <div className="flex items-center gap-6 text-xs text-slate-600 border-t md:border-t-0 md:border-l border-slate-100 pt-3 md:pt-0 md:pl-6 shrink-0">
                    <div>
                      <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block">
                        Priority Score
                      </span>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-lg font-bold text-slate-900">{scorePct}</span>
                        <span className="text-[10px] text-slate-400">/ 100</span>
                      </div>
                    </div>

                    <div>
                      <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block">
                        Time to Failure
                      </span>
                      <div className="flex items-center gap-1.5 mt-0.5 font-semibold text-slate-800">
                        <Clock className="h-3.5 w-3.5 text-slate-400" />
                        {item.estimated_time_to_failure_days != null
                          ? `${item.estimated_time_to_failure_days} days`
                          : 'N/A'}
                      </div>
                    </div>
                  </div>

                  {/* Right Column: Inspect Case CTA */}
                  <div className="self-end md:self-center shrink-0">
                    <Button
                      size="sm"
                      onClick={() => setSelectedGrievanceId(item.grievance_id)}
                      className="bg-indigo-600 hover:bg-indigo-700 text-white flex items-center gap-1.5"
                    >
                      Inspect & Assign
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* Case inspection modal */}
      <GovernmentGrievanceDetailModal
        grievanceId={selectedGrievanceId}
        onClose={() => setSelectedGrievanceId(null)}
        onGrievanceUpdated={() => {
          fetchPriorityQueue()
        }}
      />
    </div>
  )
}
