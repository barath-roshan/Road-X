import React, { useEffect, useState } from 'react'
import {
  RotateCcw,
  RefreshCw,
  ExternalLink,
  CheckCircle2,
  MessageSquare,
} from 'lucide-react'
import { contractorService } from '../../services/contractorService'
import type { ContractorReworkItem } from '../../types/contractor'
import { Card, CardHeader, CardTitle, CardContent } from '../../components/Card'
import { Button } from '../../components/Button'
import { Alert } from '../../components/Alert'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { EmptyState } from '../../components/EmptyState'
import { PriorityBadge, StatusBadge } from '../../components/Badge'

interface ContractorReworkQueueTabProps {
  onSelectWorkOrder: (workOrderId: string) => void
}

export const ContractorReworkQueueTab: React.FC<ContractorReworkQueueTabProps> = ({
  onSelectWorkOrder,
}) => {
  const [reworkItems, setReworkItems] = useState<ContractorReworkItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchReworkQueue = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await contractorService.getReworkQueue(0, 100)
      setReworkItems(data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load rework queue.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchReworkQueue()
  }, [])

  return (
    <div className="space-y-6">
      {/* Informational Header */}
      <Card className="border-amber-200 bg-amber-50/20">
        <CardHeader className="pb-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-amber-100 rounded-lg text-amber-800 shrink-0 mt-0.5">
                <RotateCcw className="h-5 w-5" />
              </div>
              <div>
                <CardTitle className="text-lg font-bold text-amber-950">
                  Government Rework Feedback Queue
                </CardTitle>
                <p className="text-xs text-amber-800/80 mt-0.5 leading-relaxed">
                  Work orders returned by municipal verification engineers. Review specific rejection notes, perform corrective repair actions, update progress, and resubmit for verification.
                </p>
              </div>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={fetchReworkQueue}
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
          <p className="mt-4 text-sm text-slate-500 font-medium">Loading rework queue...</p>
        </div>
      ) : error ? (
        <Alert
          variant="error"
          title="Error Loading Rework Queue"
        >
          {error}
        </Alert>
      ) : reworkItems.length === 0 ? (
        <EmptyState
          icon={<CheckCircle2 className="h-10 w-10 text-emerald-500" />}
          title="No Rework Pending"
          description="Great job! There are currently no work orders rejected or flagged for rework by municipal engineers."
        />
      ) : (
        <div className="space-y-4" data-testid="rework-queue-list">
          {reworkItems.map((item) => (
            <Card
              key={item.work_order_id}
              className="border-2 border-amber-300 bg-white shadow-xs overflow-hidden"
            >
              <div className="bg-amber-100/60 px-5 py-2.5 border-b border-amber-200 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-amber-900">
                    WO: {item.work_order_id.slice(0, 8)}...
                  </span>
                  <PriorityBadge priority={item.priority} />
                  <StatusBadge status={item.current_status} />
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold bg-amber-200/80 text-amber-900 border border-amber-300">
                    <RotateCcw className="h-3 w-3" />
                    <span>Rework Required</span>
                  </span>
                </div>
                {item.rejection_timestamp && (
                  <span className="text-[11px] text-amber-800">
                    Rejected on {new Date(item.rejection_timestamp).toLocaleString()}
                  </span>
                )}
              </div>

              <CardContent className="p-5 space-y-4">
                <div>
                  <h3 className="text-base font-bold text-slate-900">{item.title}</h3>
                  <div className="text-xs text-slate-500 mt-0.5">
                    Grievance ID: <span className="font-mono text-slate-700">{item.grievance_id}</span>
                  </div>
                </div>

                {/* Government Rejection Feedback Box */}
                <div className="bg-amber-50 rounded-xl p-4 border border-amber-300/80 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-amber-900">
                    <MessageSquare className="h-4 w-4 text-amber-700" />
                    <span>Government Officer Rejection Feedback:</span>
                  </div>
                  <p className="text-xs text-amber-950 font-medium leading-relaxed bg-white/80 p-3 rounded-lg border border-amber-200">
                    "{item.rejection_message}"
                  </p>
                </div>

                {/* Footer with Progress & Action */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t border-slate-100">
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-slate-500">Current Progress:</span>
                    <span className="text-xs font-bold text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded border border-indigo-200">
                      {item.current_progress}%
                    </span>
                  </div>

                  <Button
                    size="sm"
                    onClick={() => onSelectWorkOrder(item.work_order_id)}
                    className="bg-amber-600 hover:bg-amber-700 text-white text-xs gap-1.5 self-end sm:self-auto shadow-xs"
                    data-testid={`address-rework-btn-${item.work_order_id}`}
                  >
                    <span>Address Rework & Resubmit</span>
                    <ExternalLink className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
