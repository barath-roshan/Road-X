import React, { useEffect, useState } from 'react'
import {
  X,
  HardHat,
  MapPin,
  FileText,
  Clock,
  CheckCircle2,
  RotateCcw,
  Upload,
  Send,
  Play,
  Check,
  Layers,
  Paperclip,
  Activity,
} from 'lucide-react'
import { contractorService } from '../../services/contractorService'
import type { ContractorWorkOrderDetail } from '../../types/contractor'
import { Button } from '../../components/Button'
import { Input } from '../../components/Input'
import { Alert } from '../../components/Alert'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { StatusBadge, PriorityBadge } from '../../components/Badge'

interface ContractorWorkOrderDetailModalProps {
  workOrderId: string
  isOpen: boolean
  onClose: () => void
  onOrderUpdated?: () => void
}

export const ContractorWorkOrderDetailModal: React.FC<ContractorWorkOrderDetailModalProps> = ({
  workOrderId,
  isOpen,
  onClose,
  onOrderUpdated,
}) => {
  const [detail, setDetail] = useState<ContractorWorkOrderDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Progress Update Form State
  const [progressPct, setProgressPct] = useState<number>(0)
  const [progressNote, setProgressNote] = useState<string>('')
  const [updatingProgress, setUpdatingProgress] = useState(false)
  const [progressError, setProgressError] = useState<string | null>(null)
  const [progressSuccess, setProgressSuccess] = useState<string | null>(null)

  // Completion Submission Form State
  const [completionNote, setCompletionNote] = useState<string>('')
  const [actualWorkSummary, setActualWorkSummary] = useState<string>('')
  const [selectedEvidenceIds, setSelectedEvidenceIds] = useState<string[]>([])
  const [submittingCompletion, setSubmittingCompletion] = useState(false)
  const [completionError, setCompletionError] = useState<string | null>(null)
  const [completionSuccess, setCompletionSuccess] = useState<string | null>(null)

  // Evidence Attachment Form State
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null)
  const [attachingEvidence, setAttachingEvidence] = useState(false)
  const [evidenceError, setEvidenceError] = useState<string | null>(null)
  const [evidenceSuccess, setEvidenceSuccess] = useState<string | null>(null)

  // Start / Ack States
  const [actionLoading, setActionLoading] = useState(false)
  const [actionMessage, setActionMessage] = useState<string | null>(null)

  const fetchDetail = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await contractorService.getWorkOrderDetail(workOrderId)
      setDetail(data)
      setProgressPct(data.current_progress)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load work order details.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen && workOrderId) {
      fetchDetail()
      // Reset form states
      setProgressNote('')
      setProgressError(null)
      setProgressSuccess(null)
      setCompletionNote('')
      setActualWorkSummary('')
      setSelectedEvidenceIds([])
      setCompletionError(null)
      setCompletionSuccess(null)
      setEvidenceFile(null)
      setEvidenceError(null)
      setEvidenceSuccess(null)
      setActionMessage(null)
    }
  }, [isOpen, workOrderId])

  if (!isOpen) return null

  // Handle Acknowledge
  const handleAcknowledge = async () => {
    if (!detail) return
    setActionLoading(true)
    setActionMessage(null)
    try {
      await contractorService.acknowledgeWorkOrder(detail.id, 'Contractor acknowledged assignment.')
      setActionMessage('Work order assignment acknowledged successfully.')
      await fetchDetail()
      onOrderUpdated?.()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to acknowledge work order.'
      setError(msg)
    } finally {
      setActionLoading(false)
    }
  }

  // Handle Start Work
  const handleStartWork = async () => {
    if (!detail) return
    setActionLoading(true)
    setActionMessage(null)
    try {
      await contractorService.startWorkOrder(detail.id, 'Contractor commenced physical repair work.')
      setActionMessage('Work order status changed to IN_PROGRESS.')
      await fetchDetail()
      onOrderUpdated?.()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to start work order.'
      setError(msg)
    } finally {
      setActionLoading(false)
    }
  }

  // Handle Log Progress
  const handleLogProgress = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!detail) return

    setProgressError(null)
    setProgressSuccess(null)

    if (progressPct < 0 || progressPct > 100) {
      setProgressError('Progress must be between 0 and 100%.')
      return
    }

    // Monotonicity check in UI
    if (progressPct < detail.current_progress) {
      const lower = progressNote.toLowerCase()
      const allowed = ['correction', 'rework', 'revised', 'reset', 'rollback', 'adjustment']
      if (!allowed.some((kw) => lower.includes(kw))) {
        setProgressError(
          `Progress cannot decrease from ${detail.current_progress}% to ${progressPct}% without an explicit note containing 'correction', 'rework', 'revised', or 'adjustment'.`
        )
        return
      }
    }

    setUpdatingProgress(true)
    try {
      await contractorService.updateProgress(detail.id, {
        progress_percentage: progressPct,
        note: progressNote.trim() || undefined,
      })
      setProgressSuccess(`Progress successfully recorded at ${progressPct}%.`)
      setProgressNote('')
      await fetchDetail()
      onOrderUpdated?.()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update progress.'
      setProgressError(msg)
    } finally {
      setUpdatingProgress(false)
    }
  }

  // Handle Evidence Metadata Attachment
  const handleAttachEvidence = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!detail || !evidenceFile) return

    setEvidenceError(null)
    setEvidenceSuccess(null)

    // Allowed file types
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf']
    if (!allowedTypes.includes(evidenceFile.type)) {
      setEvidenceError('Invalid file type. Only JPEG, PNG, WebP images, or PDF documents are accepted.')
      return
    }

    // Max 10MB
    const maxSizeBytes = 10 * 1024 * 1024
    if (evidenceFile.size > maxSizeBytes) {
      setEvidenceError('File size exceeds the 10MB limit.')
      return
    }

    setAttachingEvidence(true)
    try {
      // Backend contract expects EvidenceCreate metadata
      const sanitizedName = evidenceFile.name.replace(/[^a-zA-Z0-9._-]/g, '_')
      const storagePath = `/uploads/evidence/${Date.now()}_${sanitizedName}`

      const createdEvidence = await contractorService.attachEvidence(detail.id, {
        file_name: evidenceFile.name,
        file_type: evidenceFile.type,
        storage_path: storagePath,
        file_size_bytes: evidenceFile.size,
        grievance_id: detail.grievance_id,
        work_order_id: detail.id,
      })

      setEvidenceSuccess(`Evidence metadata attached successfully (${evidenceFile.name}).`)
      setEvidenceFile(null)
      // Auto-select this evidence for completion submission
      setSelectedEvidenceIds((prev) => [...prev, createdEvidence.id])
      await fetchDetail()
      onOrderUpdated?.()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to attach evidence metadata.'
      setEvidenceError(msg)
    } finally {
      setAttachingEvidence(false)
    }
  }

  // Handle Completion Submission
  const handleSubmitCompletion = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!detail) return

    setCompletionError(null)
    setCompletionSuccess(null)

    if (!completionNote.trim()) {
      setCompletionError('A completion summary note is required.')
      return
    }

    setSubmittingCompletion(true)
    try {
      await contractorService.submitCompletion(detail.id, {
        completion_note: completionNote.trim(),
        actual_work_summary: actualWorkSummary.trim() || undefined,
        evidence_ids: selectedEvidenceIds.length > 0 ? selectedEvidenceIds : undefined,
      })
      setCompletionSuccess(
        'Work order submitted for government officer verification. Status updated to PENDING_VERIFICATION.'
      )
      setCompletionNote('')
      setActualWorkSummary('')
      await fetchDetail()
      onOrderUpdated?.()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to submit work order for verification.'
      setCompletionError(msg)
    } finally {
      setSubmittingCompletion(false)
    }
  }

  const toggleEvidenceSelection = (evId: string) => {
    setSelectedEvidenceIds((prev) =>
      prev.includes(evId) ? prev.filter((id) => id !== evId) : [...prev, evId]
    )
  }

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-4"
      data-testid="contractor-work-order-detail-modal"
    >
      <div className="relative bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-4xl max-h-[92vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50/80">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-100 text-indigo-700 rounded-lg">
              <HardHat className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-slate-900 line-clamp-1">
                  {detail?.title || 'Work Order Inspection'}
                </h2>
                {detail && <StatusBadge status={detail.status} />}
                {detail?.rework_required && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">
                    Rework Required
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 font-mono">
                WO ID: {workOrderId} {detail?.grievance_id && `• Grievance: ${detail.grievance_id}`}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            data-testid="modal-close-button"
            className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading && (
            <div className="py-16 flex flex-col items-center justify-center">
              <LoadingSpinner size="lg" />
              <p className="mt-4 text-sm text-slate-500">Loading work order details...</p>
            </div>
          )}

          {error && (
            <Alert
              variant="error"
              title="Failed to Load Work Order"
            >
              {error}
            </Alert>
          )}

          {actionMessage && (
            <Alert
              variant="success"
              title="Action Completed"
            >
              {actionMessage}
            </Alert>
          )}

          {detail && !loading && (
            <>
              {/* Rework Feedback Banner (If rejected by government) */}
              {detail.rework_required && detail.latest_rejection_notes && (
                <div
                  data-testid="rework-feedback-banner"
                  className="bg-amber-50 border-2 border-amber-400/80 rounded-xl p-4 space-y-2"
                >
                  <div className="flex items-center gap-2 text-amber-900 font-bold text-sm">
                    <RotateCcw className="h-4 w-4 text-amber-600" />
                    <span>Government Officer Rejection Feedback & Corrective Instructions</span>
                  </div>
                  <div className="text-xs text-amber-800 bg-white/70 p-3 rounded-lg border border-amber-200 font-medium">
                    "{detail.latest_rejection_notes}"
                  </div>
                  {detail.rejection_timestamp && (
                    <div className="text-[11px] text-amber-600">
                      Rejected on: {new Date(detail.rejection_timestamp).toLocaleString()}
                    </div>
                  )}
                  <p className="text-[11px] text-amber-700 italic">
                    Execute the requested repairs, update progress notes, attach corrected evidence photos, and resubmit for verification below.
                  </p>
                </div>
              )}

              {/* Status Notice if Pending Verification */}
              {detail.status === 'PENDING_VERIFICATION' && (
                <Alert
                  variant="info"
                  title="Awaiting Municipal Verification"
                >
                  Work completion was submitted to the municipal authority. Further progress updates or resubmissions are locked until the government officer verifies the repairs.
                </Alert>
              )}

              {/* Status Notice if Completed */}
              {detail.status === 'COMPLETED' && (
                <Alert
                  variant="success"
                  title="Work Order Verified & Completed"
                >
                  This road repair was approved and officially closed by the municipal engineer. The citizen grievance is resolved.
                </Alert>
              )}

              {/* Action Buttons: Acknowledge & Start */}
              {detail.status === 'ASSIGNED' && (
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-bold text-blue-900">Job Assignment Pending Start</h4>
                    <p className="text-xs text-blue-700 mt-0.5">
                      Confirm receipt of this dispatch order and mark repair work as started.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={handleAcknowledge}
                      disabled={actionLoading}
                      data-testid="btn-ack-order"
                      className="text-xs gap-1.5"
                    >
                      <Check className="h-3.5 w-3.5" />
                      <span>Acknowledge</span>
                    </Button>
                    <Button
                      size="sm"
                      onClick={handleStartWork}
                      disabled={actionLoading}
                      data-testid="btn-start-order"
                      className="text-xs gap-1.5 bg-blue-600 hover:bg-blue-700 text-white"
                    >
                      <Play className="h-3.5 w-3.5" />
                      <span>Start Work</span>
                    </Button>
                  </div>
                </div>
              )}

              {/* Two Column Grid: Job Overview & Grievance Context */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Left: Job Details & Road Location */}
                <div className="space-y-4">
                  <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/80 space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Work Order Specification
                    </h3>
                    <p className="text-sm text-slate-700 leading-relaxed">{detail.description}</p>
                    <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-200">
                      <PriorityBadge priority={detail.priority} />
                      <span className="text-xs text-slate-500 py-0.5 px-2 bg-white rounded border border-slate-200">
                        Created: {new Date(detail.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>

                  <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/80 space-y-2 text-xs">
                    <div className="flex items-center gap-1.5 font-bold text-slate-700">
                      <MapPin className="h-3.5 w-3.5 text-rose-500" />
                      <span>Road Location Reference</span>
                    </div>
                    <div className="text-slate-800 font-semibold">{detail.road_name || 'Designated Road Section'}</div>
                    {detail.road_code && (
                      <div className="text-slate-500 font-mono">Segment ID: {detail.road_code}</div>
                    )}
                    {detail.latitude && detail.longitude && (
                      <div className="text-slate-500 font-mono">
                        GPS: {detail.latitude.toFixed(6)}, {detail.longitude.toFixed(6)}
                      </div>
                    )}
                  </div>
                </div>

                {/* Right: Citizen Grievance & ML Intelligence */}
                <div className="space-y-4">
                  <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/80 space-y-2 text-xs">
                    <div className="flex items-center gap-1.5 font-bold text-slate-700">
                      <FileText className="h-3.5 w-3.5 text-indigo-500" />
                      <span>Citizen Defect Report Context</span>
                    </div>
                    <p className="text-slate-600 italic">
                      "{detail.grievance_description || 'No citizen defect description provided.'}"
                    </p>
                    {detail.grievance_issue_category && (
                      <div className="pt-2 border-t border-slate-200 text-slate-500">
                        Category: <strong className="text-slate-800">{detail.grievance_issue_category}</strong>
                      </div>
                    )}
                  </div>

                  {/* ML Risk & Priority indicators if present */}
                  {(detail.grievance_severity || detail.grievance_risk_level) && (
                    <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/80 space-y-2 text-xs">
                      <div className="flex items-center gap-1.5 font-bold text-slate-700">
                        <Activity className="h-3.5 w-3.5 text-purple-600" />
                        <span>AI Defect Severity & Failure Risk</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-slate-600">
                        <div>
                          Severity:{' '}
                          <span className="font-semibold text-slate-800">{detail.grievance_severity || 'N/A'}</span>
                        </div>
                        <div>
                          Risk Level:{' '}
                          <span className="font-semibold text-slate-800">{detail.grievance_risk_level || 'N/A'}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Progress Tracking Section */}
              <div className="border border-slate-200 rounded-xl p-5 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                      <Clock className="h-4 w-4 text-indigo-600" />
                      <span>Progress Tracking & Milestones</span>
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Log incremental progress updates. Note: 100% progress does not automatically resolve the work order.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xl font-extrabold text-indigo-600" data-testid="current-progress-pct">
                      {detail.current_progress}%
                    </span>
                    <span className="text-xs text-slate-400">Current</span>
                  </div>
                </div>

                {/* Visual Progress Bar */}
                <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                  <div
                    className="bg-indigo-600 h-2.5 rounded-full transition-all duration-300"
                    style={{ width: `${detail.current_progress}%` }}
                  />
                </div>

                {/* Progress Update Form (Enabled only if ASSIGNED or IN_PROGRESS) */}
                {detail.status !== 'PENDING_VERIFICATION' && detail.status !== 'COMPLETED' && (
                  <form onSubmit={handleLogProgress} className="bg-slate-50 p-4 rounded-xl border border-slate-200/80 space-y-3">
                    <div className="text-xs font-bold text-slate-700">Log Progress Update</div>

                    {progressError && (
                      <Alert variant="error">{progressError}</Alert>
                    )}
                    {progressSuccess && (
                      <Alert variant="success">{progressSuccess}</Alert>
                    )}

                    <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-slate-600 mb-1">
                          Progress % (0-100)
                        </label>
                        <Input
                          type="number"
                          min={0}
                          max={100}
                          value={progressPct}
                          onChange={(e) => setProgressPct(Number(e.target.value))}
                          data-testid="input-progress-pct"
                          required
                        />
                      </div>
                      <div className="sm:col-span-3">
                        <label className="block text-xs font-medium text-slate-600 mb-1">
                          Progress Note / Status Explanation
                        </label>
                        <Input
                          type="text"
                          placeholder="e.g. Cleared debris, laid asphalt base layer..."
                          value={progressNote}
                          onChange={(e) => setProgressNote(e.target.value)}
                          data-testid="input-progress-note"
                        />
                      </div>
                    </div>

                    <div className="flex justify-end pt-1">
                      <Button
                        type="submit"
                        size="sm"
                        disabled={updatingProgress}
                        data-testid="btn-submit-progress"
                        className="text-xs gap-1.5"
                      >
                        {updatingProgress ? <LoadingSpinner size="sm" /> : <Clock className="h-3.5 w-3.5" />}
                        <span>Save Progress Update</span>
                      </Button>
                    </div>
                  </form>
                )}

                {/* Progress History List */}
                {detail.progress_history && detail.progress_history.length > 0 && (
                  <div className="space-y-2 pt-2">
                    <div className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Logged Progress Updates ({detail.progress_history.length})
                    </div>
                    <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                      {detail.progress_history.map((item) => (
                        <div
                          key={item.id}
                          className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-200/70 text-xs"
                        >
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200 font-mono">
                              {item.progress_percentage}%
                            </span>
                            <span className="text-slate-700">{item.note || 'Progress update recorded'}</span>
                          </div>
                          <span className="text-[11px] text-slate-400">
                            {new Date(item.created_at).toLocaleString()}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Completion Evidence Attachment & Gallery */}
              <div className="border border-slate-200 rounded-xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                      <Paperclip className="h-4 w-4 text-emerald-600" />
                      <span>Completion & Repair Evidence</span>
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Upload photo evidence or repair documentation to support verification
                    </p>
                  </div>
                  <span className="text-xs text-slate-500 font-medium">
                    {detail.completion_evidence?.length || 0} file(s) attached
                  </span>
                </div>

                {/* Evidence Attachment Form */}
                {detail.status !== 'PENDING_VERIFICATION' && detail.status !== 'COMPLETED' && (
                  <form onSubmit={handleAttachEvidence} className="bg-slate-50 p-4 rounded-xl border border-slate-200/80 space-y-3">
                    <div className="text-xs font-bold text-slate-700">Attach Repair Photo Evidence</div>

                    {evidenceError && <Alert variant="error">{evidenceError}</Alert>}
                    {evidenceSuccess && <Alert variant="success">{evidenceSuccess}</Alert>}

                    <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
                      <input
                        type="file"
                        accept="image/jpeg,image/png,image/webp,application/pdf"
                        onChange={(e) => setEvidenceFile(e.target.files?.[0] || null)}
                        data-testid="input-evidence-file"
                        className="text-xs text-slate-600 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-emerald-50 file:text-emerald-700 hover:file:bg-emerald-100 cursor-pointer"
                      />
                      <Button
                        type="submit"
                        size="sm"
                        disabled={!evidenceFile || attachingEvidence}
                        data-testid="btn-attach-evidence"
                        className="text-xs gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white shrink-0"
                      >
                        {attachingEvidence ? <LoadingSpinner size="sm" /> : <Upload className="h-3.5 w-3.5" />}
                        <span>Attach Metadata</span>
                      </Button>
                    </div>
                    <p className="text-[11px] text-slate-500">
                      Supports JPEG, PNG, WebP or PDF documents up to 10MB. Stores evidence reference linking this work order and grievance.
                    </p>
                  </form>
                )}

                {/* Existing Evidence List */}
                {detail.completion_evidence && detail.completion_evidence.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2">
                    {detail.completion_evidence.map((ev) => (
                      <div
                        key={ev.id}
                        className={`flex items-center justify-between p-2.5 rounded-lg border text-xs transition-colors ${
                          selectedEvidenceIds.includes(ev.id)
                            ? 'bg-emerald-50/70 border-emerald-300'
                            : 'bg-white border-slate-200'
                        }`}
                      >
                        <div className="flex items-center gap-2 overflow-hidden">
                          <input
                            type="checkbox"
                            checked={selectedEvidenceIds.includes(ev.id)}
                            onChange={() => toggleEvidenceSelection(ev.id)}
                            id={`ev-checkbox-${ev.id}`}
                            className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 cursor-pointer"
                          />
                          <label htmlFor={`ev-checkbox-${ev.id}`} className="truncate cursor-pointer">
                            <div className="font-semibold text-slate-800 truncate">{ev.file_name}</div>
                            <div className="text-[11px] text-slate-400 font-mono">
                              {ev.file_type} • {ev.file_size_bytes ? `${Math.round(ev.file_size_bytes / 1024)} KB` : 'size unknown'}
                            </div>
                          </label>
                        </div>
                        <span className="text-[10px] text-slate-400 shrink-0">
                          {new Date(ev.uploaded_at).toLocaleDateString()}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs text-slate-400 italic py-2">
                    No evidence photos attached yet. Attach post-repair photos before submitting for verification.
                  </div>
                )}
              </div>

              {/* Submit for Government Verification Section */}
              {detail.status !== 'PENDING_VERIFICATION' && detail.status !== 'COMPLETED' && (
                <div className="border-2 border-indigo-200 bg-indigo-50/30 rounded-xl p-5 space-y-4">
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-indigo-100 text-indigo-700 rounded-lg shrink-0 mt-0.5">
                      <Send className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-indigo-950">
                        Submit Work Completion for Government Verification
                      </h3>
                      <p className="text-xs text-indigo-800/80 mt-0.5 leading-relaxed">
                        Transitions this work order and grievance to <strong>PENDING_VERIFICATION</strong>.
                        A municipal government engineer will inspect the repairs and photographic evidence to approve and resolve.
                      </p>
                    </div>
                  </div>

                  {completionError && <Alert variant="error">{completionError}</Alert>}
                  {completionSuccess && <Alert variant="success">{completionSuccess}</Alert>}

                  <form onSubmit={handleSubmitCompletion} className="space-y-3 pt-1">
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        Completion Summary Note <span className="text-rose-500">*</span>
                      </label>
                      <Input
                        type="text"
                        placeholder="e.g. Pothole filled and sealed with high-grade bitumen asphalt."
                        value={completionNote}
                        onChange={(e) => setCompletionNote(e.target.value)}
                        data-testid="input-completion-note"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        Actual Work Details & Repair Breakdown (Optional)
                      </label>
                      <Input
                        type="text"
                        placeholder="e.g. Dimensions: 2m x 1.5m, compaction completed, road reopened."
                        value={actualWorkSummary}
                        onChange={(e) => setActualWorkSummary(e.target.value)}
                        data-testid="input-actual-work-summary"
                      />
                    </div>

                    <div className="flex items-center justify-between pt-2">
                      <span className="text-xs text-slate-500">
                        {selectedEvidenceIds.length} evidence file(s) linked to this submission
                      </span>
                      <Button
                        type="submit"
                        disabled={submittingCompletion || !completionNote.trim()}
                        data-testid="btn-submit-verification"
                        className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs gap-1.5 shadow-xs"
                      >
                        {submittingCompletion ? <LoadingSpinner size="sm" /> : <CheckCircle2 className="h-4 w-4" />}
                        <span>Submit for Verification</span>
                      </Button>
                    </div>
                  </form>
                </div>
              )}

              {/* Workflow Audit Timeline */}
              {detail.timeline && detail.timeline.length > 0 && (
                <div className="border border-slate-200 rounded-xl p-5 space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                    <Layers className="h-3.5 w-3.5 text-slate-400" />
                    <span>Audit Trail & Workflow History</span>
                  </h3>
                  <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                    {detail.timeline.map((event) => (
                      <div
                        key={event.id}
                        className="p-2.5 bg-slate-50 rounded-lg border border-slate-200/70 text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-800">{event.event_type}</span>
                          <span className="text-[11px] text-slate-400">
                            {new Date(event.created_at).toLocaleString()}
                          </span>
                        </div>
                        {event.notes && <p className="text-slate-600 text-[11px]">{event.notes}</p>}
                        <div className="flex items-center gap-2 text-[10px] text-slate-400">
                          {event.actor_role && <span>Actor: {event.actor_role}</span>}
                          {event.old_status && event.new_status && (
                            <span>
                              State: {event.old_status} &rarr; {event.new_status}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-200 bg-slate-50/80 flex items-center justify-between">
          <span className="text-xs text-slate-400">RoadX Contractor Dashboard Module</span>
          <Button variant="secondary" size="sm" onClick={onClose} data-testid="modal-done-button">
            Close
          </Button>
        </div>
      </div>
    </div>
  )
}
