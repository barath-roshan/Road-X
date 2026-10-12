import React from 'react'
import { useAuth } from '../features/auth/AuthContext'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, RoleBadge, EmptyState } from '../components'
import { User, MessageSquare, AlertTriangle, Clock } from 'lucide-react'

export const CitizenDashboardPlaceholder: React.FC = () => {
  const { user } = useAuth()

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold text-slate-900">Citizen Platform</h1>
            {user && <RoleBadge role={user.role} />}
          </div>
          <p className="text-sm text-slate-500">
            Welcome, <span className="font-semibold text-slate-700">{user?.name || user?.id}</span>. Report road damage, track repair progress, and communicate with road authorities.
          </p>
        </div>
      </div>

      {/* Explicit Phase 23 Foundation Placeholder Notice */}
      <Card className="border-indigo-100 bg-indigo-50/20">
        <CardHeader>
          <CardTitle className="text-indigo-900 text-base">Phase 23 Frontend Foundation Active</CardTitle>
          <CardDescription className="text-indigo-700/80">
            Authentication, role-aware routing, and the centralized API client are active. Full interactive citizen features are scheduled for subsequent dashboard implementation phases.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
            <div className="p-4 bg-white rounded-lg border border-slate-200">
              <div className="flex items-center gap-2 text-indigo-600 font-semibold text-sm mb-1">
                <AlertTriangle className="h-4 w-4" />
                <span>Grievance Reporting</span>
              </div>
              <p className="text-xs text-slate-500">
                Submit damage photos, GPS coordinates, and road condition descriptions to trigger ML failure analysis.
              </p>
            </div>

            <div className="p-4 bg-white rounded-lg border border-slate-200">
              <div className="flex items-center gap-2 text-indigo-600 font-semibold text-sm mb-1">
                <Clock className="h-4 w-4" />
                <span>Repair Timeline</span>
              </div>
              <p className="text-xs text-slate-500">
                Track submitted reports from review to contractor assignment, repair completion, and government verification.
              </p>
            </div>

            <div className="p-4 bg-white rounded-lg border border-slate-200">
              <div className="flex items-center gap-2 text-indigo-600 font-semibold text-sm mb-1">
                <MessageSquare className="h-4 w-4" />
                <span>AI Citizen Assistant</span>
              </div>
              <p className="text-xs text-slate-500">
                Conversational RAG assistant answering road closure queries and grievance status updates in real time.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Empty State Indicator */}
      <EmptyState
        icon={<User className="w-8 h-8 text-indigo-500" />}
        title="Citizen Dashboard Ready for Implementation"
        description="Your actor credentials (X-Actor-User-ID: citizen) are active and verified. Comprehensive grievance intake forms and photo upload widgets will be connected in the citizen portal phase."
      />
    </div>
  )
}
