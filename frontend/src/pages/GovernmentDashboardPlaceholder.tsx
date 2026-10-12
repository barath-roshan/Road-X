import React from 'react'
import { useAuth } from '../features/auth/AuthContext'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, RoleBadge, EmptyState } from '../components'
import { Shield, BarChart3, CheckSquare, AlertOctagon } from 'lucide-react'

export const GovernmentDashboardPlaceholder: React.FC = () => {
  const { user } = useAuth()

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold text-slate-900">Government Operations Dashboard</h1>
            {user && <RoleBadge role={user.role} />}
          </div>
          <p className="text-sm text-slate-500">
            Welcome, <span className="font-semibold text-slate-700">{user?.name || user?.id}</span>. Municipal road risk ranking, work order administration, and quality verification.
          </p>
        </div>
      </div>

      {/* Explicit Phase 23 Foundation Placeholder Notice */}
      <Card className="border-indigo-100 bg-indigo-50/20">
        <CardHeader>
          <CardTitle className="text-indigo-900 text-base">Phase 23 Frontend Foundation Active</CardTitle>
          <CardDescription className="text-indigo-700/80">
            Government officer credentials and role-protected routing verified. Operational dispatch tables, map visualizations, and review flows will be implemented in subsequent phases.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
            <div className="p-4 bg-white rounded-lg border border-slate-200">
              <div className="flex items-center gap-2 text-indigo-600 font-semibold text-sm mb-1">
                <BarChart3 className="h-4 w-4" />
                <span>High-Risk Road Rankings</span>
              </div>
              <p className="text-xs text-slate-500">
                AI spatiotemporal failure probability, survival curves, and multi-criteria priority rankings.
              </p>
            </div>

            <div className="p-4 bg-white rounded-lg border border-slate-200">
              <div className="flex items-center gap-2 text-indigo-600 font-semibold text-sm mb-1">
                <CheckSquare className="h-4 w-4" />
                <span>Work Order Dispatch</span>
              </div>
              <p className="text-xs text-slate-500">
                Review citizen grievances, assign contractor work orders, and track budget allocations.
              </p>
            </div>

            <div className="p-4 bg-white rounded-lg border border-slate-200">
              <div className="flex items-center gap-2 text-indigo-600 font-semibold text-sm mb-1">
                <AlertOctagon className="h-4 w-4" />
                <span>Road Operations & Detours</span>
              </div>
              <p className="text-xs text-slate-500">
                Publish municipal road closures, maintenance restrictions, and official detour routes.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Empty State Indicator */}
      <EmptyState
        icon={<Shield className="w-8 h-8 text-indigo-500" />}
        title="Government Portal Ready for Implementation"
        description="Your actor credentials (X-Actor-User-ID: government_officer) are authenticated. Complete municipal analytics tables and work order approval actions are queued for the government dashboard phase."
      />
    </div>
  )
}
