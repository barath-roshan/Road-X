import React, { useEffect, useState } from 'react'
import {
  HardHat,
  RefreshCw,
  Eye,
  MapPin,
} from 'lucide-react'
import { Card } from '../../components/Card'
import { Button } from '../../components/Button'
import { Badge } from '../../components/Badge'
import { Alert } from '../../components/Alert'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { EmptyState } from '../../components/EmptyState'
import { governmentService } from '../../services/governmentService'
import type { WorkOrderFilterParams } from '../../services/governmentService'
import { GovernmentGrievanceDetailModal } from './GovernmentGrievanceDetailModal'
import type {
  GovernmentDashboardWorkOrderItem,
  WorkOrderStatus,
} from '../../types/government'

export const GovernmentWorkOrdersTab: React.FC = () => {
  const [workOrders, setWorkOrders] = useState<GovernmentDashboardWorkOrderItem[]>([])
  const [statusFilter, setStatusFilter] = useState<WorkOrderStatus | ''>('')
  const [priorityFilter, setPriorityFilter] = useState<string>('')
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedGrievanceId, setSelectedGrievanceId] = useState<string | null>(null)

  const fetchWorkOrders = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const params: WorkOrderFilterParams = {
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
      }
      const data = await governmentService.listWorkOrders(params)
      setWorkOrders(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load work orders.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchWorkOrders()
  }, [statusFilter, priorityFilter])

  const getStatusBadge = (st: WorkOrderStatus): 'default' | 'officer' | 'warning' | 'danger' | 'success' => {
    switch (st) {
      case 'COMPLETED':
        return 'success'
      case 'IN_PROGRESS':
        return 'officer'
      case 'PENDING_VERIFICATION':
        return 'warning'
      case 'CANCELLED':
        return 'danger'
      default:
        return 'default'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            Work Order Monitoring
          </h2>
          <p className="text-xs text-slate-500">
            Track road engineering repairs, contractor progress milestones, and work statuses across the municipality.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as WorkOrderStatus | '')}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs bg-white text-slate-700 focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Statuses</option>
            <option value="OPEN">OPEN</option>
            <option value="ASSIGNED">ASSIGNED</option>
            <option value="IN_PROGRESS">IN_PROGRESS</option>
            <option value="PENDING_VERIFICATION">PENDING_VERIFICATION</option>
            <option value="COMPLETED">COMPLETED</option>
            <option value="CANCELLED">CANCELLED</option>
          </select>

          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs bg-white text-slate-700 focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Priorities</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>

          <Button
            variant="outline"
            size="sm"
            onClick={fetchWorkOrders}
            className="flex items-center gap-1.5 text-slate-600"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="error" title="Work Orders Error" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      {isLoading ? (
        <div className="py-16 flex justify-center">
          <LoadingSpinner size="lg" message="Loading work orders queue..." />
        </div>
      ) : workOrders.length === 0 ? (
        <EmptyState
          title="No Work Orders Found"
          description="There are currently no work orders matching the selected status filters."
        />
      ) : (
        <Card className="overflow-hidden shadow-2xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                  <th className="py-3 px-4">Work Order Title</th>
                  <th className="py-3 px-4">Road / Location</th>
                  <th className="py-3 px-4">Assigned Contractor</th>
                  <th className="py-3 px-4">Priority</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Progress</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {workOrders.map((wo) => {
                  const progressPct = Math.min(100, Math.max(0, wo.current_progress_percentage || 0))

                  return (
                    <tr key={wo.id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-900">{wo.title}</div>
                        <div className="text-[11px] text-slate-500 line-clamp-1 max-w-xs">
                          {wo.description}
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                          ID: {wo.id.slice(0, 8)}...
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-medium text-slate-800 flex items-center gap-1">
                          <MapPin className="h-3 w-3 text-slate-400" />
                          {wo.road_name || 'Unassigned Road'}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        {wo.contractor_name ? (
                          <div className="flex items-center gap-1.5">
                            <HardHat className="h-3.5 w-3.5 text-amber-600" />
                            <span className="font-semibold text-slate-800">{wo.contractor_name}</span>
                          </div>
                        ) : (
                          <span className="text-slate-400 italic">Unassigned (Open)</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold ${
                            wo.priority === 'CRITICAL'
                              ? 'bg-rose-100 text-rose-800'
                              : wo.priority === 'HIGH'
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-blue-100 text-blue-800'
                          }`}
                        >
                          {wo.priority}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant={getStatusBadge(wo.status)}>
                          {wo.status.replace('_', ' ')}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <div className="w-28 space-y-1">
                          <div className="flex justify-between text-[11px]">
                            <span className="font-medium text-slate-700">{progressPct}%</span>
                          </div>
                          <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                            <div
                              className={`h-1.5 rounded-full ${
                                progressPct === 100
                                  ? 'bg-emerald-500'
                                  : progressPct > 50
                                  ? 'bg-indigo-500'
                                  : 'bg-amber-500'
                              }`}
                              style={{ width: `${progressPct}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setSelectedGrievanceId(wo.grievance_id)}
                          className="text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 border-indigo-200"
                        >
                          <Eye className="h-3.5 w-3.5 mr-1" />
                          View Case
                        </Button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Case inspection modal */}
      <GovernmentGrievanceDetailModal
        grievanceId={selectedGrievanceId}
        onClose={() => setSelectedGrievanceId(null)}
        onGrievanceUpdated={() => {
          fetchWorkOrders()
        }}
      />
    </div>
  )
}
