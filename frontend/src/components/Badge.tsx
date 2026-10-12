import React, { type ReactNode } from 'react'
import type { UserRole } from '../types/auth'

export interface BadgeProps {
  children: ReactNode
  variant?: 'default' | 'citizen' | 'officer' | 'contractor' | 'success' | 'warning' | 'danger'
  className?: string
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'default', className = '' }) => {
  const styles = {
    default: 'bg-slate-100 text-slate-700 border-slate-200',
    citizen: 'bg-blue-50 text-blue-700 border-blue-200',
    officer: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    contractor: 'bg-amber-50 text-amber-700 border-amber-200',
    success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    warning: 'bg-amber-50 text-amber-700 border-amber-200',
    danger: 'bg-rose-50 text-rose-700 border-rose-200',
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${styles[variant]} ${className}`}
    >
      {children}
    </span>
  )
}

export const RoleBadge: React.FC<{ role: UserRole; className?: string }> = ({ role, className = '' }) => {
  const roleConfig: Record<UserRole, { label: string; variant: 'citizen' | 'officer' | 'contractor' }> = {
    CITIZEN: { label: 'Citizen', variant: 'citizen' },
    GOVERNMENT_OFFICER: { label: 'Government Officer', variant: 'officer' },
    CONTRACTOR: { label: 'Contractor', variant: 'contractor' },
  }

  const config = roleConfig[role] || { label: role, variant: 'default' }

  return (
    <Badge variant={config.variant} className={className}>
      {config.label}
    </Badge>
  )
}
