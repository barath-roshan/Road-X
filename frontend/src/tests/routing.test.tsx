import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../features/auth/AuthContext'
import { AppRoutes } from '../app/AppRoutes'

describe('Role-Aware Routing & Protected Route Enforcement', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.restoreAllMocks()
  })

  it('redirects unauthenticated visitor to /login when navigating to /government', () => {
    render(
      <MemoryRouter initialEntries={['/government']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )

    // Should render the Login page heading
    expect(screen.getByRole('heading', { name: /sign in to roadx/i })).toBeInTheDocument()
  })

  it('allows authenticated citizen to view /citizen', () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'citizen-101', role: 'CITIZEN', name: 'Citizen Alice' })
    )

    render(
      <MemoryRouter initialEntries={['/citizen']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )

    expect(screen.getByRole('heading', { name: /citizen platform/i })).toBeInTheDocument()
    expect(screen.getByText(/phase 23 frontend foundation active/i)).toBeInTheDocument()
  })

  it('blocks authenticated citizen from accessing /government and redirects to /unauthorized', () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'citizen-101', role: 'CITIZEN', name: 'Citizen Alice' })
    )

    render(
      <MemoryRouter initialEntries={['/government']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )

    expect(screen.getByRole('heading', { name: /403 — access restricted/i })).toBeInTheDocument()
    expect(screen.getByText(/your current account role does not have authorization/i)).toBeInTheDocument()
  })

  it('allows authenticated government officer to view /government', () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'officer-202', role: 'GOVERNMENT_OFFICER', name: 'Officer Bob' })
    )

    render(
      <MemoryRouter initialEntries={['/government']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )

    expect(screen.getByRole('heading', { name: /government officer portal/i })).toBeInTheDocument()
  })

  it('renders NotFoundPage when navigating to nonexistent route', () => {
    render(
      <MemoryRouter initialEntries={['/some-nonexistent-path-12345']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )

    expect(screen.getByRole('heading', { name: /404 — page not found/i })).toBeInTheDocument()
  })
})
