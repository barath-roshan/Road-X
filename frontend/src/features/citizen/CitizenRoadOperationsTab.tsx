import React, { useState, useEffect } from 'react'
import {
  AlertOctagon,
  CornerUpRight,
  Clock,
  Calendar,
  RefreshCw,
  Search,
  MapPin,
  Loader2,
} from 'lucide-react'
import { citizenService } from '../../services/citizenService'
import { Card, CardContent } from '../../components/Card'
import { Button } from '../../components/Button'
import { Badge } from '../../components/Badge'
import { Alert } from '../../components/Alert'
import { EmptyState } from '../../components/EmptyState'
import type { CitizenRoadOperation } from '../../types/citizen'
import type { RoadOperationStatus, RoadOperationType } from '../../types/government'

export const CitizenRoadOperationsTab: React.FC = () => {
  const [operations, setOperations] = useState<CitizenRoadOperation[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('ACTIVE')
  const [typeFilter, setTypeFilter] = useState<string>('ALL')
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    loadRoadOperations()
  }, [statusFilter, typeFilter])

  const loadRoadOperations = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const params: {
        status?: RoadOperationStatus
        operation_type?: RoadOperationType
        active_only?: boolean
      } = {}

      if (statusFilter === 'ACTIVE') {
        params.status = 'ACTIVE'
        params.active_only = true
      } else if (statusFilter !== 'ALL') {
        params.status = statusFilter as RoadOperationStatus
        params.active_only = false
      } else {
        params.active_only = false
      }

      if (typeFilter !== 'ALL') {
        params.operation_type = typeFilter as RoadOperationType
      }

      const data = await citizenService.listRoadOperations(params)
      setOperations(data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve road operations.'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }

  const filteredOperations = operations.filter((op) => {
    if (!searchQuery.trim()) return true
    const q = searchQuery.toLowerCase()
    return (
      op.title.toLowerCase().includes(q) ||
      op.description.toLowerCase().includes(q) ||
      (op.road_name && op.road_name.toLowerCase().includes(q)) ||
      (op.alternative_route_name && op.alternative_route_name.toLowerCase().includes(q)) ||
      op.reason.toLowerCase().includes(q)
    )
  })

  const getStatusBadge = (status: RoadOperationStatus) => {
    switch (status) {
      case 'ACTIVE':
        return <Badge variant="danger">Active Closure</Badge>
      case 'PLANNED':
        return <Badge variant="warning">Scheduled</Badge>
      case 'COMPLETED':
        return <Badge variant="success">Completed</Badge>
      case 'CANCELLED':
        return <Badge variant="default">Cancelled</Badge>
      default:
        return <Badge variant="default">{status}</Badge>
    }
  }

  const getTypeBadge = (type: RoadOperationType) => {
    const formatted = type.replace(/_/g, ' ')
    switch (type) {
      case 'ROAD_CLOSURE':
        return <span className="text-xs font-semibold px-2 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200">{formatted}</span>
      case 'DETOUR':
        return <span className="text-xs font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">{formatted}</span>
      case 'LANE_RESTRICTION':
        return <span className="text-xs font-semibold px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">{formatted}</span>
      case 'HAZARD_BLOCK':
        return <span className="text-xs font-semibold px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200">{formatted}</span>
      default:
        return <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">{formatted}</span>
    }
  }

  const formatDateTime = (isoString?: string | null) => {
    if (!isoString) return '—'
    try {
      return new Date(isoString).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      })
    } catch {
      return isoString
    }
  }

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-xl font-bold text-slate-900">Road Operations & Traffic Advisories</h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200">
              Public Advisory
            </span>
          </div>
          <p className="text-sm text-slate-500">
            Real-time municipal road closures, maintenance restrictions, and verified detour routes for city commuters.
          </p>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={loadRoadOperations}
          disabled={isLoading}
          className="flex items-center gap-1.5 self-start sm:self-auto text-slate-600 hover:text-slate-900"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Advisories</span>
        </Button>
      </div>

      {error && (
        <Alert variant="error" title="Advisory Notice" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Filters and Search */}
      <Card>
        <CardContent className="p-4">
          <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
            <div className="sm:col-span-5 relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search road name, title, or detour instructions..."
                className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div className="sm:col-span-4 relative">
              <select
                aria-label="Filter road operations by status"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-slate-700"
              >
                <option value="ACTIVE">Active Closures & Restrictions</option>
                <option value="PLANNED">Scheduled Upcoming Operations</option>
                <option value="ALL">All Operational Statuses</option>
                <option value="COMPLETED">Completed</option>
                <option value="CANCELLED">Cancelled</option>
              </select>
            </div>

            <div className="sm:col-span-3 relative">
              <select
                aria-label="Filter road operations by type"
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-slate-700"
              >
                <option value="ALL">All Operation Types</option>
                <option value="ROAD_CLOSURE">Road Closure</option>
                <option value="DETOUR">Detour</option>
                <option value="LANE_RESTRICTION">Lane Restriction</option>
                <option value="HAZARD_BLOCK">Hazard Block</option>
                <option value="MAINTENANCE_WORK">Maintenance Work</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Operations List */}
      {isLoading ? (
        <div className="py-20 text-center bg-white rounded-xl border border-slate-200">
          <Loader2 className="w-8 h-8 animate-spin text-rose-600 mx-auto mb-2" />
          <p className="text-sm text-slate-500">Checking current traffic advisories and municipal road operations...</p>
        </div>
      ) : filteredOperations.length === 0 ? (
        <EmptyState
          icon={<AlertOctagon className="w-10 h-10 text-slate-400" />}
          title="No Active Road Advisories"
          description={
            statusFilter === 'ACTIVE'
              ? 'All municipal roadways in your monitored sectors are currently open with no active closures or detour advisories reported.'
              : 'No road operations matched your filter criteria.'
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-5">
          {filteredOperations.map((op) => (
            <Card
              key={op.id}
              className={`border-l-4 ${
                op.status === 'ACTIVE' ? 'border-l-rose-500' : 'border-l-blue-500'
              } hover:shadow-xs transition-shadow`}
            >
              <CardContent className="p-6 space-y-4">
                {/* Title & Status Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <h2 className="text-base font-bold text-slate-900">{op.title}</h2>
                      {getStatusBadge(op.status)}
                      {getTypeBadge(op.operation_type)}
                    </div>
                    {op.road_name && (
                      <p className="text-xs text-slate-500 flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5 text-slate-400" />
                        <span>Affected Roadway: <strong className="text-slate-700">{op.road_name}</strong></span>
                      </p>
                    )}
                  </div>

                  {/* Schedule */}
                  <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200/80 text-xs text-slate-600 shrink-0 space-y-1">
                    <div className="flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-blue-600" />
                      <span>Start: <strong>{formatDateTime(op.start_time)}</strong></span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-amber-600" />
                      <span>Expected End: <strong>{formatDateTime(op.expected_end_time)}</strong></span>
                    </div>
                  </div>
                </div>

                {/* Description & Reason */}
                <div className="space-y-1 text-sm text-slate-700 bg-slate-50/60 p-3.5 rounded-lg border border-slate-200/60 leading-relaxed">
                  <p>{op.description}</p>
                  <p className="text-xs text-slate-500 pt-1">
                    <strong>Reason for Notice:</strong> {op.reason}
                  </p>
                </div>

                {/* Alternative Detour Route Section */}
                {(op.alternative_route_name || op.alternative_route_instructions) && (
                  <div className="bg-blue-50/40 p-4 rounded-xl border border-blue-200/80 space-y-2">
                    <div className="flex items-center gap-2 text-blue-900 font-semibold text-xs uppercase tracking-wider">
                      <CornerUpRight className="w-4 h-4 text-blue-600" />
                      <span>Recommended Detour Route</span>
                      {op.alternative_distance_km !== null && op.alternative_distance_km !== undefined && (
                        <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 ml-auto lowercase">
                          +{op.alternative_distance_km.toFixed(1)} km detour
                        </span>
                      )}
                    </div>

                    {op.alternative_route_name && (
                      <h4 className="text-sm font-semibold text-slate-800">
                        {op.alternative_route_name}
                      </h4>
                    )}

                    {op.alternative_route_instructions && (
                      <p className="text-xs text-slate-600 leading-relaxed">
                        {op.alternative_route_instructions}
                      </p>
                    )}

                    {op.alternative_road_name && (
                      <p className="text-[11px] text-blue-700 font-medium">
                        Diverts traffic via: {op.alternative_road_name}
                      </p>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
