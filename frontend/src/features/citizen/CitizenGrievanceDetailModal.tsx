import React, { useState, useEffect } from 'react'
import {
  X,
  MapPin,
  Clock,
  FileText,
  Activity,
  HardHat,
  RotateCcw,
  Camera,
  Upload,
  Calendar,
  Image as ImageIcon,
  Loader2,
} from 'lucide-react'
import { citizenService } from '../../services/citizenService'
import { Modal } from '../../components/Modal'
import { Button } from '../../components/Button'
import { Badge } from '../../components/Badge'
import { Alert } from '../../components/Alert'
import type { CitizenGrievanceDetail } from '../../types/citizen'
import type { GrievanceStatus } from '../../types/government'

const MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg']

interface CitizenGrievanceDetailModalProps {
  grievanceId: string | null
  isOpen: boolean
  onClose: () => void
}

export const CitizenGrievanceDetailModal: React.FC<CitizenGrievanceDetailModalProps> = ({
  grievanceId,
  isOpen,
  onClose,
}) => {
  const [detail, setDetail] = useState<CitizenGrievanceDetail | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Additional evidence upload state
  const [showAttachForm, setShowAttachForm] = useState(false)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadPreview, setUploadPreview] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen && grievanceId) {
      loadGrievanceDetails(grievanceId)
    } else {
      setDetail(null)
      setError(null)
      setShowAttachForm(false)
      handleClearUpload()
    }
  }, [isOpen, grievanceId])

  const loadGrievanceDetails = async (id: string) => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await citizenService.getGrievanceDetails(id)
      setDetail(data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unable to fetch grievance details.'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }

  const handleClearUpload = () => {
    setUploadFile(null)
    if (uploadPreview) {
      URL.revokeObjectURL(uploadPreview)
      setUploadPreview(null)
    }
    setUploadError(null)
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUploadError(null)
    setUploadSuccess(null)
    const file = e.target.files?.[0]
    if (!file) return

    if (!ALLOWED_MIME_TYPES.includes(file.type.toLowerCase())) {
      setUploadError('Invalid file type. Supported formats are JPEG, PNG, and WebP.')
      e.target.value = ''
      return
    }

    if (file.size > MAX_IMAGE_SIZE_BYTES) {
      const mb = (file.size / (1024 * 1024)).toFixed(1)
      setUploadError(`File size (${mb} MB) exceeds maximum 10 MB limit.`)
      e.target.value = ''
      return
    }

    setUploadFile(file)
    setUploadPreview(URL.createObjectURL(file))
  }

  const handleAttachEvidence = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!detail || !uploadFile) return

    setIsUploading(true)
    setUploadError(null)
    setUploadSuccess(null)

    try {
      const sanitizedName = uploadFile.name.replace(/[^a-zA-Z0-9._-]/g, '_')
      const storagePath = `/uploads/citizen_${Date.now()}_${sanitizedName}`

      const attachedItem = await citizenService.attachEvidence(detail.id, {
        grievance_id: detail.id,
        file_name: uploadFile.name,
        file_type: uploadFile.type,
        storage_path: storagePath,
        file_size_bytes: uploadFile.size,
      })

      // Update detail local state
      setDetail((prev) => {
        if (!prev) return prev
        return {
          ...prev,
          evidence_items: [...prev.evidence_items, attachedItem],
        }
      })

      setUploadSuccess('Additional photo evidence attached successfully.')
      handleClearUpload()
      setShowAttachForm(false)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to attach evidence.'
      setUploadError(msg)
    } finally {
      setIsUploading(false)
    }
  }

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

  const formatDate = (isoString?: string | null) => {
    if (!isoString) return '—'
    try {
      return new Date(isoString).toLocaleString('en-US', {
        dateStyle: 'medium',
        timeStyle: 'short',
      })
    } catch {
      return isoString
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={detail ? `Grievance Report #${detail.id.slice(0, 8)}` : 'Grievance Details'}
      description="Citizen-safe lifecycle tracking, repair progress, and chronological milestone events."
      maxWidth="4xl"
    >
      <div className="p-6 space-y-6 overflow-y-auto max-h-[80vh]">
        {isLoading && (
          <div className="py-16 text-center">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-2" />
            <p className="text-sm text-slate-500">Loading grievance records and milestone timeline...</p>
          </div>
        )}

        {error && (
          <Alert variant="error" title="Record Unavailable" onDismiss={onClose}>
            {error}
          </Alert>
        )}

        {detail && !isLoading && (
          <>
            {/* Header Summary Card */}
            <div className="bg-slate-50 p-5 rounded-xl border border-slate-200/80 space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-lg text-slate-900">{detail.issue_category}</span>
                  {getStatusBadge(detail.status)}
                </div>
                <div className="text-xs text-slate-500 flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5" />
                  <span>Submitted: {formatDate(detail.created_at)}</span>
                </div>
              </div>

              <p className="text-sm text-slate-700 bg-white p-3 rounded-lg border border-slate-200/80 leading-relaxed">
                {detail.description}
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-xs pt-1">
                <div className="flex items-center gap-2 text-slate-600">
                  <MapPin className="w-4 h-4 text-blue-600 shrink-0" />
                  <span>
                    GPS: <span className="font-mono font-medium">{detail.latitude.toFixed(5)}, {detail.longitude.toFixed(5)}</span>
                  </span>
                </div>
                <div className="flex items-center gap-2 text-slate-600">
                  <FileText className="w-4 h-4 text-slate-500 shrink-0" />
                  <span>Road: <span className="font-medium text-slate-800">{detail.road_name || detail.road_id || 'Municipal Sector'}</span></span>
                </div>
                <div className="flex items-center gap-2 text-slate-600">
                  <Clock className="w-4 h-4 text-slate-500 shrink-0" />
                  <span>Last Update: {formatDate(detail.updated_at)}</span>
                </div>
              </div>
            </div>

            {/* Rework Alert if reverted by municipal audit */}
            {detail.rejection_info?.is_reverted_for_rework && (
              <Alert variant="warning" title="Municipal Audit Notice: Rework Requested">
                <div className="flex items-start gap-2 text-xs">
                  <RotateCcw className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium">
                      {detail.rejection_info.public_message ||
                        'Municipal inspection identified quality requirements requiring contractor correction before final resolution.'}
                    </p>
                    <p className="text-amber-800/80 mt-1">
                      The maintenance work order has been returned for contractor rework to ensure high-grade pavement durability.
                    </p>
                  </div>
                </div>
              </Alert>
            )}

            {/* Work Progress Tracker */}
            {detail.work_progress && (
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-md bg-blue-50 text-blue-600">
                      <HardHat className="w-4 h-4" />
                    </div>
                    <h4 className="font-semibold text-sm text-slate-900">Contractor Repair Progress</h4>
                  </div>
                  {detail.work_progress.status && (
                    <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
                      {detail.work_progress.status}
                    </span>
                  )}
                </div>

                {/* Progress bar */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs text-slate-600">
                    <span>{detail.work_progress.status_display || 'Field Work Progress'}</span>
                    <span className="font-bold text-blue-700">{detail.work_progress.progress_percentage || 0}%</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                    <div
                      className="bg-blue-600 h-2.5 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, Math.max(0, detail.work_progress.progress_percentage || 0))}%` }}
                    />
                  </div>
                </div>

                {detail.work_progress.last_updated_at && (
                  <p className="text-[11px] text-slate-400">
                    Latest contractor update logged at {formatDate(detail.work_progress.last_updated_at)}
                  </p>
                )}
              </div>
            )}

            {/* Citizen-Safe ML Decision Support Summary */}
            {detail.ml_summary && (
              <div className="bg-indigo-50/40 p-4 rounded-xl border border-indigo-100">
                <div className="flex items-center gap-2 mb-2 text-indigo-900 font-semibold text-xs uppercase tracking-wider">
                  <Activity className="w-3.5 h-3.5 text-indigo-600" />
                  <span>RoadX AI Defect Assessment</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="bg-white p-2.5 rounded-lg border border-indigo-100/80">
                    <span className="text-slate-400 block text-[10px]">Identified Defect</span>
                    <span className="font-semibold text-slate-800">{detail.ml_summary.detected_issue || 'Surface Defect'}</span>
                  </div>
                  <div className="bg-white p-2.5 rounded-lg border border-indigo-100/80">
                    <span className="text-slate-400 block text-[10px]">Severity Rating</span>
                    <span className="font-semibold text-slate-800">{detail.ml_summary.severity_level || 'Evaluated'}</span>
                  </div>
                  <div className="bg-white p-2.5 rounded-lg border border-indigo-100/80">
                    <span className="text-slate-400 block text-[10px]">Corridor Risk</span>
                    <span className="font-semibold text-slate-800">{detail.ml_summary.risk_level || 'Normal'}</span>
                  </div>
                  <div className="bg-white p-2.5 rounded-lg border border-indigo-100/80">
                    <span className="text-slate-400 block text-[10px]">Maintenance Priority</span>
                    <span className="font-semibold text-slate-800">{detail.ml_summary.priority_level || 'Standard'}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Attached Evidence Gallery & Attachment Action */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ImageIcon className="w-4 h-4 text-slate-600" />
                  <h4 className="font-semibold text-sm text-slate-900">
                    Submitted Visual Evidence ({detail.evidence_items.length})
                  </h4>
                </div>
                {/* Citizens can attach more evidence while report is active */}
                {!showAttachForm && detail.status !== 'RESOLVED' && detail.status !== 'REJECTED' && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowAttachForm(true)}
                    className="text-xs text-blue-600 flex items-center gap-1 hover:bg-blue-50"
                  >
                    <Camera className="w-3.5 h-3.5" /> Attach Photo
                  </Button>
                )}
              </div>

              {uploadSuccess && (
                <Alert variant="success" onDismiss={() => setUploadSuccess(null)}>
                  {uploadSuccess}
                </Alert>
              )}

              {/* Inline Additional Photo Upload Form */}
              {showAttachForm && (
                <form onSubmit={handleAttachEvidence} className="p-4 bg-blue-50/30 rounded-xl border border-blue-200/80 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-blue-900">Attach Additional Photo Proof</span>
                    <button
                      type="button"
                      onClick={() => {
                        setShowAttachForm(false)
                        handleClearUpload()
                      }}
                      className="text-slate-400 hover:text-slate-600"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  {uploadError && (
                    <Alert variant="error" onDismiss={() => setUploadError(null)}>
                      {uploadError}
                    </Alert>
                  )}

                  {!uploadPreview ? (
                    <label
                      htmlFor="modal-photo-upload"
                      className="border border-dashed border-blue-300 rounded-lg p-4 flex flex-col items-center justify-center cursor-pointer bg-white hover:bg-blue-50/50 transition-colors text-center"
                    >
                      <Camera className="w-5 h-5 text-blue-600 mb-1" />
                      <span className="text-xs font-medium text-slate-700">Select JPEG, PNG, or WebP photo</span>
                      <span className="text-[10px] text-slate-400 mt-0.5">Maximum size: 10 MB</span>
                      <input
                        id="modal-photo-upload"
                        type="file"
                        accept="image/jpeg,image/png,image/webp,image/jpg"
                        onChange={handleFileSelect}
                        className="sr-only"
                      />
                    </label>
                  ) : (
                    <div className="flex items-center gap-3 bg-white p-3 rounded-lg border border-slate-200">
                      <img src={uploadPreview} alt="Upload preview" className="w-16 h-12 object-cover rounded border" />
                      <div className="flex-1 min-w-0 text-xs">
                        <p className="font-medium text-slate-800 truncate">{uploadFile?.name}</p>
                        <p className="text-slate-400">
                          {uploadFile ? (uploadFile.size / (1024 * 1024)).toFixed(2) : 0} MB
                        </p>
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={handleClearUpload}
                        className="text-rose-600 text-xs"
                      >
                        Change
                      </Button>
                    </div>
                  )}

                  <div className="flex justify-end gap-2 pt-1">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setShowAttachForm(false)
                        handleClearUpload()
                      }}
                      disabled={isUploading}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      variant="primary"
                      size="sm"
                      disabled={!uploadFile || isUploading}
                      className="flex items-center gap-1.5"
                    >
                      {isUploading ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Attaching...</span>
                        </>
                      ) : (
                        <>
                          <Upload className="w-3.5 h-3.5" />
                          <span>Upload & Attach</span>
                        </>
                      )}
                    </Button>
                  </div>
                </form>
              )}

              {/* Evidence Items List */}
              {detail.evidence_items.length === 0 ? (
                <div className="p-4 text-center rounded-lg border border-dashed border-slate-200 text-slate-400 text-xs">
                  No visual evidence photos attached for this report.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                  {detail.evidence_items.map((item, idx) => (
                    <div
                      key={item.id || idx}
                      className="p-3 bg-white rounded-lg border border-slate-200 text-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-800 truncate" title={item.file_name}>
                          {item.file_name}
                        </span>
                        <span className="text-[10px] text-slate-400 uppercase font-mono">{item.file_type.split('/')[1] || 'IMG'}</span>
                      </div>
                      <p className="font-mono text-[11px] text-slate-500 truncate" title={item.storage_path}>
                        {item.storage_path}
                      </p>
                      <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-100">
                        <span>{item.file_size_bytes ? `${(item.file_size_bytes / 1024).toFixed(0)} KB` : '—'}</span>
                        <span>{formatDate(item.uploaded_at)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Chronological Milestone Timeline */}
            <div className="space-y-3 pt-2">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-slate-600" />
                <h4 className="font-semibold text-sm text-slate-900">Progress History & Audit Trail</h4>
              </div>

              {detail.timeline.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No milestone events logged yet.</p>
              ) : (
                <div className="relative pl-6 space-y-4 border-l-2 border-slate-200 ml-2 py-1">
                  {detail.timeline.map((event, idx) => (
                    <div key={idx} className="relative group">
                      {/* Timeline dot */}
                      <div className="absolute -left-[31px] top-1 w-3.5 h-3.5 rounded-full bg-white border-2 border-blue-600 group-hover:scale-125 transition-transform" />
                      <div className="bg-slate-50/80 p-3 rounded-lg border border-slate-200/60 text-xs space-y-1">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-semibold text-slate-800">{event.event_type.replace(/_/g, ' ')}</span>
                          <span className="text-[11px] text-slate-400">{formatDate(event.timestamp)}</span>
                        </div>
                        <p className="text-slate-600 leading-relaxed">{event.public_message}</p>
                        {event.status && (
                          <div className="pt-0.5">
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-200 text-slate-700">
                              Status: {event.status}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>

      <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-end">
        <Button variant="secondary" onClick={onClose}>
          Close Details
        </Button>
      </div>
    </Modal>
  )
}
