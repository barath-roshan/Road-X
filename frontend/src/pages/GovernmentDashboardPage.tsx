import React, { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  LayoutDashboard,
  FileText,
  AlertTriangle,
  Briefcase,
  CheckCircle2,
  HardHat,
  AlertOctagon,
  Shield,
} from 'lucide-react'
import { useAuth } from '../features/auth/AuthContext'
import { RoleBadge } from '../components/Badge'
import { UnauthorizedPage } from './UnauthorizedPage'
import { GovernmentOverviewTab } from '../features/government/GovernmentOverviewTab'
import { GovernmentGrievancesTab } from '../features/government/GovernmentGrievancesTab'
import { GovernmentPriorityQueueTab } from '../features/government/GovernmentPriorityQueueTab'
import { GovernmentWorkOrdersTab } from '../features/government/GovernmentWorkOrdersTab'
import { GovernmentVerificationQueueTab } from '../features/government/GovernmentVerificationQueueTab'
import { GovernmentContractorsTab } from '../features/government/GovernmentContractorsTab'
import { GovernmentRoadOperationsTab } from '../features/government/GovernmentRoadOperationsTab'

export type GovernmentTab =
  | 'overview'
  | 'grievances'
  | 'priority-queue'
  | 'work-orders'
  | 'verifications'
  | 'contractors'
  | 'road-operations'

export const GovernmentDashboardPage: React.FC = () => {
  const { user, isAuthenticated, hasRole } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialTab = (searchParams.get('tab') as GovernmentTab) || 'overview'
  const [activeTab, setActiveTab] = useState<GovernmentTab>(initialTab)

  // Sync tab with URL search parameter
  useEffect(() => {
    const tabParam = searchParams.get('tab') as GovernmentTab
    if (tabParam && tabParam !== activeTab) {
      setActiveTab(tabParam)
    }
  }, [searchParams])

  const handleTabChange = (tab: GovernmentTab) => {
    setActiveTab(tab)
    setSearchParams({ tab })
  }

  // Enforce Government Officer role
  if (!isAuthenticated || !hasRole('GOVERNMENT_OFFICER')) {
    return <UnauthorizedPage />
  }

  const navItems: Array<{
    id: GovernmentTab
    label: string
    icon: React.ReactNode
    badge?: string
  }> = [
    {
      id: 'overview',
      label: 'Overview',
      icon: <LayoutDashboard className="h-4 w-4" />,
    },
    {
      id: 'grievances',
      label: 'Grievance Review',
      icon: <FileText className="h-4 w-4" />,
    },
    {
      id: 'priority-queue',
      label: 'Priority Queue',
      icon: <AlertTriangle className="h-4 w-4 text-amber-500" />,
    },
    {
      id: 'work-orders',
      label: 'Work Orders',
      icon: <Briefcase className="h-4 w-4" />,
    },
    {
      id: 'verifications',
      label: 'Verification Queue',
      icon: <CheckCircle2 className="h-4 w-4 text-emerald-500" />,
    },
    {
      id: 'contractors',
      label: 'Contractors',
      icon: <HardHat className="h-4 w-4" />,
    },
    {
      id: 'road-operations',
      label: 'Road Operations',
      icon: <AlertOctagon className="h-4 w-4 text-rose-500" />,
    },
  ]

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Top Welcome & Officer Profile Banner */}
      <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3.5">
          <div className="h-11 w-11 rounded-xl bg-indigo-600 text-white flex items-center justify-center shadow-xs">
            <Shield className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-slate-900 tracking-tight">
                Government Officer Portal
              </h1>
              <RoleBadge role="GOVERNMENT_OFFICER" />
            </div>
            <p className="text-xs text-slate-500">
              Authenticated Officer: <span className="font-semibold text-slate-800">{user?.name || user?.id}</span> (Officer ID: <span className="font-mono text-slate-600">{user?.id}</span>)
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2 text-xs text-slate-500 bg-slate-50 py-1.5 px-3 rounded-lg border border-slate-200">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Municipal Operations Online</span>
        </div>
      </div>

      {/* Navigation Sub-Tabs Bar */}
      <div className="border-b border-slate-200 bg-white rounded-t-xl px-2 shadow-2xs">
        <nav className="flex space-x-1 overflow-x-auto py-2" aria-label="Dashboard Tabs">
          {navItems.map((item) => {
            const isActive = activeTab === item.id
            return (
              <button
                key={item.id}
                onClick={() => handleTabChange(item.id)}
                className={`flex items-center space-x-2 px-3.5 py-2.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors cursor-pointer ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-700 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
                aria-current={isActive ? 'page' : undefined}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </button>
            )
          })}
        </nav>
      </div>

      {/* Active Tab Content Area */}
      <main className="bg-white rounded-b-xl border border-t-0 border-slate-200/90 p-6 shadow-2xs min-h-[500px]">
        {activeTab === 'overview' && (
          <GovernmentOverviewTab onNavigateTab={(tab) => handleTabChange(tab as GovernmentTab)} />
        )}
        {activeTab === 'grievances' && <GovernmentGrievancesTab />}
        {activeTab === 'priority-queue' && <GovernmentPriorityQueueTab />}
        {activeTab === 'work-orders' && <GovernmentWorkOrdersTab />}
        {activeTab === 'verifications' && <GovernmentVerificationQueueTab />}
        {activeTab === 'contractors' && <GovernmentContractorsTab />}
        {activeTab === 'road-operations' && <GovernmentRoadOperationsTab />}
      </main>
    </div>
  )
}
