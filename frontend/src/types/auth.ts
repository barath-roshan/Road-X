/**
 * Authentication and User Role types matching RoadX backend governance model.
 */

export type UserRole = 'CITIZEN' | 'GOVERNMENT_OFFICER' | 'CONTRACTOR'

export interface AuthUser {
  id: string
  name: string
  email?: string
  role: UserRole
  phone?: string
}

export interface LoginCredentials {
  userId: string
  role: UserRole
  name?: string
  email?: string
}

export interface AuthState {
  user: AuthUser | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
}
