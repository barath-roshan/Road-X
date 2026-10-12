import React, { useEffect, useState } from 'react'
import {
  HardHat,
  RefreshCw,
  Mail,
} from 'lucide-react'
import { Card, CardHeader, CardContent } from '../../components/Card'
import { Button } from '../../components/Button'
import { Alert } from '../../components/Alert'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { EmptyState } from '../../components/EmptyState'
import { governmentService } from '../../services/governmentService'
import type { GovernmentDashboardContractorSummary } from '../../types/government'

export const GovernmentContractorsTab: React.FC = () => {
  const [contractors, setContractors] = useState<GovernmentDashboardContractorSummary[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const fetchContractors = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await governmentService.listContractors()
      setContractors(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load contractor summaries.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchContractors()
  }, [])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Contractor Monitoring</h2>
          <p className="text-xs text-slate-500">
            Read-only audit of registered municipal contractors, workload distributions, and completion performance.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchContractors}
          className="self-start sm:self-auto flex items-center gap-1.5 text-slate-600"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </Button>
      </div>

      {error && (
        <Alert variant="error" title="Contractor Audit Error" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      {isLoading ? (
        <div className="py-16 flex justify-center">
          <LoadingSpinner size="lg" message="Loading contractor workload metrics..." />
        </div>
      ) : contractors.length === 0 ? (
        <EmptyState
          title="No Registered Contractors"
          description="There are currently no contractor users registered in the municipal database."
        />
      ) : (
        <div className="space-y-6">
          {/* Contractor Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {contractors.map((c) => {
              const avgProgress = Math.round(c.average_progress_percentage || 0)

              return (
                <Card key={c.contractor_id} className="hover:border-slate-300 transition-all shadow-2xs">
                  <CardHeader className="pb-3 border-b border-slate-100 flex flex-row items-center justify-between space-y-0">
                    <div className="flex items-center space-x-2.5">
                      <div className="h-9 w-9 rounded-lg bg-amber-50 text-amber-700 flex items-center justify-center">
                        <HardHat className="h-5 w-5" />
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-slate-900">{c.contractor_name}</h4>
                        <p className="text-[11px] text-slate-400 flex items-center gap-1">
                          <Mail className="h-3 w-3" />
                          {c.contractor_email}
                        </p>
                      </div>
                    </div>
                  </CardHeader>

                  <CardContent className="p-4 space-y-3 text-xs">
                    <div className="grid grid-cols-2 gap-2 text-slate-600">
                      <div className="p-2 bg-slate-50 rounded-lg">
                        <span className="text-[10px] uppercase font-semibold text-slate-400 block">
                          Total Assigned
                        </span>
                        <span className="text-base font-bold text-slate-900 mt-0.5 block">
                          {c.assigned_work_orders_count}
                        </span>
                      </div>

                      <div className="p-2 bg-indigo-50/50 rounded-lg">
                        <span className="text-[10px] uppercase font-semibold text-indigo-500 block">
                          In Progress
                        </span>
                        <span className="text-base font-bold text-indigo-700 mt-0.5 block">
                          {c.in_progress_count}
                        </span>
                      </div>

                      <div className="p-2 bg-amber-50/50 rounded-lg">
                        <span className="text-[10px] uppercase font-semibold text-amber-600 block">
                          Pending Verification
                        </span>
                        <span className="text-base font-bold text-amber-800 mt-0.5 block">
                          {c.pending_verification_count}
                        </span>
                      </div>

                      <div className="p-2 bg-emerald-50/50 rounded-lg">
                        <span className="text-[10px] uppercase font-semibold text-emerald-600 block">
                          Completed
                        </span>
                        <span className="text-base font-bold text-emerald-800 mt-0.5 block">
                          {c.completed_count}
                        </span>
                      </div>
                    </div>

                    {/* Average Progress Bar */}
                    <div className="space-y-1 pt-1">
                      <div className="flex justify-between text-[11px]">
                        <span className="font-medium text-slate-500">Average Active Progress</span>
                        <span className="font-bold text-slate-800">{avgProgress}%</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                        <div
                          className="bg-amber-500 h-1.5 rounded-full"
                          style={{ width: `${avgProgress}%` }}
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
