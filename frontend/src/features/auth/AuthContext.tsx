/**
 * Authentication Context managing actor session state, login, and logout.
 */

import React, { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import type { AuthState, AuthUser, LoginCredentials, UserRole } from '../../types/auth'
import { apiClient } from '../../services/apiClient'

interface AuthContextValue extends AuthState {
  login: (credentials: LoginCredentials) => Promise<AuthUser>
  logout: () => void
  clearError: () => void
  hasRole: (role: UserRole) => boolean
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

const SESSION_STORAGE_KEY = 'roadx_user'

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
    error: null,
  })

  // Restore session from sessionStorage on initial load
  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(SESSION_STORAGE_KEY)
      if (stored) {
        const user: AuthUser = JSON.parse(stored)
        if (user && user.id && user.role) {
          setState({
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          })
          return
        }
      }
    } catch {
      // In case of corrupt storage, clear it
      sessionStorage.removeItem(SESSION_STORAGE_KEY)
    }

    setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    })
  }, [])

  const login = useCallback(async (credentials: LoginCredentials): Promise<AuthUser> => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }))

    try {
      const trimmedUserId = credentials.userId.trim()
      if (!trimmedUserId) {
        throw new Error('User ID is required.')
      }

      // Verify server liveness using apiClient
      await apiClient.get('/health')

      const user: AuthUser = {
        id: trimmedUserId,
        role: credentials.role,
        name: credentials.name?.trim() || `${credentials.role.toLowerCase()}-${trimmedUserId.slice(0, 8)}`,
        email: credentials.email?.trim(),
      }

      // Secure session storage for development actor identity (never store passwords)
      sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(user))

      setState({
        user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      })

      return user
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Authentication failed. Please verify credentials.'
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: message,
      }))
      throw err
    }
  }, [])

  const logout = useCallback(() => {
    sessionStorage.removeItem(SESSION_STORAGE_KEY)
    setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    })
  }, [])

  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }))
  }, [])

  const hasRole = useCallback((role: UserRole) => {
    return state.user?.role === role
  }, [state.user])

  const value: AuthContextValue = {
    ...state,
    login,
    logout,
    clearError,
    hasRole,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = (): AuthContextValue => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
