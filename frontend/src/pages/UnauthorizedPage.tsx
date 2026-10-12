import React from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../features/auth/AuthContext'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter, Button, RoleBadge } from '../components'
import { ShieldAlert, ArrowLeft, LogIn } from 'lucide-react'

export const UnauthorizedPage: React.FC = () => {
  const { user } = useAuth()

  const authorizedHome =
    user?.role === 'GOVERNMENT_OFFICER'
      ? '/government'
      : user?.role === 'CONTRACTOR'
      ? '/contractor'
      : user?.role === 'CITIZEN'
      ? '/citizen'
      : '/login'

  return (
    <div className="max-w-xl mx-auto py-12">
      <Card className="border-rose-200 shadow-sm">
        <CardHeader className="text-center pb-2 bg-rose-50/40">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-rose-100 text-rose-600 mb-3">
            <ShieldAlert className="h-8 w-8" />
          </div>
          <CardTitle className="text-xl text-rose-900">403 — Access Restricted</CardTitle>
          <CardDescription className="text-rose-700/80">
            Your current account role does not have authorization to access this portal or resource.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4 pt-6">
          <div className="rounded-lg bg-slate-50 border border-slate-200 p-4 text-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-slate-500 font-medium">Active User ID:</span>
              <span className="font-mono text-slate-800">{user?.id || 'Unknown'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500 font-medium">Assigned Role:</span>
              {user ? <RoleBadge role={user.role} /> : <span className="text-slate-400">None</span>}
            </div>
          </div>

          <p className="text-sm text-slate-600 leading-relaxed">
            RoadX enforces strict actor-role boundaries. Government administrative features, contractor work orders, and citizen grievance private histories are separated by role authorization rules enforced on the backend.
          </p>
        </CardContent>

        <CardFooter className="flex-col sm:flex-row gap-3 pt-4">
          <Link to={authorizedHome} className="w-full sm:w-auto">
            <Button variant="primary" className="w-full sm:w-auto flex items-center gap-2">
              <ArrowLeft className="h-4 w-4" />
              Return to Your Portal
            </Button>
          </Link>
          <Link to="/login" className="w-full sm:w-auto">
            <Button variant="outline" className="w-full sm:w-auto flex items-center gap-2">
              <LogIn className="h-4 w-4" />
              Switch Account Role
            </Button>
          </Link>
        </CardFooter>
      </Card>
    </div>
  )
}
