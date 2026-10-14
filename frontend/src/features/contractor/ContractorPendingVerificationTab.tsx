import React, { useEffect, useState } from 'react'
import {
  Clock,
  CheckCircle2,
  Paperclip,
  RefreshCw,
  ExternalLink,
} from 'lucide-react'
import { contractorService } from '../../services/contractorService'
import type { ContractorPendingVerificationItem } from '../../types/contractor'
import { Card, CardHeader, CardTitle, CardContent } from '../../components/Card'
import { Button } from '../../components/Button'
import { Alert } from '../../components/Alert'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { EmptyState } from '../../components/EmptyState'
import { PriorityBadge } from '../../components/Badge'

interface ContractorPendingVerificationTabProps {
  onSelectWorkOrder: (workOrderId: string) => void
}

export const ContractorPendingVerificationTab: React.FC<ContractorPendingVerificationTabProps> = ({
  onSelectWorkOrder,
}) => {
  const [pendingItems, setPendingItems] = useState<ContractorPendingVerificationItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchPendingQueue = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await contractorService.getPendingVerificationQueue(0, 100)
      setPendingItems(data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load pending verification queue.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPendingQueue()
  }, [])

  return (
    <div className="space-y-6">
      {/* Informational Header */}
      <Card className="border-purple-200 bg-purple-50/20">
        <CardHeader className="pb-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-purple-100 rounded-lg text-purple-800 shrink-0 mt-0.5">
                <Clock className="h-5 w-5" />
              </div>
              <div>
                <CardTitle className="text-lg font-bold text-purple-950">
                  Pending Government Verification Queue
                </CardTitle>
                <p className="text-xs text-purple-800/80 mt-0.5 leading-relaxed">
                  Work orders submitted by your team awaiting official inspection and approval by municipal engineers.
                  Contractors cannot self-verify completion or mark grievances resolved.
                </p>
              </div>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={fetchPendingQueue}
              disabled={loading}
              className="text-xs gap-1.5 self-start sm:self-auto"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </Button>
          </div>
        </CardHeader>
      </Card>

      {/* Content */}
      {loading ? (
        <div className="py-16 flex flex-col items-center justify-center">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-sm text-slate-500 font-medium">Loading verification queue...</p>
        </div>
      ) : error ? (
        <Alert
          variant="error"
          title="Error Loading Verification Queue"
        >
          {error}
        </Alert>
      ) : pendingItems.length === 0 ? (
        <EmptyState
          icon={<CheckCircle2 className="h-10 w-10 text-slate-400" />}
          title="No Jobs Pending Verification"
          description="There are currently no completed work orders awaiting municipal sign-off."
        />
      ) : (
        <div className="space-y-4" data-testid="pending-verification-list">
          {pendingItems.map((item) => (
            <Card
              key={item.work_order_id}
              className="border border-purple-200/80 bg-white shadow-2xs hover:shadow-xs transition-shadow"
            >
              <CardContent className="p-5">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  {/* Left Details */}
                  <div className="space-y-2 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-slate-500">
                        WO: {item.work_order_id.slice(0, 8)}...
                      </span>
                      <PriorityBadge priority={item.priority} />
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-800 border border-purple-200">
                        <Clock className="h-3 w-3" />
                        <span>Pending Government Verification</span>
                      </span>
                    </div>

                    <h3 className="text-base font-bold text-slate-900">{item.title}</h3>

                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 pt-1">
                      <div>
                        Grievance ID: <span className="font-mono text-slate-700">{item.grievance_id.slice(0, 8)}...</span>
                      </div>
                      <div>
                        Submitted at: <span className="text-slate-700">{new Date(item.completion_submitted_at).toLocaleString()}</span>
                      </div>
                      <div className="flex items-center gap-1 text-slate-600">
                        <Paperclip className="h-3.5 w-3.5 text-slate-400" />
                        <span>{item.evidence?.length || 0} evidence file(s) attached</span>
                      </div>
                    </div>

                    {/* Attached Evidence Pills */}
                    {item.evidence && item.evidence.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-2">
                        {item.evidence.map((ev) => (
                          <span
                            key={ev.id}
                            className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-100 rounded text-[11px] text-slate-700 border border-slate-200"
                          >
                            <Paperclip className="h-3 w-3 text-slate-400" />
                            <span className="max-w-[140px] truncate">{ev.file_name}</span>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Right Actions */}
                  <div className="flex flex-col sm:items-end justify-between gap-3 shrink-0 sm:w-48 pt-3 sm:pt-0 border-t sm:border-t-0 border-slate-100">
                    <div className="text-xs text-purple-700 font-semibold bg-purple-50 px-2.5 py-1 rounded border border-purple-200 text-center sm:text-right">
                      100% Repaired
                    </div>

                    <Button
                      size="sm"
                      onClick={() => onSelectWorkOrder(item.work_order_id)}
                      className="text-xs gap-1.5 bg-purple-600 hover:bg-purple-700 text-white w-full sm:w-auto"
                      data-testid={`inspect-pending-btn-${item.work_order_id}`}
                    >
                      <span>Inspect Details</span>
                      <ExternalLink className="h-3.5 w-3.5" />
                    </Button>
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
