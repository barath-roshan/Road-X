import React, { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  LayoutDashboard,
  ClipboardList,
  RotateCcw,
  Clock,
  Shield,
  HardHat,
} from 'lucide-react'
import { useAuth } from '../features/auth/AuthContext'
import { RoleBadge } from '../components/Badge'
import { UnauthorizedPage } from './UnauthorizedPage'
import { ContractorOverviewTab } from '../features/contractor/ContractorOverviewTab'
import { ContractorWorkOrdersTab } from '../features/contractor/ContractorWorkOrdersTab'
import { ContractorReworkQueueTab } from '../features/contractor/ContractorReworkQueueTab'
import { ContractorPendingVerificationTab } from '../features/contractor/ContractorPendingVerificationTab'
import { ContractorWorkOrderDetailModal } from '../features/contractor/ContractorWorkOrderDetailModal'
import { contractorService } from '../services/contractorService'

export type ContractorTab = 'overview' | 'work-orders' | 'rework' | 'pending-verification'

export const ContractorDashboardPage: React.FC = () => {
  const { user, isAuthenticated, hasRole } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  const tabParam = searchParams.get('tab') as ContractorTab | null
  const activeTab: ContractorTab =
    tabParam && ['overview', 'work-orders', 'rework', 'pending-verification'].includes(tabParam)
      ? tabParam
      : 'overview'

  const selectedWorkOrderIdFromUrl = searchParams.get('id')
  const [selectedWorkOrderId, setSelectedWorkOrderId] = useState<string | null>(selectedWorkOrderIdFromUrl)
  const [isModalOpen, setIsModalOpen] = useState<boolean>(Boolean(selectedWorkOrderIdFromUrl))
  const [reworkCount, setReworkCount] = useState<number>(0)

  // Fetch overview periodically or on mount to update rework tab badge
  useEffect(() => {
    contractorService
      .getOverview()
      .then((data) => setReworkCount(data.rework))
      .catch(() => {})
  }, [activeTab])

  // Sync state if URL changes externally
  useEffect(() => {
    if (selectedWorkOrderIdFromUrl) {
      setSelectedWorkOrderId(selectedWorkOrderIdFromUrl)
      setIsModalOpen(true)
    }
  }, [selectedWorkOrderIdFromUrl])

  const handleTabChange = (tab: ContractorTab, workOrderId?: string) => {
    const newParams: Record<string, string> = { tab }
    if (workOrderId) {
      newParams.id = workOrderId
      setSelectedWorkOrderId(workOrderId)
      setIsModalOpen(true)
    } else {
      setSelectedWorkOrderId(null)
      setIsModalOpen(false)
    }
    setSearchParams(newParams)
  }

  const handleOpenWorkOrder = (workOrderId: string) => {
    setSelectedWorkOrderId(workOrderId)
    setIsModalOpen(true)
    const newParams = new URLSearchParams(searchParams)
    newParams.set('id', workOrderId)
    setSearchParams(newParams)
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setSelectedWorkOrderId(null)
    const newParams = new URLSearchParams(searchParams)
    newParams.delete('id')
    setSearchParams(newParams)
  }

  // Strictly enforce Contractor role
  if (!isAuthenticated || !hasRole('CONTRACTOR')) {
    return <UnauthorizedPage />
  }

  const navItems: Array<{
    id: ContractorTab
    label: string
    icon: React.ReactNode
    badge?: number | string
    badgeColor?: string
  }> = [
    {
      id: 'overview',
      label: 'Overview & Analytics',
      icon: <LayoutDashboard className="h-4 w-4" />,
    },
    {
      id: 'work-orders',
      label: 'Assigned Work Orders',
      icon: <ClipboardList className="h-4 w-4 text-indigo-600" />,
    },
    {
      id: 'rework',
      label: 'Rework Queue',
      icon: <RotateCcw className="h-4 w-4 text-amber-600" />,
      badge: reworkCount > 0 ? reworkCount : undefined,
      badgeColor: 'bg-amber-100 text-amber-800 border-amber-300',
    },
    {
      id: 'pending-verification',
      label: 'Pending Verification',
      icon: <Clock className="h-4 w-4 text-purple-600" />,
    },
  ]

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
              <HardHat className="h-6 w-6 text-indigo-600" />
              <span>Contractor Portal</span>
            </h1>
            {user && <RoleBadge role={user.role} />}
          </div>
          <p className="text-sm text-slate-500">
            Welcome, <span className="font-semibold text-slate-700">{user?.name || user?.id}</span>.
            Execute municipal road repair orders, track progress milestones, and submit verification evidence.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-slate-50 px-3.5 py-2 rounded-lg border border-slate-200/80 text-xs text-slate-600">
          <Shield className="w-4 h-4 text-indigo-600" />
          <span>Actor: <strong className="font-mono text-slate-800">{user?.id}</strong></span>
        </div>
      </div>

      {/* Sub-Navigation Tabs */}
      <div className="border-b border-slate-200 bg-white rounded-t-xl px-4 pt-2 shadow-2xs">
        <nav className="flex space-x-1 sm:space-x-4 overflow-x-auto" aria-label="Contractor Portal Tabs">
          {navItems.map((item) => {
            const isActive = activeTab === item.id
            return (
              <button
                key={item.id}
                onClick={() => handleTabChange(item.id)}
                data-testid={`contractor-tab-${item.id}`}
                className={`flex items-center gap-2 py-3 px-3 text-xs sm:text-sm font-semibold border-b-2 transition-colors whitespace-nowrap cursor-pointer ${
                  isActive
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
                }`}
              >
                {item.icon}
                <span>{item.label}</span>
                {item.badge !== undefined && (
                  <span
                    className={`ml-1 px-1.5 py-0.2 rounded-full text-[11px] font-bold border ${
                      item.badgeColor || 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            )
          })}
        </nav>
      </div>

      {/* Tab Content Display */}
      <div className="pt-2">
        {activeTab === 'overview' && (
          <ContractorOverviewTab
            onNavigateTab={(tab) => handleTabChange(tab)}
            onSelectWorkOrder={handleOpenWorkOrder}
          />
        )}

        {activeTab === 'work-orders' && (
          <ContractorWorkOrdersTab onSelectWorkOrder={handleOpenWorkOrder} />
        )}

        {activeTab === 'rework' && (
          <ContractorReworkQueueTab onSelectWorkOrder={handleOpenWorkOrder} />
        )}

        {activeTab === 'pending-verification' && (
          <ContractorPendingVerificationTab onSelectWorkOrder={handleOpenWorkOrder} />
        )}
      </div>

      {/* Detailed Work Order Inspection & Execution Modal */}
      {selectedWorkOrderId && (
        <ContractorWorkOrderDetailModal
          workOrderId={selectedWorkOrderId}
          isOpen={isModalOpen}
          onClose={handleCloseModal}
          onOrderUpdated={() => {
            contractorService
              .getOverview()
              .then((data) => setReworkCount(data.rework))
              .catch(() => {})
          }}
        />
      )}
    </div>
  )
}
