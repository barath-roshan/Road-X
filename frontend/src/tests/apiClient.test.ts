import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { apiClient, APIClientError } from '../services/apiClient'

describe('APIClient Service', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('injects actor identity headers when user is stored in session', async () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'officer-test-99', role: 'GOVERNMENT_OFFICER', name: 'Officer Test' })
    )

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'healthy' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    await apiClient.get('/health')

    expect(fetchSpy).toHaveBeenCalledTimes(1)
    const callArgs = fetchSpy.mock.calls[0]
    const headers = callArgs[1]?.headers as Headers
    expect(headers.get('X-Actor-User-ID')).toBe('officer-test-99')
    expect(headers.get('X-Actor-Role')).toBe('GOVERNMENT_OFFICER')
  })

  it('parses structured APIErrorResponse from FastAPI on 400/403/422 responses', async () => {
    const errorBody = {
      error: {
        code: 'UNAUTHORIZED_ACCESS',
        message: "Role 'CITIZEN' is not authorized. Operation requires 'GOVERNMENT_OFFICER'.",
        request_id: 'req-test-123',
      },
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify(errorBody), {
        status: 403,
        headers: { 'Content-Type': 'application/json', 'X-Request-ID': 'req-test-123' },
      })
    )

    await expect(apiClient.get('/api/v1/government/dashboard/overview')).rejects.toThrow(
      "Role 'CITIZEN' is not authorized. Operation requires 'GOVERNMENT_OFFICER'."
    )
  })

  it('handles network failure gracefully without exposing raw stack traces', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new TypeError('Failed to fetch'))

    try {
      await apiClient.get('/health')
      expect.fail('Should have thrown APIClientError')
    } catch (err: unknown) {
      expect(err).toBeInstanceOf(APIClientError)
      const apiErr = err as APIClientError
      expect(apiErr.code).toBe('NETWORK_ERROR')
      expect(apiErr.message).toContain('Unable to reach RoadX service')
    }
  })

  it('supports multipart file upload without overriding browser Content-Type boundary', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'uploaded' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    const formData = new FormData()
    formData.append('file', new Blob(['test content'], { type: 'text/plain' }), 'test.txt')

    await apiClient.upload('/api/v1/ml/damage/analyze', formData)

    const callArgs = fetchSpy.mock.calls[0]
    const headers = callArgs[1]?.headers as Headers
    // Content-Type should not be application/json for multipart uploads
    expect(headers.get('Content-Type')).toBeNull()
  })
})
