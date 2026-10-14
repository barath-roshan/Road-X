import React, { useEffect, useState } from 'react'
import {
  ClipboardList,
  Clock,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  TrendingUp,
  ArrowRight,
  HardHat,
  RefreshCw,
  ExternalLink,
} from 'lucide-react'
import { contractorService } from '../../services/contractorService'
import type {
  ContractorDashboardOverview,
  ContractorWorkOrderItem,
  ContractorWorkloadSummary,
} from '../../types/contractor'
import { Card, CardHeader, CardTitle, CardContent } from '../../components/Card'
import { Button } from '../../components/Button'
import { Alert } from '../../components/Alert'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { EmptyState } from '../../components/EmptyState'
import { StatusBadge, PriorityBadge } from '../../components/Badge'

interface ContractorOverviewTabProps {
  onNavigateTab: (tab: 'work-orders' | 'rework' | 'pending-verification') => void
  onSelectWorkOrder: (workOrderId: string) => void
}

export const ContractorOverviewTab: React.FC<ContractorOverviewTabProps> = ({
  onNavigateTab,
  onSelectWorkOrder,
}) => {
  const [overview, setOverview] = useState<ContractorDashboardOverview | null>(null)
  const [workload, setWorkload] = useState<ContractorWorkloadSummary | null>(null)
  const [recentOrders, setRecentOrders] = useState<ContractorWorkOrderItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [overviewData, workloadData, ordersData] = await Promise.all([
        contractorService.getOverview(),
        contractorService.getWorkloadSummary().catch(() => null),
        contractorService.listWorkOrders({ limit: 5, sort_by: 'created_at', sort_order: 'desc' }).catch(() => []),
      ])
      setOverview(overviewData)
      setWorkload(workloadData)
      setRecentOrders(ordersData)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load contractor overview statistics.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="py-16 flex flex-col items-center justify-center">
        <LoadingSpinner size="lg" />
        <p className="mt-4 text-sm text-slate-500 font-medium">Loading contractor dashboard overview...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Alert
          variant="error"
          title="Overview Unavailable"
        >
          {error}
        </Alert>
        <Button variant="secondary" onClick={fetchData} className="gap-2">
          <RefreshCw className="h-4 w-4" />
          <span>Retry Loading</span>
        </Button>
      </div>
    )
  }

  if (!overview) {
    return null
  }

  return (
    <div className="space-y-6">
      {/* Rework Alert Banner (Prominent Callout if rework required) */}
      {overview.rework > 0 && (
        <div
          data-testid="rework-alert-banner"
          className="bg-amber-50 border-2 border-amber-400/80 rounded-xl p-5 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
        >
          <div className="flex items-start gap-3">
            <div className="p-2 bg-amber-100 rounded-lg text-amber-700 mt-0.5">
              <RotateCcw className="h-5 w-5 animate-pulse" />
            </div>
            <div>
              <h2 className="text-base font-bold text-amber-900">
                Action Required: {overview.rework} Work Order{overview.rework > 1 ? 's' : ''} Returned for Rework
              </h2>
              <p className="text-xs text-amber-700 mt-0.5">
                Government verification rejected repair evidence on {overview.rework} job{overview.rework > 1 ? 's' : ''}.
                Inspect officer rejection feedback, execute corrective repairs, and resubmit for verification.
              </p>
            </div>
          </div>
          <Button
            size="sm"
            onClick={() => onNavigateTab('rework')}
            className="bg-amber-600 hover:bg-amber-700 text-white shrink-0 gap-1.5 shadow-xs"
          >
            <span>Review Rework Queue</span>
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {/* Total Assigned */}
        <Card className="border-slate-200 shadow-2xs hover:border-slate-300 transition-colors">
          <CardContent className="p-4">
            <div className="flex items-center justify-between text-slate-500 mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider">Total Orders</span>
              <ClipboardList className="h-4 w-4 text-blue-600" />
            </div>
            <div className="text-2xl font-bold text-slate-900" data-testid="kpi-total-assigned">
              {overview.total_assigned}
            </div>
            <div className="text-xs text-slate-500 mt-1">Contract assignments</div>
          </CardContent>
        </Card>

        {/* Assigned / Pending Start */}
        <Card className="border-slate-200 shadow-2xs hover:border-slate-300 transition-colors">
          <CardContent className="p-4">
            <div className="flex items-center justify-between text-slate-500 mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider">Assigned</span>
              <HardHat className="h-4 w-4 text-amber-600" />
            </div>
            <div className="text-2xl font-bold text-slate-900" data-testid="kpi-assigned">
              {overview.assigned}
            </div>
            <div className="text-xs text-slate-500 mt-1">Awaiting start</div>
          </CardContent>
        </Card>

        {/* In Progress */}
        <Card className="border-slate-200 shadow-2xs hover:border-slate-300 transition-colors">
          <CardContent className="p-4">
            <div className="flex items-center justify-between text-slate-500 mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider">In Progress</span>
              <Clock className="h-4 w-4 text-indigo-600" />
            </div>
            <div className="text-2xl font-bold text-slate-900" data-testid="kpi-in-progress">
              {overview.in_progress}
            </div>
            <div className="text-xs text-slate-500 mt-1">Active repair work</div>
          </CardContent>
        </Card>

        {/* Pending Verification */}
        <Card className="border-slate-200 shadow-2xs hover:border-slate-300 transition-colors">
          <CardContent className="p-4">
            <div className="flex items-center justify-between text-slate-500 mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider">Pending Sign-off</span>
              <AlertTriangle className="h-4 w-4 text-purple-600" />
            </div>
            <div className="text-2xl font-bold text-slate-900" data-testid="kpi-pending-verification">
              {overview.pending_verification}
            </div>
            <div className="text-xs text-slate-500 mt-1">Submitted to govt</div>
          </CardContent>
        </Card>

        {/* Completed */}
        <Card className="border-slate-200 shadow-2xs hover:border-slate-300 transition-colors">
          <CardContent className="p-4">
            <div className="flex items-center justify-between text-slate-500 mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider">Completed</span>
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            </div>
            <div className="text-2xl font-bold text-slate-900" data-testid="kpi-completed">
              {overview.completed}
            </div>
            <div className="text-xs text-slate-500 mt-1">Verified & closed</div>
          </CardContent>
        </Card>

        {/* Rework Count */}
        <Card
          className={`border-slate-200 shadow-2xs transition-colors ${
            overview.rework > 0 ? 'border-amber-300 bg-amber-50/40' : ''
          }`}
        >
          <CardContent className="p-4">
            <div className="flex items-center justify-between text-slate-500 mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider">Rework</span>
              <RotateCcw className={`h-4 w-4 ${overview.rework > 0 ? 'text-amber-600' : 'text-slate-400'}`} />
            </div>
            <div
              className={`text-2xl font-bold ${overview.rework > 0 ? 'text-amber-700' : 'text-slate-900'}`}
              data-testid="kpi-rework"
            >
              {overview.rework}
            </div>
            <div className="text-xs text-slate-500 mt-1">Rejection updates</div>
          </CardContent>
        </Card>
      </div>

      {/* Progress & Workload Summary Card */}
      <Card className="border-slate-200">
        <CardHeader className="pb-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <CardTitle className="text-base font-bold text-slate-900 flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-indigo-600" />
                <span>Overall Execution Progress</span>
              </CardTitle>
              <p className="text-xs text-slate-500 mt-0.5">
                Aggregate completion metric across all assigned municipal work orders
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-extrabold text-indigo-600" data-testid="kpi-average-progress">
                {overview.average_progress}%
              </span>
              <span className="text-xs text-slate-400 font-medium">Avg Progress</span>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Progress Bar */}
          <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden mb-4">
            <div
              className="bg-indigo-600 h-3 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${Math.min(100, Math.max(0, overview.average_progress))}%` }}
              role="progressbar"
              aria-valuenow={overview.average_progress}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>

          {/* Workload breakdown metrics if available */}
          {workload && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-3 border-t border-slate-100 text-xs">
              <div>
                <span className="text-slate-500">Active Repair Orders:</span>
                <span className="ml-2 font-bold text-slate-800">{workload.active_assignments}</span>
              </div>
              <div>
                <span className="text-slate-500">Awaiting Govt Sign-off:</span>
                <span className="ml-2 font-bold text-purple-700">{workload.pending_verification}</span>
              </div>
              <div>
                <span className="text-slate-500">Rework Required:</span>
                <span className="ml-2 font-bold text-amber-700">{workload.rework_required}</span>
              </div>
              <div>
                <span className="text-slate-500">Resolved & Closed:</span>
                <span className="ml-2 font-bold text-emerald-700">{workload.resolved_completed}</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent Assigned Work Orders Table */}
      <Card className="border-slate-200">
        <CardHeader className="pb-3 flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base font-bold text-slate-900">Recent Assigned Work Orders</CardTitle>
            <p className="text-xs text-slate-500 mt-0.5">
              Latest road maintenance work orders dispatched to your team
            </p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => onNavigateTab('work-orders')}
            className="text-xs gap-1.5"
          >
            <span>View All ({overview.total_assigned})</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </CardHeader>
        <CardContent>
          {recentOrders.length === 0 ? (
            <EmptyState
              icon={<ClipboardList className="h-8 w-8 text-slate-400" />}
              title="No Work Orders Assigned"
              description="No road maintenance work orders have been dispatched to your contractor ID yet."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-collapse" data-testid="recent-work-orders-table">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/75 text-xs text-slate-600 uppercase tracking-wider font-semibold">
                    <th className="py-2.5 px-3">Work Order</th>
                    <th className="py-2.5 px-3">Road Location</th>
                    <th className="py-2.5 px-3">Priority</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Progress</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {recentOrders.map((wo) => (
                    <tr key={wo.id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-3 px-3">
                        <div className="font-semibold text-slate-900 line-clamp-1">{wo.title}</div>
                        <div className="text-xs text-slate-400 font-mono">WO: {wo.id.slice(0, 8)}...</div>
                      </td>
                      <td className="py-3 px-3 text-slate-600 text-xs">
                        {wo.road_name || 'Unspecified road segment'}
                      </td>
                      <td className="py-3 px-3">
                        <PriorityBadge priority={wo.priority} />
                      </td>
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-1.5">
                          <StatusBadge status={wo.status} />
                          {wo.rework_required && (
                            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800 border border-amber-300">
                              Rework
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        <div className="w-24">
                          <div className="flex justify-between text-[11px] font-semibold text-slate-600 mb-0.5">
                            <span>{wo.progress_percentage}%</span>
                          </div>
                          <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                            <div
                              className="bg-indigo-600 h-1.5 rounded-full"
                              style={{ width: `${wo.progress_percentage}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-3 text-right">
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => onSelectWorkOrder(wo.id)}
                          className="text-xs gap-1 py-1 px-2.5"
                          data-testid={`inspect-wo-${wo.id}`}
                        >
                          <span>Inspect</span>
                          <ExternalLink className="h-3 w-3" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
