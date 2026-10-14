import React, { useEffect, useState } from 'react'
import {
  ClipboardList,
  Search,
  ArrowUpDown,
  RefreshCw,
  ExternalLink,
  Play,
  RotateCcw,
} from 'lucide-react'
import { contractorService } from '../../services/contractorService'
import type { ContractorWorkOrderItem } from '../../types/contractor'
import type { WorkOrderStatus } from '../../types/government'
import { Card, CardHeader, CardTitle, CardContent } from '../../components/Card'
import { Button } from '../../components/Button'
import { Input } from '../../components/Input'
import { Alert } from '../../components/Alert'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { EmptyState } from '../../components/EmptyState'
import { StatusBadge, PriorityBadge } from '../../components/Badge'

interface ContractorWorkOrdersTabProps {
  onSelectWorkOrder: (workOrderId: string) => void
}

export const ContractorWorkOrdersTab: React.FC<ContractorWorkOrdersTabProps> = ({
  onSelectWorkOrder,
}) => {
  const [workOrders, setWorkOrders] = useState<ContractorWorkOrderItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters & Search
  const [statusFilter, setStatusFilter] = useState<string>('ALL')
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL')
  const [sortBy, setSortBy] = useState<string>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [searchQuery, setSearchQuery] = useState<string>('')

  // Quick Action State
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null)
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null)

  const fetchWorkOrders = async () => {
    setLoading(true)
    setError(null)
    setActionSuccessMsg(null)
    try {
      const data = await contractorService.listWorkOrders({
        status: statusFilter !== 'ALL' ? (statusFilter as WorkOrderStatus) : undefined,
        priority: priorityFilter !== 'ALL' ? priorityFilter : undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        limit: 100,
      })
      setWorkOrders(data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load assigned work orders.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchWorkOrders()
  }, [statusFilter, priorityFilter, sortBy, sortOrder])

  // Quick Start Job action
  const handleQuickStart = async (woId: string) => {
    setActionLoadingId(woId)
    setActionSuccessMsg(null)
    try {
      await contractorService.startWorkOrder(woId, 'Contractor quick started work from list view.')
      setActionSuccessMsg(`Work order started and transitioned to IN_PROGRESS.`)
      await fetchWorkOrders()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to start work order.'
      setError(msg)
    } finally {
      setActionLoadingId(null)
    }
  }

  // Client search filter across contractor-authorized orders
  const filteredOrders = workOrders.filter((wo) => {
    if (!searchQuery.trim()) return true
    const q = searchQuery.toLowerCase()
    return (
      wo.title.toLowerCase().includes(q) ||
      wo.description.toLowerCase().includes(q) ||
      (wo.road_name && wo.road_name.toLowerCase().includes(q)) ||
      wo.grievance_id.toLowerCase().includes(q) ||
      wo.id.toLowerCase().includes(q)
    )
  })

  return (
    <div className="space-y-6">
      {/* Header & Filter Controls Card */}
      <Card className="border-slate-200">
        <CardHeader className="pb-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <CardTitle className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <ClipboardList className="h-5 w-5 text-indigo-600" />
                <span>Assigned Work Orders</span>
              </CardTitle>
              <p className="text-xs text-slate-500 mt-0.5">
                Inspect job specifications, log incremental progress, and submit completed repairs for verification
              </p>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={fetchWorkOrders}
              disabled={loading}
              className="text-xs gap-1.5 self-start sm:self-auto"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {actionSuccessMsg && (
            <div className="mb-4">
              <Alert variant="success">{actionSuccessMsg}</Alert>
            </div>
          )}

          {/* Search & Filters Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Search title, road, or ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 text-xs"
                data-testid="input-search-work-orders"
              />
            </div>

            {/* Status Filter */}
            <div>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                data-testid="filter-status-select"
                className="w-full text-xs rounded-lg border border-slate-300 py-2 px-3 bg-white text-slate-700 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 cursor-pointer"
              >
                <option value="ALL">All Statuses</option>
                <option value="ASSIGNED">Assigned (Awaiting Start)</option>
                <option value="IN_PROGRESS">In Progress</option>
                <option value="PENDING_VERIFICATION">Pending Verification</option>
                <option value="COMPLETED">Completed</option>
                <option value="CANCELLED">Cancelled</option>
              </select>
            </div>

            {/* Priority Filter */}
            <div>
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                data-testid="filter-priority-select"
                className="w-full text-xs rounded-lg border border-slate-300 py-2 px-3 bg-white text-slate-700 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 cursor-pointer"
              >
                <option value="ALL">All Priorities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>

            {/* Sort Controls */}
            <div className="flex gap-2">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                data-testid="sort-by-select"
                className="flex-1 text-xs rounded-lg border border-slate-300 py-2 px-3 bg-white text-slate-700 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 cursor-pointer"
              >
                <option value="created_at">Date Created</option>
                <option value="priority">Priority</option>
                <option value="status">Status</option>
              </select>
              <button
                onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                title={`Sort ${sortOrder === 'asc' ? 'Descending' : 'Ascending'}`}
                className="p-2 border border-slate-300 rounded-lg hover:bg-slate-50 text-slate-600 transition-colors"
              >
                <ArrowUpDown className="h-4 w-4" />
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Content Area */}
      {loading ? (
        <div className="py-16 flex flex-col items-center justify-center">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-sm text-slate-500 font-medium">Loading work orders...</p>
        </div>
      ) : error ? (
        <Alert
          variant="error"
          title="Error Loading Work Orders"
        >
          {error}
        </Alert>
      ) : filteredOrders.length === 0 ? (
        <EmptyState
          icon={<ClipboardList className="h-10 w-10 text-slate-400" />}
          title="No Work Orders Found"
          description={
            searchQuery || statusFilter !== 'ALL' || priorityFilter !== 'ALL'
              ? 'No assigned work orders matched your selected filters or search terms.'
              : 'You have no assigned road maintenance work orders at this time.'
          }
        />
      ) : (
        <div className="space-y-3" data-testid="work-orders-list">
          {filteredOrders.map((wo) => (
            <Card
              key={wo.id}
              className={`border transition-all hover:shadow-sm ${
                wo.rework_required ? 'border-amber-300 bg-amber-50/20' : 'border-slate-200'
              }`}
            >
              <CardContent className="p-4 sm:p-5">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  {/* Left Info */}
                  <div className="space-y-2 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs text-slate-400 font-medium">
                        WO: {wo.id.slice(0, 8)}...
                      </span>
                      <PriorityBadge priority={wo.priority} />
                      <StatusBadge status={wo.status} />
                      {wo.rework_required && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">
                          <RotateCcw className="h-3 w-3" />
                          <span>Rework Required</span>
                        </span>
                      )}
                    </div>

                    <h3 className="text-base font-bold text-slate-900">{wo.title}</h3>
                    <p className="text-xs text-slate-600 line-clamp-2">{wo.description}</p>

                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 pt-1">
                      <div>
                        Location: <span className="font-semibold text-slate-700">{wo.road_name || 'Designated Road Section'}</span>
                      </div>
                      <div>
                        Dispatched: <span className="text-slate-700">{new Date(wo.created_at).toLocaleDateString()}</span>
                      </div>
                      <div>
                        Grievance ID: <span className="font-mono text-slate-700">{wo.grievance_id.slice(0, 8)}...</span>
                      </div>
                    </div>
                  </div>

                  {/* Right Actions & Progress */}
                  <div className="flex flex-col sm:items-end justify-between gap-3 shrink-0 sm:w-56 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-100">
                    {/* Progress Bar */}
                    <div className="w-full">
                      <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                        <span>Progress</span>
                        <span className="text-indigo-600">{wo.progress_percentage}%</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                        <div
                          className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${wo.progress_percentage}%` }}
                        />
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex items-center gap-2 w-full sm:w-auto">
                      {wo.status === 'ASSIGNED' && (
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => handleQuickStart(wo.id)}
                          disabled={actionLoadingId === wo.id}
                          className="text-xs gap-1 py-1.5 flex-1 sm:flex-initial"
                          data-testid={`quick-start-wo-${wo.id}`}
                        >
                          {actionLoadingId === wo.id ? (
                            <LoadingSpinner size="sm" />
                          ) : (
                            <Play className="h-3.5 w-3.5 text-blue-600" />
                          )}
                          <span>Start</span>
                        </Button>
                      )}

                      <Button
                        size="sm"
                        onClick={() => onSelectWorkOrder(wo.id)}
                        className="text-xs gap-1.5 py-1.5 flex-1 sm:flex-initial bg-indigo-600 hover:bg-indigo-700 text-white"
                        data-testid={`inspect-wo-btn-${wo.id}`}
                      >
                        <span>Inspect & Execute</span>
                        <ExternalLink className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
