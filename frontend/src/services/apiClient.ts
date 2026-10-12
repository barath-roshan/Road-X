/**
 * Centralized API client for communicating with the RoadX FastAPI backend.
 *
 * Injects required header-based authentication credentials (X-Actor-User-ID, X-Actor-Role),
 * standardizes APIErrorResponse handling, supports request cancellation, and handles multipart uploads.
 */

import type { APIErrorResponse } from '../types/api'
import type { UserRole } from '../types/auth'

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000'

export class APIClientError extends Error {
  public code: string
  public status: number
  public requestId?: string | null

  constructor(message: string, code: string = 'API_ERROR', status: number = 500, requestId?: string | null) {
    super(message)
    this.name = 'APIClientError'
    this.code = code
    this.status = status
    this.requestId = requestId
  }
}

export interface RequestOptions {
  headers?: Record<string, string>
  signal?: AbortSignal
  userId?: string | null
  role?: UserRole | null
}

class APIClient {
  private baseUrl: string

  constructor() {
    this.baseUrl = import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
    // Strip trailing slash if present
    if (this.baseUrl.endsWith('/')) {
      this.baseUrl = this.baseUrl.slice(0, -1)
    }
  }

  public getBaseUrl(): string {
    return this.baseUrl
  }

  private buildHeaders(options?: RequestOptions, isFormData = false): Headers {
    const headers = new Headers()

    if (!isFormData) {
      headers.set('Content-Type', 'application/json')
    }
    headers.set('Accept', 'application/json')

    // Attach custom request headers
    if (options?.headers) {
      Object.entries(options.headers).forEach(([key, value]) => {
        headers.set(key, value)
      })
    }

    // Attach RoadX Actor context headers if provided or stored in session
    const activeUserId = options?.userId ?? this.getSessionUserId()
    const activeRole = options?.role ?? this.getSessionUserRole()

    if (activeUserId) {
      headers.set('X-Actor-User-ID', activeUserId)
    }
    if (activeRole) {
      headers.set('X-Actor-Role', activeRole)
    }

    return headers
  }

  private getSessionUserId(): string | null {
    try {
      const stored = sessionStorage.getItem('roadx_user')
      if (stored) {
        const parsed = JSON.parse(stored)
        return parsed?.id ?? null
      }
    } catch {
      // Ignore parse failure
    }
    return null
  }

  private getSessionUserRole(): UserRole | null {
    try {
      const stored = sessionStorage.getItem('roadx_user')
      if (stored) {
        const parsed = JSON.parse(stored)
        return parsed?.role ?? null
      }
    } catch {
      // Ignore parse failure
    }
    return null
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (response.ok) {
      // If 204 No Content
      if (response.status === 204) {
        return {} as T
      }
      return (await response.json()) as T
    }

    // Extract structured FastAPI APIErrorResponse if present
    let errorDetails: { message: string; code: string; requestId?: string | null } = {
      message: `Request failed with status ${response.status}`,
      code: `HTTP_${response.status}`,
      requestId: response.headers.get('X-Request-ID'),
    }

    try {
      const body = await response.json()
      if (body && typeof body === 'object') {
        const parsedBody = body as APIErrorResponse
        if (parsedBody.error) {
          errorDetails.message = parsedBody.error.message || errorDetails.message
          errorDetails.code = parsedBody.error.code || errorDetails.code
          errorDetails.requestId = parsedBody.error.request_id || errorDetails.requestId
        } else if (typeof (body as { detail?: string }).detail === 'string') {
          errorDetails.message = (body as { detail: string }).detail
        }
      }
    } catch {
      // Body not JSON
    }

    throw new APIClientError(
      errorDetails.message,
      errorDetails.code,
      response.status,
      errorDetails.requestId
    )
  }

  public async get<T>(path: string, options?: RequestOptions): Promise<T> {
    const url = `${this.baseUrl}${path.startsWith('/') ? path : `/${path}`}`
    const headers = this.buildHeaders(options)

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers,
        signal: options?.signal,
      })
      return await this.handleResponse<T>(response)
    } catch (err: unknown) {
      if (err instanceof APIClientError) {
        throw err
      }
      if (err instanceof DOMException && err.name === 'AbortError') {
        throw new APIClientError('Request was aborted.', 'ABORT_ERROR', 0)
      }
      throw new APIClientError(
        'Unable to reach RoadX service. Please check your network connection.',
        'NETWORK_ERROR',
        0
      )
    }
  }

  public async post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    const url = `${this.baseUrl}${path.startsWith('/') ? path : `/${path}`}`
    const headers = this.buildHeaders(options)

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: options?.signal,
      })
      return await this.handleResponse<T>(response)
    } catch (err: unknown) {
      if (err instanceof APIClientError) {
        throw err
      }
      if (err instanceof DOMException && err.name === 'AbortError') {
        throw new APIClientError('Request was aborted.', 'ABORT_ERROR', 0)
      }
      throw new APIClientError(
        'Unable to reach RoadX service. Please check your network connection.',
        'NETWORK_ERROR',
        0
      )
    }
  }

  public async upload<T>(path: string, formData: FormData, options?: RequestOptions): Promise<T> {
    const url = `${this.baseUrl}${path.startsWith('/') ? path : `/${path}`}`
    const headers = this.buildHeaders(options, true)

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: formData,
        signal: options?.signal,
      })
      return await this.handleResponse<T>(response)
    } catch (err: unknown) {
      if (err instanceof APIClientError) {
        throw err
      }
      if (err instanceof DOMException && err.name === 'AbortError') {
        throw new APIClientError('Upload was aborted.', 'ABORT_ERROR', 0)
      }
      throw new APIClientError(
        'Failed to upload file. Please verify network connection.',
        'UPLOAD_ERROR',
        0
      )
    }
  }
}

export const apiClient = new APIClient()
