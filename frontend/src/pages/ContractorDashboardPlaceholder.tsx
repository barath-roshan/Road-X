import React from 'react'
import { useAuth } from '../features/auth/AuthContext'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, RoleBadge, EmptyState } from '../components'
import { HardHat, ClipboardList, Camera, CheckCircle } from 'lucide-react'

export const ContractorDashboardPlaceholder: React.FC = () => {
  const { user } = useAuth()

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold text-slate-900">Contractor Portal</h1>
            {user && <RoleBadge role={user.role} />}
          </div>
          <p className="text-sm text-slate-500">
            Welcome, <span className="font-semibold text-slate-700">{user?.name || user?.id}</span>. Maintenance job orders, repair progress tracking, and completion verification submissions.
          </p>
        </div>
      </div>

      {/* Explicit Phase 23 Foundation Placeholder Notice */}
      <Card className="border-indigo-100 bg-indigo-50/20">
        <CardHeader>
          <CardTitle className="text-indigo-900 text-base">Phase 23 Frontend Foundation Active</CardTitle>
          <CardDescription className="text-indigo-700/80">
            Contractor identity headers and protected routes are confirmed. Job queues, progress status updates, and repair evidence upload widgets will be built in the contractor portal phase.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
            <div className="p-4 bg-white rounded-lg border border-slate-200">
              <div className="flex items-center gap-2 text-indigo-600 font-semibold text-sm mb-1">
                <ClipboardList className="h-4 w-4" />
                <span>Assigned Work Orders</span>
              </div>
              <p className="text-xs text-slate-500">
                Receive and acknowledge road repair jobs dispatched by municipal engineers.
              </p>
            </div>

            <div className="p-4 bg-white rounded-lg border border-slate-200">
              <div className="flex items-center gap-2 text-indigo-600 font-semibold text-sm mb-1">
                <Camera className="h-4 w-4" />
                <span>Evidence Submissions</span>
              </div>
              <p className="text-xs text-slate-500">
                Upload post-repair photographic evidence and inspection reports for verification.
              </p>
            </div>

            <div className="p-4 bg-white rounded-lg border border-slate-200">
              <div className="flex items-center gap-2 text-indigo-600 font-semibold text-sm mb-1">
                <CheckCircle className="h-4 w-4" />
                <span>Verification & Quality</span>
              </div>
              <p className="text-xs text-slate-500">
                Monitor government officer verification decisions and manage rework feedback notes.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Empty State Indicator */}
      <EmptyState
        icon={<HardHat className="w-8 h-8 text-indigo-500" />}
        title="Contractor Portal Ready for Implementation"
        description="Your actor credentials (X-Actor-User-ID: contractor) are validated. Active work order queues and photo evidence upload forms will be linked in the contractor dashboard phase."
      />
    </div>
  )
}
