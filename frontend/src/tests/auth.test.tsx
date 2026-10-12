import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { AuthProvider, useAuth } from '../features/auth/AuthContext'

const TestAuthConsumer: React.FC = () => {
  const { user, isAuthenticated, isLoading, login, logout } = useAuth()

  return (
    <div>
      <div data-testid="loading-status">{isLoading ? 'loading' : 'ready'}</div>
      <div data-testid="auth-status">{isAuthenticated ? 'authenticated' : 'unauthenticated'}</div>
      <div data-testid="user-id">{user?.id || 'none'}</div>
      <div data-testid="user-role">{user?.role || 'none'}</div>
      <button
        onClick={() =>
          login({ userId: 'test-officer-1', role: 'GOVERNMENT_OFFICER', name: 'Officer Test' })
        }
      >
        Trigger Login
      </button>
      <button onClick={logout}>Trigger Logout</button>
    </div>
  )
}

describe('AuthContext and Session Restoration', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.restoreAllMocks()
  })

  it('restores authenticated actor session from sessionStorage on initial mount', async () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'persisted-user-123', role: 'CITIZEN', name: 'Persisted Citizen' })
    )

    render(
      <AuthProvider>
        <TestAuthConsumer />
      </AuthProvider>
    )

    expect(screen.getByTestId('auth-status').textContent).toBe('authenticated')
    expect(screen.getByTestId('user-id').textContent).toBe('persisted-user-123')
    expect(screen.getByTestId('user-role').textContent).toBe('CITIZEN')
  })

  it('updates state and persists session on successful login', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'healthy' }), { status: 200 })
    )

    render(
      <AuthProvider>
        <TestAuthConsumer />
      </AuthProvider>
    )

    expect(screen.getByTestId('auth-status').textContent).toBe('unauthenticated')

    await act(async () => {
      screen.getByText('Trigger Login').click()
    })

    expect(screen.getByTestId('auth-status').textContent).toBe('authenticated')
    expect(screen.getByTestId('user-id').textContent).toBe('test-officer-1')
    expect(screen.getByTestId('user-role').textContent).toBe('GOVERNMENT_OFFICER')

    const stored = sessionStorage.getItem('roadx_user')
    expect(stored).not.toBeNull()
    expect(JSON.parse(stored!).id).toBe('test-officer-1')
  })

  it('clears state and sessionStorage upon logout', async () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'user-to-logout', role: 'CONTRACTOR', name: 'Contractor X' })
    )

    render(
      <AuthProvider>
        <TestAuthConsumer />
      </AuthProvider>
    )

    expect(screen.getByTestId('auth-status').textContent).toBe('authenticated')

    act(() => {
      screen.getByText('Trigger Logout').click()
    })

    expect(screen.getByTestId('auth-status').textContent).toBe('unauthenticated')
    expect(screen.getByTestId('user-id').textContent).toBe('none')
    expect(sessionStorage.getItem('roadx_user')).toBeNull()
  })
})
