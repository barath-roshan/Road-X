/**
 * API response and error types matching FastAPI backend schemas.
 */

export interface APIErrorDetails {
  code: string
  message: string
  request_id?: string | null
}

export interface APIErrorResponse {
  error: APIErrorDetails
}

export interface HealthResponse {
  status: string
  service: string
  version: string
}

export interface ReadinessResponse {
  status: string
  pipeline_loaded: boolean
  details: {
    service_version: string
    database: string
    error?: string
  }
}
