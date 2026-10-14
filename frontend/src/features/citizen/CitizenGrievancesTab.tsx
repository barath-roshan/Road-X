import React, { useState, useEffect, useMemo } from 'react'
import {
  FileText,
  Search,
  RefreshCw,
  MapPin,
  Calendar,
  ArrowRight,
  PlusCircle,
  Loader2,
} from 'lucide-react'
import { citizenService } from '../../services/citizenService'
import { Card, CardContent } from '../../components/Card'
import { Button } from '../../components/Button'
import { Badge } from '../../components/Badge'
import { Alert } from '../../components/Alert'
import { EmptyState } from '../../components/EmptyState'
import { CitizenGrievanceDetailModal } from './CitizenGrievanceDetailModal'
import type { CitizenGrievanceItem } from '../../types/citizen'
import type { GrievanceStatus } from '../../types/government'

interface CitizenGrievancesTabProps {
  onNavigateToReport?: () => void
  initialSelectedId?: string | null
}

export const CitizenGrievancesTab: React.FC<CitizenGrievancesTabProps> = ({
  onNavigateToReport,
  initialSelectedId,
}) => {
  const [grievances, setGrievances] = useState<CitizenGrievanceItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters & Search
  const [statusFilter, setStatusFilter] = useState<string>('ALL')
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL')
  const [searchQuery, setSearchQuery] = useState('')

  // Modal State
  const [selectedGrievanceId, setSelectedGrievanceId] = useState<string | null>(initialSelectedId || null)
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(Boolean(initialSelectedId))

  useEffect(() => {
    loadGrievances()
  }, [statusFilter, categoryFilter])

  const loadGrievances = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const params: { status?: GrievanceStatus; issue_category?: string } = {}
      if (statusFilter !== 'ALL') {
        params.status = statusFilter as GrievanceStatus
      }
      if (categoryFilter !== 'ALL') {
        params.issue_category = categoryFilter
      }

      const data = await citizenService.listGrievances(params)
      setGrievances(data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve your grievance records.'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }

  const handleOpenDetail = (id: string) => {
    setSelectedGrievanceId(id)
    setIsDetailModalOpen(true)
  }

  const handleCloseDetail = () => {
    setIsDetailModalOpen(false)
    setSelectedGrievanceId(null)
  }

  // Client-side search filtering on the citizen's own retrieved items
  const filteredGrievances = useMemo(() => {
    if (!searchQuery.trim()) return grievances
    const q = searchQuery.toLowerCase()
    return grievances.filter(
      (g) =>
        g.id.toLowerCase().includes(q) ||
        g.description.toLowerCase().includes(q) ||
        g.issue_category.toLowerCase().includes(q) ||
        (g.road_id && g.road_id.toLowerCase().includes(q))
    )
  }, [grievances, searchQuery])

  const getStatusBadge = (status: GrievanceStatus) => {
    switch (status) {
      case 'SUBMITTED':
        return <Badge variant="default">Submitted</Badge>
      case 'UNDER_REVIEW':
        return <Badge variant="warning">Under Review</Badge>
      case 'IN_PROGRESS':
        return <Badge variant="officer">In Progress</Badge>
      case 'PENDING_VERIFICATION':
        return <Badge variant="contractor">Pending Verification</Badge>
      case 'RESOLVED':
        return <Badge variant="success">Resolved</Badge>
      case 'REJECTED':
        return <Badge variant="danger">Rejected</Badge>
      default:
        return <Badge variant="default">{status}</Badge>
    }
  }

  const formatDate = (isoString: string) => {
    try {
      return new Date(isoString).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
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
            <h1 className="text-xl font-bold text-slate-900">My Grievance Reports</h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
              {grievances.length} Registered
            </span>
          </div>
          <p className="text-sm text-slate-500">
            Track road defects you have reported, inspect inspection findings, contractor progress, and repair resolution.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={loadGrievances}
            disabled={isLoading}
            className="flex items-center gap-1.5 text-slate-600 hover:text-slate-900"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </Button>

          {onNavigateToReport && (
            <Button
              variant="primary"
              size="sm"
              onClick={onNavigateToReport}
              className="flex items-center gap-1.5 shadow-xs"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Report Problem</span>
            </Button>
          )}
        </div>
      </div>

      {error && (
        <Alert variant="error" title="Data Retrieval Notice" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Filter and Search Bar */}
      <Card>
        <CardContent className="p-4">
          <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
            {/* Search Input */}
            <div className="sm:col-span-5 relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by description, report ID..."
                className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Status Filter */}
            <div className="sm:col-span-4 relative">
              <select
                aria-label="Filter grievances by lifecycle status"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-slate-700"
              >
                <option value="ALL">All Statuses</option>
                <option value="SUBMITTED">Submitted</option>
                <option value="UNDER_REVIEW">Under Review</option>
                <option value="IN_PROGRESS">In Progress</option>
                <option value="PENDING_VERIFICATION">Pending Verification</option>
                <option value="RESOLVED">Resolved</option>
                <option value="REJECTED">Rejected</option>
              </select>
            </div>

            {/* Category Filter */}
            <div className="sm:col-span-3 relative">
              <select
                aria-label="Filter grievances by defect category"
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-slate-700"
              >
                <option value="ALL">All Categories</option>
                <option value="POTHOLE">Potholes</option>
                <option value="WATERLOGGING">Waterlogging</option>
                <option value="STREETLIGHT">Streetlights</option>
                <option value="ROAD_CRACK">Road Cracks</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Grievance Records */}
      {isLoading ? (
        <div className="py-20 text-center bg-white rounded-xl border border-slate-200">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-2" />
          <p className="text-sm text-slate-500">Retrieving your reported grievances...</p>
        </div>
      ) : filteredGrievances.length === 0 ? (
        <EmptyState
          icon={<FileText className="w-10 h-10 text-slate-400" />}
          title={grievances.length === 0 ? 'No Grievances Reported Yet' : 'No Matching Reports Found'}
          description={
            grievances.length === 0
              ? 'You have not submitted any road defect reports yet. Help improve our roads by reporting potholes, waterlogging, or damaged streetlights.'
              : 'Try clearing your search query or adjusting your status and category filters to find existing reports.'
          }
          action={
            grievances.length === 0 && onNavigateToReport ? (
              <Button variant="primary" onClick={onNavigateToReport} className="mt-2">
                Report a Defect Now
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {filteredGrievances.map((item) => (
            <Card
              key={item.id}
              className="hover:border-slate-300 transition-all hover:shadow-xs group"
            >
              <CardContent className="p-5">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-2 flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-bold text-slate-900 text-base">{item.issue_category}</span>
                      {getStatusBadge(item.status)}
                      <span className="text-xs text-slate-400 font-mono">#{item.id.slice(0, 8)}</span>
                    </div>

                    <p className="text-sm text-slate-700 line-clamp-2 leading-relaxed">
                      {item.description}
                    </p>

                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 pt-1">
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5 text-blue-600" />
                        <span className="font-mono">{item.latitude.toFixed(4)}, {item.longitude.toFixed(4)}</span>
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        <span>Submitted: {formatDate(item.created_at)}</span>
                      </span>
                      {item.road_id && (
                        <span className="font-mono text-slate-500">
                          Road: {item.road_id}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="shrink-0 flex items-center justify-end">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleOpenDetail(item.id)}
                      className="flex items-center gap-1.5 group-hover:border-blue-400 group-hover:text-blue-700 transition-colors"
                    >
                      <span>View Details & Timeline</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Detail Modal */}
      <CitizenGrievanceDetailModal
        grievanceId={selectedGrievanceId}
        isOpen={isDetailModalOpen}
        onClose={handleCloseDetail}
      />
    </div>
  )
}
