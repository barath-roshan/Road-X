import React, { useState, useEffect } from 'react'
import {
  FileText,
  CheckCircle2,
  AlertOctagon,
  MessageSquare,
  PlusCircle,
  ArrowRight,
  Clock,
  MapPin,
  Sparkles,
  Loader2,
} from 'lucide-react'
import { citizenService } from '../../services/citizenService'
import { Card, CardContent } from '../../components/Card'
import { Button } from '../../components/Button'
import { Badge } from '../../components/Badge'
import { Alert } from '../../components/Alert'
import type { CitizenGrievanceItem, CitizenRoadOperation } from '../../types/citizen'
import type { GrievanceStatus } from '../../types/government'

interface CitizenOverviewTabProps {
  onNavigateToTab: (tab: 'overview' | 'report' | 'my-grievances' | 'road-operations' | 'chatbot') => void
  onSelectGrievance?: (id: string) => void
}

export const CitizenOverviewTab: React.FC<CitizenOverviewTabProps> = ({
  onNavigateToTab,
  onSelectGrievance,
}) => {
  const [grievances, setGrievances] = useState<CitizenGrievanceItem[]>([])
  const [operations, setOperations] = useState<CitizenRoadOperation[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadOverviewData()
  }, [])

  const loadOverviewData = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [grievanceData, opsData] = await Promise.all([
        citizenService.listGrievances({ limit: 10 }),
        citizenService.listRoadOperations({ active_only: true, limit: 5 }),
      ])
      setGrievances(grievanceData)
      setOperations(opsData)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve citizen overview data.'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }

  const totalSubmitted = grievances.length
  const totalInProgress = grievances.filter(
    (g) => g.status === 'UNDER_REVIEW' || g.status === 'IN_PROGRESS' || g.status === 'PENDING_VERIFICATION'
  ).length
  const totalResolved = grievances.filter((g) => g.status === 'RESOLVED').length
  const activeClosuresCount = operations.length

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
      })
    } catch {
      return isoString
    }
  }

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-blue-700 via-indigo-700 to-slate-900 text-white p-7 rounded-2xl shadow-sm relative overflow-hidden">
        <div className="relative z-10 max-w-2xl">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-white/20 text-white backdrop-blur-xs mb-3">
            <Sparkles className="w-3.5 h-3.5 text-blue-200" />
            Civic Road Safety & Grievance Portal
          </span>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Empowering Citizens for Safer, Smarter Roads
          </h1>
          <p className="mt-2 text-sm text-blue-100 leading-relaxed">
            Report road craters, waterlogging, or hazardous failures directly to municipal engineers. Track repair progress and detour advisories with real-time transparency.
          </p>

          <div className="flex flex-wrap gap-3 mt-5">
            <Button
              variant="primary"
              onClick={() => onNavigateToTab('report')}
              className="bg-white text-blue-700 hover:bg-blue-50 border-transparent shadow-xs font-semibold flex items-center gap-2"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Report a Problem</span>
            </Button>
            <Button
              variant="secondary"
              onClick={() => onNavigateToTab('road-operations')}
              className="bg-white/10 hover:bg-white/20 text-white border-white/20 backdrop-blur-xs flex items-center gap-2"
            >
              <AlertOctagon className="w-4 h-4 text-rose-300" />
              <span>View Road Closures</span>
            </Button>
          </div>
        </div>

        {/* Decorative background glow */}
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-radial from-blue-400/20 to-transparent pointer-events-none" />
      </div>

      {error && (
        <Alert variant="warning" title="Notice" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="hover:border-slate-300 transition-all">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Reports Logged</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">
                {isLoading ? <Loader2 className="w-5 h-5 animate-spin text-slate-400" /> : totalSubmitted}
              </h3>
              <p className="text-[11px] text-slate-400 mt-0.5">Submitted by you</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <FileText className="w-6 h-6" />
            </div>
          </CardContent>
        </Card>

        <Card className="hover:border-slate-300 transition-all">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">In Progress</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">
                {isLoading ? <Loader2 className="w-5 h-5 animate-spin text-slate-400" /> : totalInProgress}
              </h3>
              <p className="text-[11px] text-slate-400 mt-0.5">Under contractor repair</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <Clock className="w-6 h-6" />
            </div>
          </CardContent>
        </Card>

        <Card className="hover:border-slate-300 transition-all">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Resolved Reports</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">
                {isLoading ? <Loader2 className="w-5 h-5 animate-spin text-slate-400" /> : totalResolved}
              </h3>
              <p className="text-[11px] text-slate-400 mt-0.5">Verified & completed</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <CheckCircle2 className="w-6 h-6" />
            </div>
          </CardContent>
        </Card>

        <Card className="hover:border-slate-300 transition-all">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Road Advisories</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">
                {isLoading ? <Loader2 className="w-5 h-5 animate-spin text-slate-400" /> : activeClosuresCount}
              </h3>
              <p className="text-[11px] text-slate-400 mt-0.5">Active closures & detours</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
              <AlertOctagon className="w-6 h-6" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Action Navigation Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <button
          type="button"
          onClick={() => onNavigateToTab('report')}
          className="p-5 bg-white rounded-xl border border-slate-200 hover:border-blue-400 hover:shadow-xs transition-all text-left flex items-start gap-4 group"
        >
          <div className="p-3 rounded-lg bg-blue-50 text-blue-600 group-hover:bg-blue-600 group-hover:text-white transition-colors">
            <PlusCircle className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900 group-hover:text-blue-700 transition-colors">
              Report Road Problem
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Submit damage photos, GPS coordinates, and describe road crater hazards.
            </p>
          </div>
        </button>

        <button
          type="button"
          onClick={() => onNavigateToTab('my-grievances')}
          className="p-5 bg-white rounded-xl border border-slate-200 hover:border-blue-400 hover:shadow-xs transition-all text-left flex items-start gap-4 group"
        >
          <div className="p-3 rounded-lg bg-indigo-50 text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900 group-hover:text-indigo-700 transition-colors">
              Track My Grievances
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              View milestone timeline, ML analysis, and contractor repair completion.
            </p>
          </div>
        </button>

        <button
          type="button"
          onClick={() => onNavigateToTab('chatbot')}
          className="p-5 bg-white rounded-xl border border-slate-200 hover:border-blue-400 hover:shadow-xs transition-all text-left flex items-start gap-4 group"
        >
          <div className="p-3 rounded-lg bg-purple-50 text-purple-600 group-hover:bg-purple-600 group-hover:text-white transition-colors">
            <MessageSquare className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900 group-hover:text-purple-700 transition-colors">
              Ask RoadX AI Assistant
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Inquire about road closures, bylaws, and municipal defect resolution standards.
            </p>
          </div>
        </button>
      </div>

      {/* Split Section: Recent Reports & Active Road Closures */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Recent Grievances (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-600" />
              Recent Reports
            </h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onNavigateToTab('my-grievances')}
              className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
            >
              <span>View All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Button>
          </div>

          {isLoading ? (
            <div className="p-8 text-center bg-white rounded-xl border border-slate-200 text-xs text-slate-400">
              Loading recent reports...
            </div>
          ) : grievances.length === 0 ? (
            <div className="p-8 text-center bg-white rounded-xl border border-dashed border-slate-200">
              <p className="text-sm font-medium text-slate-700">No reports logged yet</p>
              <p className="text-xs text-slate-400 mt-1">
                Notice a pothole or waterlogging on your commute? Submit a report now.
              </p>
              <Button
                variant="primary"
                size="sm"
                onClick={() => onNavigateToTab('report')}
                className="mt-3 text-xs"
              >
                Report a Defect
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {grievances.slice(0, 4).map((g) => (
                <div
                  key={g.id}
                  onClick={() => {
                    if (onSelectGrievance) onSelectGrievance(g.id)
                    onNavigateToTab('my-grievances')
                  }}
                  className="p-4 bg-white rounded-xl border border-slate-200 hover:border-blue-300 hover:shadow-xs transition-all cursor-pointer flex items-center justify-between gap-3"
                >
                  <div className="min-w-0 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-900 text-sm truncate">{g.issue_category}</span>
                      {getStatusBadge(g.status)}
                    </div>
                    <p className="text-xs text-slate-500 truncate">{g.description}</p>
                    <div className="flex items-center gap-3 text-[11px] text-slate-400">
                      <span>{formatDate(g.created_at)}</span>
                      <span className="font-mono">{g.latitude.toFixed(3)}, {g.longitude.toFixed(3)}</span>
                    </div>
                  </div>
                  <ArrowRight className="w-4 h-4 text-slate-400 shrink-0" />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Active Traffic Advisories (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <AlertOctagon className="w-4 h-4 text-rose-600" />
              Active Road Closures
            </h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onNavigateToTab('road-operations')}
              className="text-xs text-rose-600 hover:text-rose-800 flex items-center gap-1"
            >
              <span>All Advisories</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Button>
          </div>

          {isLoading ? (
            <div className="p-8 text-center bg-white rounded-xl border border-slate-200 text-xs text-slate-400">
              Checking advisories...
            </div>
          ) : operations.length === 0 ? (
            <div className="p-8 text-center bg-white rounded-xl border border-slate-200 text-xs text-slate-500">
              <CheckCircle2 className="w-6 h-6 text-emerald-500 mx-auto mb-2" />
              No active road closures or detour restrictions currently reported.
            </div>
          ) : (
            <div className="space-y-3">
              {operations.slice(0, 3).map((op) => (
                <div
                  key={op.id}
                  onClick={() => onNavigateToTab('road-operations')}
                  className="p-4 bg-white rounded-xl border border-slate-200 hover:border-rose-300 hover:shadow-xs transition-all cursor-pointer space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-slate-900 truncate">{op.title}</h4>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-rose-50 text-rose-700">
                      {op.operation_type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  {op.road_name && (
                    <p className="text-[11px] text-slate-600 flex items-center gap-1">
                      <MapPin className="w-3 h-3 text-slate-400" />
                      <span>{op.road_name}</span>
                    </p>
                  )}
                  {op.alternative_route_name && (
                    <p className="text-[11px] text-blue-600 font-medium">
                      Detour: {op.alternative_route_name}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
