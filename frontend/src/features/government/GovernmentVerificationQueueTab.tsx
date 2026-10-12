import React, { useEffect, useState } from 'react'
import {
  CheckCircle2,
  XCircle,
  HardHat,
  FileText,
  RefreshCw,
  Send,
  MapPin,
  Calendar,
} from 'lucide-react'
import { Card, CardContent } from '../../components/Card'
import { Button } from '../../components/Button'
import { Alert } from '../../components/Alert'
import { Modal } from '../../components/Modal'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { EmptyState } from '../../components/EmptyState'
import { governmentService } from '../../services/governmentService'
import type {
  GovernmentDashboardVerificationItem,
  VerificationDecision,
} from '../../types/government'

export const GovernmentVerificationQueueTab: React.FC = () => {
  const [items, setItems] = useState<GovernmentDashboardVerificationItem[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)

  // Verification Action Dialog State
  const [activeItem, setActiveItem] = useState<GovernmentDashboardVerificationItem | null>(null)
  const [decision, setDecision] = useState<VerificationDecision>('APPROVE')
  const [officerNotes, setOfficerNotes] = useState<string>('')
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false)

  const fetchVerificationQueue = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await governmentService.getVerificationQueue()
      setItems(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch verification queue.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchVerificationQueue()
  }, [])

  const handleOpenVerification = (
    item: GovernmentDashboardVerificationItem,
    targetDecision: VerificationDecision
  ) => {
    setActiveItem(item)
    setDecision(targetDecision)
    setOfficerNotes('')
    setError(null)
  }

  const handleSubmitVerification = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!activeItem) return

    if (decision === 'REJECT' && !officerNotes.trim()) {
      setError('Please provide feedback or rework instructions when rejecting completion.')
      return
    }

    setIsSubmitting(true)
    setError(null)
    setActionSuccess(null)

    try {
      await governmentService.verifyWorkOrder(activeItem.work_order_id, {
        decision,
        notes: officerNotes.trim() || undefined,
      })
      setActionSuccess(
        decision === 'APPROVE'
          ? `Work Order ${activeItem.work_order_id.slice(0, 8)} approved and grievance officially resolved!`
          : `Work Order ${activeItem.work_order_id.slice(0, 8)} rejected and returned to contractor for rework.`
      )
      setActiveItem(null)
      await fetchVerificationQueue()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to process verification decision.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            Work Completion Verification Queue
          </h2>
          <p className="text-xs text-slate-500">
            Audit contractor completion evidence and issue authoritative municipal sign-off to resolve citizen grievances.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchVerificationQueue}
          className="self-start sm:self-auto flex items-center gap-1.5 text-slate-600"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh Queue
        </Button>
      </div>

      {/* Governance Notice Banner */}
      <div className="bg-indigo-50 border border-indigo-200/80 rounded-xl p-4 flex items-start gap-3 shadow-2xs">
        <div className="p-2 bg-indigo-100 rounded-lg text-indigo-700 shrink-0">
          <CheckCircle2 className="h-5 w-5" />
        </div>
        <div>
          <h4 className="text-sm font-semibold text-indigo-950">
            Exclusive Municipal Resolution Authority
          </h4>
          <p className="text-xs text-indigo-800 leading-relaxed">
            By system governance rule, contractor status updates cannot directly close a grievance. An authorized government officer APPROVE decision is required to verify repairs and transition a citizen grievance to <span className="font-semibold uppercase">RESOLVED</span>.
          </p>
        </div>
      </div>

      {actionSuccess && (
        <Alert
          variant="success"
          title="Sign-off Confirmed"
          onDismiss={() => setActionSuccess(null)}
        >
          {actionSuccess}
        </Alert>
      )}

      {error && !activeItem && (
        <Alert variant="error" title="Queue Error" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      {isLoading ? (
        <div className="py-16 flex justify-center">
          <LoadingSpinner size="lg" message="Loading work orders pending verification..." />
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          title="Verification Queue Empty"
          description="There are currently no contractor submissions awaiting officer completion verification."
        />
      ) : (
        <div className="grid grid-cols-1 gap-5">
          {items.map((item) => (
            <Card key={item.work_order_id} className="border-amber-200 bg-amber-50/10 shadow-2xs">
              <CardContent className="p-5 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-100 text-amber-800">
                        PENDING VERIFICATION
                      </span>
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                        {item.priority} PRIORITY
                      </span>
                    </div>
                    <h3 className="text-base font-bold text-slate-900 mt-1.5">{item.work_order_title}</h3>
                    <p className="text-xs text-slate-600 mt-1">{item.grievance_description}</p>
                  </div>

                  <div className="text-xs text-slate-500 space-y-1 sm:text-right shrink-0">
                    <div className="flex sm:justify-end items-center gap-1">
                      <MapPin className="h-3.5 w-3.5 text-slate-400" />
                      <span className="font-medium text-slate-800">{item.road_name || 'Road Segment'}</span>
                    </div>
                    <div className="flex sm:justify-end items-center gap-1">
                      <HardHat className="h-3.5 w-3.5 text-amber-600" />
                      <span className="font-semibold text-slate-800">{item.contractor_name || item.contractor_id}</span>
                    </div>
                    <div className="flex sm:justify-end items-center gap-1 text-[11px] text-slate-400">
                      <Calendar className="h-3 w-3" />
                      Submitted: {new Date(item.submitted_at).toLocaleString()}
                    </div>
                  </div>
                </div>

                {/* Latest Contractor Progress Note */}
                {item.latest_progress_note && (
                  <div className="p-3 bg-white rounded-lg border border-slate-200 text-xs">
                    <span className="font-bold text-slate-700">Contractor Completion Note: </span>
                    <span className="text-slate-600 italic">"{item.latest_progress_note}"</span>
                  </div>
                )}

                {/* Evidence Attachments */}
                {item.evidence_items.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="text-xs font-bold text-slate-700 flex items-center gap-1">
                      <FileText className="h-3.5 w-3.5 text-slate-500" />
                      Completion Evidence ({item.evidence_items.length} items)
                    </span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                      {item.evidence_items.map((ev) => (
                        <div key={ev.id} className="p-2.5 bg-white rounded border border-slate-200 text-xs">
                          <p className="font-semibold text-slate-800 truncate" title={ev.file_name}>
                            {ev.file_name}
                          </p>
                          <p className="text-[11px] text-slate-400">{ev.file_type}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="pt-3 border-t border-slate-200 flex flex-wrap items-center justify-end gap-3">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleOpenVerification(item, 'REJECT')}
                    className="border-rose-200 text-rose-600 hover:bg-rose-50 flex items-center gap-1.5"
                  >
                    <XCircle className="h-4 w-4" />
                    Reject / Request Rework
                  </Button>

                  <Button
                    size="sm"
                    onClick={() => handleOpenVerification(item, 'APPROVE')}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1.5"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    Approve & Resolve Grievance
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Verification Confirmation Modal */}
      {activeItem && (
        <Modal
          isOpen={Boolean(activeItem)}
          onClose={() => !isSubmitting && setActiveItem(null)}
          title={
            decision === 'APPROVE'
              ? 'Approve Repair Completion'
              : 'Reject Completion & Request Rework'
          }
          description={`Work Order: ${activeItem.work_order_title}`}
          maxWidth="lg"
        >
          <form onSubmit={handleSubmitVerification} className="space-y-4">
            {error && (
              <Alert variant="error" title="Validation Error" onDismiss={() => setError(null)}>
                {error}
              </Alert>
            )}

            <div
              className={`p-3 rounded-lg text-xs border ${
                decision === 'APPROVE'
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                  : 'bg-rose-50 border-rose-200 text-rose-900'
              }`}
            >
              {decision === 'APPROVE' ? (
                <p>
                  Approving this work order verifies that road repairs meet municipal standards. This will officially transition the grievance to <strong>RESOLVED</strong> and mark the work order as <strong>COMPLETED</strong>.
                </p>
              ) : (
                <p>
                  Rejecting this submission indicates that the road repair is incomplete or substandard. Both the work order and grievance will revert to <strong>IN_PROGRESS</strong> status for rework.
                </p>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                {decision === 'REJECT' ? 'Rework Reason & Instructions (Required)' : 'Officer Verification Remarks (Optional)'}
              </label>
              <textarea
                rows={3}
                value={officerNotes}
                onChange={(e) => setOfficerNotes(e.target.value)}
                placeholder={
                  decision === 'REJECT'
                    ? 'Specify why repair evidence is insufficient or what rework is required...'
                    : 'Notes on quality of work, asphalt condition, or inspection...'
                }
                className="w-full rounded-lg border border-slate-300 p-2.5 text-xs text-slate-900 focus:ring-2 focus:ring-indigo-500 outline-none"
                required={decision === 'REJECT'}
              />
            </div>

            <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-200">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={isSubmitting}
                onClick={() => setActiveItem(null)}
              >
                Cancel
              </Button>

              <Button
                type="submit"
                size="sm"
                disabled={isSubmitting}
                className={
                  decision === 'APPROVE'
                    ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                    : 'bg-rose-600 hover:bg-rose-700 text-white'
                }
              >
                {isSubmitting ? (
                  <LoadingSpinner size="sm" />
                ) : (
                  <>
                    <Send className="h-3.5 w-3.5 mr-1.5" />
                    {decision === 'APPROVE' ? 'Confirm Approval' : 'Submit Rejection'}
                  </>
                )}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
