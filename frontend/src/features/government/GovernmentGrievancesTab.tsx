import React, { useEffect, useState } from 'react'
import {
  Search,
  RefreshCw,
  Eye,
  MapPin,
  Calendar,
  X,
} from 'lucide-react'
import { Card, CardContent } from '../../components/Card'
import { Button } from '../../components/Button'
import { Badge } from '../../components/Badge'
import { Alert } from '../../components/Alert'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { EmptyState } from '../../components/EmptyState'
import { governmentService } from '../../services/governmentService'
import type { GrievanceFilterParams } from '../../services/governmentService'
import { GovernmentGrievanceDetailModal } from './GovernmentGrievanceDetailModal'
import type {
  GovernmentDashboardGrievanceItem,
  GrievanceStatus,
} from '../../types/government'

export const GovernmentGrievancesTab: React.FC = () => {
  const [grievances, setGrievances] = useState<GovernmentDashboardGrievanceItem[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  // Filters state
  const [search, setSearch] = useState<string>('')
  const [status, setStatus] = useState<GrievanceStatus | ''>('')
  const [category, setCategory] = useState<string>('')
  const [priority, setPriority] = useState<string>('')
  const [severity, setSeverity] = useState<string>('')

  // Active detail modal
  const [selectedGrievanceId, setSelectedGrievanceId] = useState<string | null>(null)

  const fetchGrievances = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const params: GrievanceFilterParams = {
        search: search.trim() || undefined,
        status: status || undefined,
        issue_category: category.trim() || undefined,
        priority: priority || undefined,
        severity: severity || undefined,
      }
      const data = await governmentService.listGrievances(params)
      setGrievances(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch grievances.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchGrievances()
  }, [status, priority, severity])

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    fetchGrievances()
  }

  const handleResetFilters = () => {
    setSearch('')
    setStatus('')
    setCategory('')
    setPriority('')
    setSeverity('')
    // will trigger reload due to useEffect dependency changes or call directly
    setTimeout(() => {
      fetchGrievances()
    }, 0)
  }

  const getStatusBadgeVariant = (st: GrievanceStatus): 'default' | 'officer' | 'warning' | 'danger' | 'success' => {
    switch (st) {
      case 'RESOLVED':
        return 'success'
      case 'IN_PROGRESS':
        return 'officer'
      case 'PENDING_VERIFICATION':
        return 'warning'
      case 'REJECTED':
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
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Grievance Management</h2>
          <p className="text-xs text-slate-500">
            Audit, filter, review, and commission repairs for citizen-reported road grievances.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchGrievances}
          className="self-start sm:self-auto flex items-center gap-1.5 text-slate-600"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh Queue
        </Button>
      </div>

      {/* Filter and Search Bar */}
      <Card className="shadow-2xs">
        <CardContent className="p-4 space-y-3">
          <form onSubmit={handleSearchSubmit} className="flex flex-col md:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search description, road name, or grievance ID..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div className="flex items-center gap-2">
              <Button type="submit" size="sm" className="bg-indigo-600 text-white hover:bg-indigo-700">
                Search
              </Button>
              {(search || status || category || priority || severity) && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleResetFilters}
                  className="text-slate-500 hover:text-slate-700"
                >
                  <X className="h-3.5 w-3.5 mr-1" />
                  Clear
                </Button>
              )}
            </div>
          </form>

          {/* Filter Dropdowns */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-100 text-xs">
            <div>
              <label className="block text-[11px] font-semibold text-slate-500 mb-1">Status</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as GrievanceStatus | '')}
                className="w-full rounded-md border border-slate-200 p-1.5 text-xs bg-white text-slate-700 focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">All Statuses</option>
                <option value="SUBMITTED">SUBMITTED</option>
                <option value="UNDER_REVIEW">UNDER_REVIEW</option>
                <option value="IN_PROGRESS">IN_PROGRESS</option>
                <option value="PENDING_VERIFICATION">PENDING_VERIFICATION</option>
                <option value="RESOLVED">RESOLVED</option>
                <option value="REJECTED">REJECTED</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-500 mb-1">Category</label>
              <input
                type="text"
                placeholder="e.g. POTHOLE"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                onBlur={fetchGrievances}
                className="w-full rounded-md border border-slate-200 p-1.5 text-xs bg-white text-slate-700 focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-500 mb-1">ML Priority</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full rounded-md border border-slate-200 p-1.5 text-xs bg-white text-slate-700 focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">All Priorities</option>
                <option value="CRITICAL">CRITICAL</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-500 mb-1">ML Severity</label>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="w-full rounded-md border border-slate-200 p-1.5 text-xs bg-white text-slate-700 focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">All Severities</option>
                <option value="CRITICAL">CRITICAL</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Error state */}
      {error && (
        <Alert variant="error" title="Queue Error" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Content Table */}
      {isLoading ? (
        <div className="py-16 flex justify-center">
          <LoadingSpinner size="lg" message="Loading grievance records..." />
        </div>
      ) : grievances.length === 0 ? (
        <EmptyState
          title="No Grievances Found"
          description="No road complaints match your active filter criteria. Try adjusting or clearing search filters."
          action={
            <Button size="sm" variant="outline" onClick={handleResetFilters}>
              Reset Filters
            </Button>
          }
        />
      ) : (
        <Card className="overflow-hidden shadow-2xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                  <th className="py-3 px-4">Case / Category</th>
                  <th className="py-3 px-4">Location / Road</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">ML Priority</th>
                  <th className="py-3 px-4">Contractor / WO</th>
                  <th className="py-3 px-4">Submitted</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {grievances.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-900">{item.issue_category}</div>
                      <div className="text-[11px] text-slate-500 line-clamp-1 max-w-xs">
                        {item.description}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                        ID: {item.id.slice(0, 8)}...
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-medium text-slate-800 flex items-center gap-1">
                        <MapPin className="h-3 w-3 text-slate-400" />
                        {item.road_name || 'Unassigned Road'}
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        {item.latitude.toFixed(4)}, {item.longitude.toFixed(4)}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <Badge variant={getStatusBadgeVariant(item.status)}>
                        {item.status.replace('_', ' ')}
                      </Badge>
                    </td>
                    <td className="py-3 px-4">
                      {item.priority ? (
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold ${
                            item.priority === 'CRITICAL'
                              ? 'bg-rose-100 text-rose-800'
                              : item.priority === 'HIGH'
                              ? 'bg-amber-100 text-amber-800'
                              : item.priority === 'MEDIUM'
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-slate-100 text-slate-700'
                          }`}
                        >
                          {item.priority}
                        </span>
                      ) : (
                        <span className="text-slate-400 italic text-[11px]">Pending ML</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      {item.assigned_contractor_name ? (
                        <div>
                          <span className="font-semibold text-slate-800 text-[11px]">
                            {item.assigned_contractor_name}
                          </span>
                          {item.work_order_status && (
                            <span className="block text-[10px] text-slate-500">
                              WO: {item.work_order_status}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-slate-400 italic text-[11px]">Unassigned</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                      <div className="flex items-center gap-1 text-[11px]">
                        <Calendar className="h-3 w-3 text-slate-400" />
                        {new Date(item.created_at).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setSelectedGrievanceId(item.id)}
                        className="text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 border-indigo-200"
                      >
                        <Eye className="h-3.5 w-3.5 mr-1" />
                        Inspect Case
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Grievance Detail Inspection Modal */}
      <GovernmentGrievanceDetailModal
        grievanceId={selectedGrievanceId}
        onClose={() => setSelectedGrievanceId(null)}
        onGrievanceUpdated={() => {
          fetchGrievances()
        }}
      />
    </div>
  )
}
