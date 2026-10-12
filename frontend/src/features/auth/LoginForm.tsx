import React, { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'
import type { UserRole } from '../../types/auth'
import { Button, Input, Alert, Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components'
import { Shield, HardHat, User as UserIcon } from 'lucide-react'

export const LoginForm: React.FC = () => {
  const { login, isLoading, error: authError, clearError } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [role, setRole] = useState<UserRole>('CITIZEN')
  const [userId, setUserId] = useState('citizen-smoke-1')
  const [name, setName] = useState('')
  const [fieldErrors, setFieldErrors] = useState<{ userId?: string }>({})

  // Determine redirection target
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname

  const handleRoleChange = (newRole: UserRole) => {
    setRole(newRole)
    clearError()
    setFieldErrors({})
    // Set appropriate demo ID preset for convenience
    if (newRole === 'GOVERNMENT_OFFICER') {
      setUserId('officer-smoke-1')
    } else if (newRole === 'CONTRACTOR') {
      setUserId('contractor-smoke-1')
    } else {
      setUserId('citizen-smoke-1')
    }
  }

  const validate = (): boolean => {
    const errors: { userId?: string } = {}
    if (!userId.trim()) {
      errors.userId = 'User ID is required to identify your actor in RoadX.'
    }
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()

    if (!validate()) {
      return
    }

    try {
      const user = await login({
        userId: userId.trim(),
        role,
        name: name.trim() || undefined,
      })

      // Destination mapping based on role
      const defaultDest =
        user.role === 'GOVERNMENT_OFFICER'
          ? '/government'
          : user.role === 'CONTRACTOR'
          ? '/contractor'
          : '/citizen'

      const destination = from && !from.includes('/login') ? from : defaultDest
      navigate(destination, { replace: true })
    } catch {
      // Error handled by AuthContext state
    }
  }

  return (
    <Card className="w-full max-w-md shadow-lg border-slate-200">
      <CardHeader className="text-center pb-4">
        <CardTitle className="text-xl text-slate-900">Sign in to RoadX</CardTitle>
        <CardDescription>Select your platform role and enter your verified actor ID</CardDescription>
      </CardHeader>
      <CardContent>
        {authError && (
          <Alert variant="error" className="mb-5" onDismiss={clearError}>
            {authError}
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          {/* Role Selection Tabs */}
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
              Select Governance Role
            </label>
            <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label="Governance Role">
              <button
                type="button"
                onClick={() => handleRoleChange('CITIZEN')}
                className={`flex flex-col items-center justify-center p-3 rounded-lg border text-xs font-medium transition-all cursor-pointer ${
                  role === 'CITIZEN'
                    ? 'border-indigo-600 bg-indigo-50/50 text-indigo-700 ring-1 ring-indigo-600'
                    : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                }`}
                role="radio"
                aria-checked={role === 'CITIZEN'}
              >
                <UserIcon className="h-5 w-5 mb-1.5" />
                <span>Citizen</span>
              </button>

              <button
                type="button"
                onClick={() => handleRoleChange('GOVERNMENT_OFFICER')}
                className={`flex flex-col items-center justify-center p-3 rounded-lg border text-xs font-medium transition-all cursor-pointer ${
                  role === 'GOVERNMENT_OFFICER'
                    ? 'border-indigo-600 bg-indigo-50/50 text-indigo-700 ring-1 ring-indigo-600'
                    : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                }`}
                role="radio"
                aria-checked={role === 'GOVERNMENT_OFFICER'}
              >
                <Shield className="h-5 w-5 mb-1.5" />
                <span>Officer</span>
              </button>

              <button
                type="button"
                onClick={() => handleRoleChange('CONTRACTOR')}
                className={`flex flex-col items-center justify-center p-3 rounded-lg border text-xs font-medium transition-all cursor-pointer ${
                  role === 'CONTRACTOR'
                    ? 'border-indigo-600 bg-indigo-50/50 text-indigo-700 ring-1 ring-indigo-600'
                    : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                }`}
                role="radio"
                aria-checked={role === 'CONTRACTOR'}
              >
                <HardHat className="h-5 w-5 mb-1.5" />
                <span>Contractor</span>
              </button>
            </div>
          </div>

          {/* User ID Input */}
          <Input
            id="user-id-input"
            label="Actor User ID"
            placeholder="e.g. officer-smoke-1, citizen-123"
            value={userId}
            onChange={(e) => {
              setUserId(e.target.value)
              if (fieldErrors.userId) {
                setFieldErrors((prev) => ({ ...prev, userId: undefined }))
              }
            }}
            error={fieldErrors.userId}
            helperText="Header-based actor identifier sent with all authorized API requests"
            required
            autoComplete="username"
          />

          {/* Display Name Input (Optional) */}
          <Input
            id="name-input"
            label="Display Name (Optional)"
            placeholder="e.g. Officer Raman, Jane Doe"
            value={name}
            onChange={(e) => setName(e.target.value)}
            helperText="Used for UI display in navigation bar"
          />

          <Button type="submit" fullWidth isLoading={isLoading} className="mt-2">
            Sign In as {role.replace('_', ' ')}
          </Button>

          <div className="text-center pt-2">
            <p className="text-xs text-slate-400">
              RoadX uses header-based actor identity context verified on each API request.
            </p>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
