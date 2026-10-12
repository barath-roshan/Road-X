import React, { type ReactNode } from 'react'
import { AlertCircle, CheckCircle, Info, AlertTriangle, X } from 'lucide-react'

export interface AlertProps {
  variant?: 'info' | 'success' | 'warning' | 'error'
  title?: string
  children: ReactNode
  onDismiss?: () => void
  className?: string
}

export const Alert: React.FC<AlertProps> = ({
  variant = 'info',
  title,
  children,
  onDismiss,
  className = '',
}) => {
  const styles = {
    info: {
      container: 'bg-blue-50/70 border-blue-200 text-blue-900',
      icon: <Info className="h-5 w-5 text-blue-500 shrink-0 mt-0.5" aria-hidden="true" />,
    },
    success: {
      container: 'bg-emerald-50/70 border-emerald-200 text-emerald-900',
      icon: <CheckCircle className="h-5 w-5 text-emerald-500 shrink-0 mt-0.5" aria-hidden="true" />,
    },
    warning: {
      container: 'bg-amber-50/70 border-amber-200 text-amber-900',
      icon: <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" aria-hidden="true" />,
    },
    error: {
      container: 'bg-rose-50/70 border-rose-200 text-rose-900',
      icon: <AlertCircle className="h-5 w-5 text-rose-500 shrink-0 mt-0.5" aria-hidden="true" />,
    },
  }

  const current = styles[variant]

  return (
    <div
      role="alert"
      className={`rounded-lg border p-4 text-sm flex items-start gap-3 relative ${current.container} ${className}`}
    >
      {current.icon}
      <div className="flex-1 pr-6">
        {title && <h5 className="font-semibold text-sm mb-1">{title}</h5>}
        <div className="text-sm leading-relaxed opacity-90">{children}</div>
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="absolute top-3 right-3 p-1 rounded-md text-slate-400 hover:text-slate-600 focus:outline-none"
          aria-label="Dismiss alert"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  )
}
