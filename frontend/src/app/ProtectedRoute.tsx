import React from 'react'
import { Navigate, useLocation, Outlet } from 'react-router-dom'
import { useAuth } from '../features/auth/AuthContext'
import type { UserRole } from '../types/auth'
import { LoadingSpinner } from '../components/LoadingSpinner'

export interface ProtectedRouteProps {
  allowedRoles?: UserRole[]
  children?: React.ReactNode
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ allowedRoles, children }) => {
  const { user, isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  // Prevent flash of protected content while session is being verified
  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <LoadingSpinner size="lg" message="Verifying actor credentials..." />
      </div>
    )
  }

  // Not authenticated -> redirect to login preserving intent
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // Role restriction enforcement: fails closed if role mismatch
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/unauthorized" replace />
  }

  return children ? <>{children}</> : <Outlet />
}
