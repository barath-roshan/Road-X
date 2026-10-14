import React from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  LayoutDashboard,
  PlusCircle,
  FileText,
  AlertOctagon,
  MessageSquare,
  Shield,
} from 'lucide-react'
import { useAuth } from '../features/auth/AuthContext'
import { RoleBadge } from '../components/Badge'
import { UnauthorizedPage } from './UnauthorizedPage'
import { CitizenOverviewTab } from '../features/citizen/CitizenOverviewTab'
import { ReportGrievanceTab } from '../features/citizen/ReportGrievanceTab'
import { CitizenGrievancesTab } from '../features/citizen/CitizenGrievancesTab'
import { CitizenRoadOperationsTab } from '../features/citizen/CitizenRoadOperationsTab'
import { CitizenChatbotTab } from '../features/citizen/CitizenChatbotTab'

export type CitizenTab = 'overview' | 'report' | 'my-grievances' | 'road-operations' | 'chatbot'

export const CitizenPortalPage: React.FC = () => {
  const { user, isAuthenticated, hasRole } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  const tabParam = searchParams.get('tab') as CitizenTab | null
  const activeTab: CitizenTab =
    tabParam && ['overview', 'report', 'my-grievances', 'road-operations', 'chatbot'].includes(tabParam)
      ? tabParam
      : 'overview'
  const selectedGrievanceId = searchParams.get('id')

  const handleTabChange = (tab: CitizenTab, grievanceId?: string) => {
    const newParams: Record<string, string> = { tab }
    if (grievanceId) {
      newParams.id = grievanceId
    }
    setSearchParams(newParams)
  }

  // Strictly enforce Citizen role
  if (!isAuthenticated || !hasRole('CITIZEN')) {
    return <UnauthorizedPage />
  }

  const navItems: Array<{
    id: CitizenTab
    label: string
    icon: React.ReactNode
    badge?: string
  }> = [
    {
      id: 'overview',
      label: 'Home & Overview',
      icon: <LayoutDashboard className="h-4 w-4" />,
    },
    {
      id: 'report',
      label: 'Report a Problem',
      icon: <PlusCircle className="h-4 w-4 text-blue-600" />,
    },
    {
      id: 'my-grievances',
      label: 'My Grievances',
      icon: <FileText className="h-4 w-4" />,
    },
    {
      id: 'road-operations',
      label: 'Road Operations & Detours',
      icon: <AlertOctagon className="h-4 w-4 text-rose-500" />,
    },
    {
      id: 'chatbot',
      label: 'RoadX AI Assistant',
      icon: <MessageSquare className="h-4 w-4 text-indigo-500" />,
    },
  ]

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold text-slate-900">Citizen Platform</h1>
            {user && <RoleBadge role={user.role} />}
          </div>
          <p className="text-sm text-slate-500">
            Welcome, <span className="font-semibold text-slate-700">{user?.name || user?.id}</span>.
            Report road damage, track repair milestones, and view municipal traffic advisories.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-slate-50 px-3.5 py-2 rounded-lg border border-slate-200/80 text-xs text-slate-600">
          <Shield className="w-4 h-4 text-blue-600" />
          <span>Actor: <strong className="font-mono text-slate-800">{user?.id}</strong></span>
        </div>
      </div>

      {/* Sub-Navigation Tabs */}
      <div className="border-b border-slate-200 bg-white rounded-t-xl px-2 shadow-2xs">
        <nav className="flex space-x-1 sm:space-x-2 overflow-x-auto py-2" aria-label="Citizen portal tabs">
          {navItems.map((item) => {
            const isActive = activeTab === item.id
            return (
              <button
                key={item.id}
                type="button"
                data-testid={`citizen-tab-${item.id}`}
                onClick={() => handleTabChange(item.id)}
                className={`flex items-center gap-2 px-3.5 py-2 text-xs sm:text-sm font-semibold rounded-lg transition-all shrink-0 ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 shadow-2xs border border-blue-200'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
                aria-current={isActive ? 'page' : undefined}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            )
          })}
        </nav>
      </div>

      {/* Active Tab Content */}
      <div className="min-h-[480px]">
        {activeTab === 'overview' && (
          <CitizenOverviewTab
            onNavigateToTab={(tab) => handleTabChange(tab)}
            onSelectGrievance={(id) => handleTabChange('my-grievances', id)}
          />
        )}

        {activeTab === 'report' && (
          <ReportGrievanceTab
            onGrievanceCreated={(g) => handleTabChange('my-grievances', g.id)}
            onNavigateToMyGrievances={() => handleTabChange('my-grievances')}
          />
        )}

        {activeTab === 'my-grievances' && (
          <CitizenGrievancesTab
            onNavigateToReport={() => handleTabChange('report')}
            initialSelectedId={selectedGrievanceId}
          />
        )}

        {activeTab === 'road-operations' && <CitizenRoadOperationsTab />}

        {activeTab === 'chatbot' && <CitizenChatbotTab />}
      </div>
    </div>
  )
}
