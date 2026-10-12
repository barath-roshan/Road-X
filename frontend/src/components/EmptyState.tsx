import React, { type ReactNode } from 'react'
import { Inbox } from 'lucide-react'

export interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
  className?: string
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className = '',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 text-center bg-white rounded-xl border border-dashed border-slate-300 ${className}`}
    >
      <div className="flex items-center justify-center w-12 h-12 mb-4 rounded-full bg-slate-100 text-slate-500">
        {icon || <Inbox className="w-6 h-6" aria-hidden="true" />}
      </div>
      <h4 className="text-base font-semibold text-slate-900">{title}</h4>
      {description && <p className="mt-1 text-sm text-slate-500 max-w-sm">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
