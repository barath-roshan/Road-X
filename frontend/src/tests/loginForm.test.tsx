import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../features/auth/AuthContext'
import { LoginForm } from '../features/auth/LoginForm'

describe('LoginForm Component', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.restoreAllMocks()
  })

  it('renders role selectors, accessible form inputs, and submit button', () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginForm />
        </AuthProvider>
      </MemoryRouter>
    )

    expect(screen.getByRole('heading', { name: /sign in to roadx/i })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /citizen/i })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /officer/i })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /contractor/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/actor user id/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in as/i })).toBeInTheDocument()
  })

  it('validates that user ID is required when cleared', async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginForm />
        </AuthProvider>
      </MemoryRouter>
    )

    const userIdInput = screen.getByLabelText(/actor user id/i)
    fireEvent.change(userIdInput, { target: { value: '' } })

    const submitBtn = screen.getByRole('button', { name: /sign in as/i })
    fireEvent.click(submitBtn)

    expect(
      await screen.findByText(/user id is required to identify your actor in roadx/i)
    ).toBeInTheDocument()
  })

  it('switches role preset properly when clicking role button', () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginForm />
        </AuthProvider>
      </MemoryRouter>
    )

    const officerRadio = screen.getByRole('radio', { name: /officer/i })
    fireEvent.click(officerRadio)

    expect(officerRadio).toHaveAttribute('aria-checked', 'true')
    expect(screen.getByLabelText(/actor user id/i)).toHaveValue('officer-smoke-1')
    expect(screen.getByRole('button', { name: /sign in as government officer/i })).toBeInTheDocument()
  })

  it('displays API error alert when backend request fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new TypeError('Failed to fetch'))

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginForm />
        </AuthProvider>
      </MemoryRouter>
    )

    const submitBtn = screen.getByRole('button', { name: /sign in as/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByText(/unable to reach roadx service/i)).toBeInTheDocument()
    })
  })
})
