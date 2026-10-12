import React, { useEffect, useState } from 'react'
import {
  Shield,
  MapPin,
  Clock,
  User,
  HardHat,
  FileText,
  Activity,
  Calendar,
  Send,
  ExternalLink,
} from 'lucide-react'
import { Modal } from '../../components/Modal'
import { Button } from '../../components/Button'
import { Input } from '../../components/Input'
import { Alert } from '../../components/Alert'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { Badge } from '../../components/Badge'
import { Card, CardHeader, CardTitle, CardContent } from '../../components/Card'
import { governmentService } from '../../services/governmentService'
import type {
  GovernmentDashboardGrievanceDetail,
  GovernmentDashboardContractorSummary,
  ReviewDecision,
} from '../../types/government'

interface GovernmentGrievanceDetailModalProps {
  grievanceId: string | null
  onClose: () => void
  onGrievanceUpdated?: () => void
}

export const GovernmentGrievanceDetailModal: React.FC<GovernmentGrievanceDetailModalProps> = ({
  grievanceId,
  onClose,
  onGrievanceUpdated,
}) => {
  const [detail, setDetail] = useState<GovernmentDashboardGrievanceDetail | null>(null)
  const [contractors, setContractors] = useState<GovernmentDashboardContractorSummary[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)

  // Review decision form state
  const [reviewDecision, setReviewDecision] = useState<ReviewDecision>('ACCEPT')
  const [reviewReason, setReviewReason] = useState<string>('')
  const [reviewNotes, setReviewNotes] = useState<string>('')
  const [isSubmittingReview, setIsSubmittingReview] = useState<boolean>(false)

  // Work order creation form state
  const [woTitle, setWoTitle] = useState<string>('')
  const [woDescription, setWoDescription] = useState<string>('')
  const [woPriority, setWoPriority] = useState<string>('MEDIUM')
  const [woContractorId, setWoContractorId] = useState<string>('')
  const [isSubmittingWo, setIsSubmittingWo] = useState<boolean>(false)

  const fetchDetail = async (id: string) => {
    setIsLoading(true)
    setError(null)
    setActionSuccess(null)
    try {
      const data = await governmentService.getGrievanceDetail(id)
      setDetail(data)
      // Pre-fill work order title if blank
      setWoTitle(`Repair ${data.issue_category}: ${data.road_name || 'Road Segment'}`)
      setWoDescription(`Address reported hazard: ${data.description}`)
      if (data.ml_analysis?.maintenance_priority?.priority_level) {
        setWoPriority(String(data.ml_analysis.maintenance_priority.priority_level).toUpperCase())
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load grievance details.')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchContractors = async () => {
    try {
      const list = await governmentService.listContractors()
      setContractors(list)
      if (list.length > 0 && !woContractorId) {
        setWoContractorId(list[0].contractor_id)
      }
    } catch {
      // Non-fatal if contractors fail to load
    }
  }

  useEffect(() => {
    if (grievanceId) {
      fetchDetail(grievanceId)
      fetchContractors()
      setReviewReason('')
      setReviewNotes('')
    } else {
      setDetail(null)
    }
  }, [grievanceId])

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!grievanceId) return

    if (reviewDecision === 'REJECT' && !reviewReason.trim()) {
      setError('A rejection reason is required when rejecting a grievance.')
      return
    }

    setIsSubmittingReview(true)
    setError(null)
    setActionSuccess(null)

    try {
      await governmentService.submitReview(grievanceId, {
        decision: reviewDecision,
        reason: reviewDecision === 'REJECT' ? reviewReason.trim() : undefined,
        notes: reviewNotes.trim() || undefined,
      })
      setActionSuccess(
        `Grievance successfully ${reviewDecision === 'ACCEPT' ? 'accepted (under review)' : 'rejected'}.`
      )
      await fetchDetail(grievanceId)
      onGrievanceUpdated?.()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to submit review decision.')
    } finally {
      setIsSubmittingReview(false)
    }
  }

  const handleCreateWorkOrder = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!grievanceId) return

    if (!woTitle.trim() || !woDescription.trim()) {
      setError('Work order title and engineering description are required.')
      return
    }

    setIsSubmittingWo(true)
    setError(null)
    setActionSuccess(null)

    try {
      await governmentService.createWorkOrder(grievanceId, {
        title: woTitle.trim(),
        description: woDescription.trim(),
        priority: woPriority,
        assigned_contractor_id: woContractorId || null,
      })
      setActionSuccess('Work order successfully created and assigned!')
      await fetchDetail(grievanceId)
      onGrievanceUpdated?.()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create work order.')
    } finally {
      setIsSubmittingWo(false)
    }
  }

  const getStatusColor = (status: string): 'default' | 'officer' | 'warning' | 'danger' | 'success' => {
    switch (status) {
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
    <Modal
      isOpen={Boolean(grievanceId)}
      onClose={onClose}
      title={detail ? `Case: ${detail.issue_category}` : 'Grievance Case Inspection'}
      description={detail ? `Grievance ID: ${detail.id}` : undefined}
      maxWidth="4xl"
    >
      {isLoading ? (
        <div className="py-12 flex justify-center">
          <LoadingSpinner size="lg" message="Retrieving grievance dossier..." />
        </div>
      ) : error && !detail ? (
        <div className="space-y-4 py-4">
          <Alert variant="error" title="Error" onDismiss={() => setError(null)}>
            {error}
          </Alert>
          <Button variant="outline" size="sm" onClick={() => grievanceId && fetchDetail(grievanceId)}>
            Retry
          </Button>
        </div>
      ) : detail ? (
        <div className="space-y-6">
          {actionSuccess && (
            <Alert
              variant="success"
              title="Action Succeeded"
              onDismiss={() => setActionSuccess(null)}
            >
              {actionSuccess}
            </Alert>
          )}

          {error && (
            <Alert variant="error" title="Action Error" onDismiss={() => setError(null)}>
              {error}
            </Alert>
          )}

          {/* Top Status & Core Identifiers Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-slate-50 rounded-xl border border-slate-200">
            <div className="flex items-center gap-3">
              <Badge variant={getStatusColor(detail.status)}>{detail.status.replace('_', ' ')}</Badge>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                {detail.issue_category}
              </span>
            </div>
            <div className="flex items-center gap-4 text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <Calendar className="h-3.5 w-3.5 text-slate-400" />
                Logged: {new Date(detail.created_at).toLocaleString()}
              </span>
            </div>
          </div>

          {/* Citizen & Location Two-Column */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Citizen Details */}
            <div className="p-4 bg-white rounded-xl border border-slate-200 space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <User className="h-3.5 w-3.5 text-slate-500" />
                Citizen Reporter
              </h4>
              <p className="text-sm font-semibold text-slate-900">{detail.citizen_name || 'Anonymous Citizen'}</p>
              {detail.citizen_email && (
                <p className="text-xs text-slate-500">{detail.citizen_email}</p>
              )}
              <p className="text-[11px] font-mono text-slate-400">ID: {detail.citizen_id}</p>
            </div>

            {/* Road Location */}
            <div className="p-4 bg-white rounded-xl border border-slate-200 space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5 text-slate-500" />
                Location & Road Segment
              </h4>
              <p className="text-sm font-semibold text-slate-900">{detail.road_name || 'Unassigned Road'}</p>
              {detail.road_code && (
                <p className="text-xs text-slate-500">Code: {detail.road_code}</p>
              )}
              <p className="text-[11px] font-mono text-slate-400 flex items-center gap-1">
                {detail.latitude.toFixed(6)}, {detail.longitude.toFixed(6)}
                <a
                  href={`https://www.google.com/maps/search/?api=1&query=${detail.latitude},${detail.longitude}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center text-indigo-600 hover:text-indigo-800 ml-1.5"
                >
                  <ExternalLink className="h-3 w-3" />
                </a>
              </p>
            </div>
          </div>

          {/* Description Text */}
          <div className="p-4 bg-white rounded-xl border border-slate-200 space-y-1.5">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Citizen Description
            </h4>
            <p className="text-sm text-slate-700 leading-relaxed">{detail.description}</p>
          </div>

          {/* Evidence Attachments */}
          {detail.evidence_items.length > 0 && (
            <div className="p-4 bg-white rounded-xl border border-slate-200 space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5 text-slate-500" />
                Attached Evidence Files ({detail.evidence_items.length})
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {detail.evidence_items.map((ev) => (
                  <div key={ev.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1">
                    <p className="font-semibold text-slate-800 truncate" title={ev.file_name}>
                      {ev.file_name}
                    </p>
                    <p className="text-[11px] text-slate-400">{ev.file_type}</p>
                    {ev.file_size_bytes && (
                      <p className="text-[11px] text-slate-400 font-mono">
                        {(ev.file_size_bytes / 1024).toFixed(1)} KB
                      </p>
                    )}
                    <p className="text-[10px] text-slate-400">
                      Uploaded {new Date(ev.uploaded_at).toLocaleDateString()}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ML Analysis Decision Support */}
          {detail.ml_analysis && (
            <Card className="border-indigo-100 bg-indigo-50/30">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-bold text-indigo-950 flex items-center gap-2">
                  <Activity className="h-4 w-4 text-indigo-600" />
                  ML Decision Support & Predictive Risk Engine
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-xs">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3 bg-white rounded-lg border border-indigo-100">
                    <span className="text-slate-400 font-medium">Pipeline Status</span>
                    <p className="font-bold text-slate-900 mt-0.5">{detail.ml_analysis.overall_status || 'READY'}</p>
                  </div>
                  <div className="p-3 bg-white rounded-lg border border-indigo-100">
                    <span className="text-slate-400 font-medium">Maintenance Priority</span>
                    <p className="font-bold text-indigo-600 mt-0.5">
                      {detail.ml_analysis.maintenance_priority?.priority_level || 'MEDIUM'}
                    </p>
                  </div>
                  <div className="p-3 bg-white rounded-lg border border-indigo-100">
                    <span className="text-slate-400 font-medium">Damage Severity</span>
                    <p className="font-bold text-slate-900 mt-0.5">
                      {detail.ml_analysis.severity_prediction?.severity_level || 'NORMAL'}
                    </p>
                  </div>
                  <div className="p-3 bg-white rounded-lg border border-indigo-100">
                    <span className="text-slate-400 font-medium">Est. Days to Failure</span>
                    <p className="font-bold text-slate-900 mt-0.5">
                      {detail.ml_analysis.time_to_failure?.estimated_days != null
                        ? `${detail.ml_analysis.time_to_failure.estimated_days} days`
                        : 'N/A'}
                    </p>
                  </div>
                </div>

                {/* ML Reasons List */}
                {detail.ml_analysis.maintenance_priority?.reasons && (
                  <div className="space-y-1.5 bg-white p-3 rounded-lg border border-indigo-100">
                    <span className="font-semibold text-slate-700">Predictive Prioritization Rationale:</span>
                    <ul className="list-disc list-inside space-y-0.5 text-slate-600 text-[11px]">
                      {detail.ml_analysis.maintenance_priority.reasons.map((r: string, idx: number) => (
                        <li key={idx}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Existing Work Order Section */}
          {detail.work_order && (
            <Card className="border-slate-200">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <HardHat className="h-4 w-4 text-amber-600" />
                  Assigned Maintenance Work Order
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                <div className="flex flex-wrap items-center justify-between gap-2 p-3 bg-slate-50 rounded-lg">
                  <div>
                    <h5 className="font-bold text-slate-900">{detail.work_order.title}</h5>
                    <p className="text-slate-500 mt-0.5">{detail.work_order.description}</p>
                  </div>
                  <Badge variant={getStatusColor(detail.work_order.status)}>
                    {detail.work_order.status.replace('_', ' ')}
                  </Badge>
                </div>

                {detail.assigned_contractor && (
                  <div className="p-3 bg-amber-50/50 rounded-lg border border-amber-100">
                    <span className="text-slate-500 font-medium">Contractor: </span>
                    <span className="font-semibold text-slate-800">{detail.assigned_contractor.name}</span>
                    <span className="text-slate-400 ml-2">({detail.assigned_contractor.email})</span>
                  </div>
                )}

                {/* Progress History */}
                {detail.progress_history.length > 0 && (
                  <div className="space-y-2">
                    <span className="font-semibold text-slate-700">Contractor Progress History:</span>
                    <div className="space-y-1.5 max-h-36 overflow-y-auto">
                      {detail.progress_history.map((p) => (
                        <div key={p.id} className="p-2 bg-slate-50 rounded border border-slate-100 flex justify-between items-center text-[11px]">
                          <div>
                            <span className="font-bold text-indigo-700">{p.progress_percentage}% completed</span>
                            {p.notes && <span className="text-slate-600 ml-2">— {p.notes}</span>}
                          </div>
                          <span className="text-slate-400 font-mono">
                            {new Date(p.created_at).toLocaleDateString()}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Workflow Audit Timeline */}
          {detail.timeline.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-slate-500" />
                Audit Workflow History ({detail.timeline.length} events)
              </h4>
              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {detail.timeline.map((ev) => (
                  <div key={ev.id} className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 text-xs flex items-start justify-between gap-3">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-800">{ev.event_type}</span>
                        {ev.actor_role && (
                          <span className="text-[10px] bg-slate-200 text-slate-700 px-1.5 py-0.2 rounded font-mono">
                            {ev.actor_role}
                          </span>
                        )}
                      </div>
                      {ev.notes && <p className="text-slate-600 text-[11px]">{ev.notes}</p>}
                      {ev.old_status && ev.new_status && (
                        <p className="text-[10px] text-slate-400 font-mono">
                          {ev.old_status} → {ev.new_status}
                        </p>
                      )}
                    </div>
                    <span className="text-[10px] text-slate-400 whitespace-nowrap">
                      {new Date(ev.created_at).toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Government Action Forms (Review & Dispatch) */}
          {detail.status !== 'RESOLVED' && detail.status !== 'REJECTED' && (
            <div className="pt-4 border-t border-slate-200 space-y-6">
              {/* Form 1: Review Decision (for SUBMITTED / UNDER_REVIEW) */}
              {(detail.status === 'SUBMITTED' || detail.status === 'UNDER_REVIEW') && (
                <form onSubmit={handleReviewSubmit} noValidate className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                    <Shield className="h-4 w-4 text-indigo-600" />
                    1. Submit Official Officer Review Decision
                  </h4>

                  <div className="flex items-center space-x-4">
                    <label className="flex items-center space-x-2 text-xs font-medium text-slate-700 cursor-pointer">
                      <input
                        type="radio"
                        name="reviewDecision"
                        value="ACCEPT"
                        checked={reviewDecision === 'ACCEPT'}
                        onChange={() => setReviewDecision('ACCEPT')}
                        className="text-indigo-600 focus:ring-indigo-500"
                      />
                      <span>Accept Grievance (Advance to Under Review)</span>
                    </label>

                    <label className="flex items-center space-x-2 text-xs font-medium text-slate-700 cursor-pointer">
                      <input
                        type="radio"
                        name="reviewDecision"
                        value="REJECT"
                        checked={reviewDecision === 'REJECT'}
                        onChange={() => setReviewDecision('REJECT')}
                        className="text-rose-600 focus:ring-rose-500"
                      />
                      <span className="text-rose-600">Reject Grievance</span>
                    </label>
                  </div>

                  {reviewDecision === 'REJECT' && (
                    <Input
                      label="Rejection Reason (Required)"
                      value={reviewReason}
                      onChange={(e) => setReviewReason(e.target.value)}
                      placeholder="State reason for rejecting grievance (e.g. Duplicate report, invalid jurisdiction)..."
                      required
                    />
                  )}

                  <Input
                    label="Administrative Notes (Optional)"
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                    placeholder="Officer internal review notes..."
                  />

                  <Button
                    type="submit"
                    size="sm"
                    disabled={isSubmittingReview}
                    className={reviewDecision === 'REJECT' ? 'bg-rose-600 hover:bg-rose-700 text-white' : 'bg-indigo-600 hover:bg-indigo-700 text-white'}
                  >
                    {isSubmittingReview ? (
                      <LoadingSpinner size="sm" />
                    ) : (
                      <>
                        <Send className="h-3.5 w-3.5 mr-1.5" />
                        Confirm Review ({reviewDecision})
                      </>
                    )}
                  </Button>
                </form>
              )}

              {/* Form 2: Create & Assign Work Order */}
              {!detail.work_order && (
                <form onSubmit={handleCreateWorkOrder} noValidate className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                    <HardHat className="h-4 w-4 text-amber-600" />
                    2. Commission Maintenance Work Order & Assign Contractor
                  </h4>

                  <Input
                    label="Work Order Title"
                    value={woTitle}
                    onChange={(e) => setWoTitle(e.target.value)}
                    required
                  />

                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Engineering Scope & Repair Instructions
                    </label>
                    <textarea
                      rows={3}
                      value={woDescription}
                      onChange={(e) => setWoDescription(e.target.value)}
                      className="w-full rounded-lg border border-slate-300 p-2.5 text-xs text-slate-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                      required
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">
                        Priority Level
                      </label>
                      <select
                        value={woPriority}
                        onChange={(e) => setWoPriority(e.target.value)}
                        className="w-full rounded-lg border border-slate-300 p-2 text-xs bg-white text-slate-900 focus:ring-2 focus:ring-indigo-500 outline-none"
                      >
                        <option value="LOW">LOW</option>
                        <option value="MEDIUM">MEDIUM</option>
                        <option value="HIGH">HIGH</option>
                        <option value="CRITICAL">CRITICAL</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">
                        Select Contractor
                      </label>
                      <select
                        value={woContractorId}
                        onChange={(e) => setWoContractorId(e.target.value)}
                        className="w-full rounded-lg border border-slate-300 p-2 text-xs bg-white text-slate-900 focus:ring-2 focus:ring-indigo-500 outline-none"
                      >
                        <option value="">-- Leave Unassigned (OPEN) --</option>
                        {contractors.map((c) => (
                          <option key={c.contractor_id} value={c.contractor_id}>
                            {c.contractor_name} ({c.in_progress_count} active jobs)
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <Button
                    type="submit"
                    size="sm"
                    disabled={isSubmittingWo}
                    className="bg-amber-600 hover:bg-amber-700 text-white"
                  >
                    {isSubmittingWo ? (
                      <LoadingSpinner size="sm" />
                    ) : (
                      <>
                        <HardHat className="h-3.5 w-3.5 mr-1.5" />
                        Create & Dispatch Work Order
                      </>
                    )}
                  </Button>
                </form>
              )}
            </div>
          )}
        </div>
      ) : null}
    </Modal>
  )
}
