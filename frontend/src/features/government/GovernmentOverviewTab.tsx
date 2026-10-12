import React, { useEffect, useState } from 'react'
import {
  FileText,
  Clock,
  CheckCircle2,
  AlertTriangle,
  HardHat,
  RefreshCw,
  TrendingUp,
  BarChart3,
  Layers,
  ArrowRight,
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '../../components/Card'
import { Button } from '../../components/Button'
import { Alert } from '../../components/Alert'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { governmentService } from '../../services/governmentService'
import type { GovernmentDashboardOverview } from '../../types/government'

interface GovernmentOverviewTabProps {
  onNavigateTab: (tab: string) => void
}

export const GovernmentOverviewTab: React.FC<GovernmentOverviewTabProps> = ({ onNavigateTab }) => {
  const [overview, setOverview] = useState<GovernmentDashboardOverview | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const fetchOverview = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await governmentService.getOverview()
      setOverview(data)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load dashboard overview.'
      setError(message)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchOverview()
  }, [])

  if (isLoading) {
    return (
      <div className="py-16 flex flex-col items-center justify-center space-y-4">
        <LoadingSpinner size="lg" message="Loading municipal overview metrics..." />
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-4 py-6">
        <Alert
          variant="error"
          title="Overview Error"
          onDismiss={() => setError(null)}
        >
          {error}
        </Alert>
        <Button variant="outline" size="sm" onClick={fetchOverview} className="flex items-center gap-1.5">
          <RefreshCw className="h-4 w-4" />
          Retry
        </Button>
      </div>
    )
  }

  if (!overview) return null

  const submittedCount = overview.status_counts['SUBMITTED'] || 0
  const underReviewCount = overview.status_counts['UNDER_REVIEW'] || 0
  const inProgressCount = overview.status_counts['IN_PROGRESS'] || 0
  const pendingVerifications = overview.pending_verifications_count || 0

  return (
    <div className="space-y-6">
      {/* Top Header with Refresh Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Executive Civic Overview</h2>
          <p className="text-xs text-slate-500">
            Real-time aggregate road grievance metrics, maintenance work orders, and contractor status.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchOverview}
          className="self-start sm:self-auto flex items-center gap-1.5 text-slate-600"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh Metrics
        </Button>
      </div>

      {/* Action Banner for Pending Verifications */}
      {pendingVerifications > 0 && (
        <div className="bg-amber-50 border border-amber-200/80 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-2xs">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-amber-100 rounded-lg text-amber-700">
              <Clock className="h-5 w-5" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-amber-900">
                {pendingVerifications} Work {pendingVerifications === 1 ? 'Order' : 'Orders'} Awaiting Verification
              </h4>
              <p className="text-xs text-amber-700">
                Contractors have completed repairs. Municipal officer verification is required to officially resolve citizen grievances.
              </p>
            </div>
          </div>
          <Button
            size="sm"
            onClick={() => onNavigateTab('verifications')}
            className="bg-amber-600 hover:bg-amber-700 text-white shrink-0"
          >
            Review Queue
            <ArrowRight className="h-3.5 w-3.5 ml-1" />
          </Button>
        </div>
      )}

      {/* Top 4 KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="hover:border-slate-300 transition-all shadow-2xs">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Grievances</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{overview.total_grievances}</h3>
              <p className="text-[11px] text-slate-400 mt-1">Logged by citizens & sensors</p>
            </div>
            <div className="h-12 w-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <FileText className="h-6 w-6" />
            </div>
          </CardContent>
        </Card>

        <Card className="hover:border-slate-300 transition-all shadow-2xs">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Pending Officer Review</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{submittedCount + underReviewCount}</h3>
              <p className="text-[11px] text-amber-600 font-medium mt-1">
                {submittedCount} new, {underReviewCount} in review
              </p>
            </div>
            <div className="h-12 w-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <Clock className="h-6 w-6" />
            </div>
          </CardContent>
        </Card>

        <Card className="hover:border-slate-300 transition-all shadow-2xs">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Active In-Progress</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{inProgressCount}</h3>
              <p className="text-[11px] text-indigo-600 font-medium mt-1">Maintenance ongoing</p>
            </div>
            <div className="h-12 w-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <TrendingUp className="h-6 w-6" />
            </div>
          </CardContent>
        </Card>

        <Card className="hover:border-slate-300 transition-all shadow-2xs">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Active Contractors</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{overview.active_contractors_count}</h3>
              <p className="text-[11px] text-slate-400 mt-1">Available for dispatch</p>
            </div>
            <div className="h-12 w-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <HardHat className="h-6 w-6" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Breakdown Grids */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Grievance Lifecycle Status */}
        <Card className="shadow-2xs">
          <CardHeader className="border-b border-slate-100 pb-3">
            <CardTitle className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Layers className="h-4 w-4 text-indigo-600" />
              Grievance Lifecycle Status
            </CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-3">
            {Object.entries(overview.status_counts).length === 0 ? (
              <p className="text-xs text-slate-400 italic">No grievances recorded.</p>
            ) : (
              Object.entries(overview.status_counts).map(([statusKey, count]) => {
                const total = overview.total_grievances || 1
                const pct = Math.round((count / total) * 100)
                const colorClass =
                  statusKey === 'RESOLVED'
                    ? 'bg-emerald-500'
                    : statusKey === 'IN_PROGRESS'
                    ? 'bg-blue-500'
                    : statusKey === 'PENDING_VERIFICATION'
                    ? 'bg-amber-500'
                    : statusKey === 'REJECTED'
                    ? 'bg-rose-500'
                    : 'bg-indigo-500'

                return (
                  <div key={statusKey} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="font-medium text-slate-700">{statusKey.replace('_', ' ')}</span>
                      <span className="text-slate-500 font-mono">
                        {count} ({pct}%)
                      </span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                      <div className={`${colorClass} h-2 rounded-full`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                )
              })
            )}
          </CardContent>
        </Card>

        {/* ML Priority Breakdown */}
        <Card className="shadow-2xs">
          <CardHeader className="border-b border-slate-100 pb-3">
            <CardTitle className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-indigo-600" />
              ML Decision Support Priority Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-3">
            {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((tier) => {
              const count = overview.priority_counts[tier] || 0
              const total = overview.total_grievances || 1
              const pct = Math.round((count / total) * 100)
              const badgeBg =
                tier === 'CRITICAL'
                  ? 'bg-rose-500'
                  : tier === 'HIGH'
                  ? 'bg-amber-500'
                  : tier === 'MEDIUM'
                  ? 'bg-blue-500'
                  : 'bg-slate-400'

              return (
                <div key={tier} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                      <span className={`h-2 w-2 rounded-full ${badgeBg}`} />
                      {tier}
                    </span>
                    <span className="text-slate-500 font-mono">
                      {count} ({pct}%)
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                    <div className={`${badgeBg} h-2 rounded-full`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              )
            })}
          </CardContent>
        </Card>

        {/* Damage Severity Breakdown */}
        <Card className="shadow-2xs">
          <CardHeader className="border-b border-slate-100 pb-3">
            <CardTitle className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-indigo-600" />
              Predicted Damage Severity
            </CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-3">
            {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((tier) => {
              const count = overview.severity_counts[tier] || 0
              const total = overview.total_grievances || 1
              const pct = Math.round((count / total) * 100)
              const badgeBg =
                tier === 'CRITICAL'
                  ? 'bg-red-500'
                  : tier === 'HIGH'
                  ? 'bg-orange-500'
                  : tier === 'MEDIUM'
                  ? 'bg-sky-500'
                  : 'bg-slate-400'

              return (
                <div key={tier} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                      <span className={`h-2 w-2 rounded-full ${badgeBg}`} />
                      {tier}
                    </span>
                    <span className="text-slate-500 font-mono">{count} cases</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                    <div className={`${badgeBg} h-2 rounded-full`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              )
            })}
          </CardContent>
        </Card>

        {/* Work Order Lifecycle Breakdown */}
        <Card className="shadow-2xs">
          <CardHeader className="border-b border-slate-100 pb-3">
            <CardTitle className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-indigo-600" />
              Work Order Lifecycle Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-3">
            {Object.entries(overview.work_order_counts).length === 0 ? (
              <p className="text-xs text-slate-400 italic">No work orders created yet.</p>
            ) : (
              Object.entries(overview.work_order_counts).map(([woStatus, count]) => {
                return (
                  <div key={woStatus} className="flex items-center justify-between text-xs py-1 border-b border-slate-50 last:border-0">
                    <span className="font-medium text-slate-700">{woStatus.replace('_', ' ')}</span>
                    <span className="font-semibold text-slate-900 bg-slate-100 px-2 py-0.5 rounded">
                      {count}
                    </span>
                  </div>
                )
              })
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
