/**
 * Government Officer Workflow & Dashboard API service.
 * Direct integration with RoadX FastAPI backend endpoints at /api/v1/government/...
 */

import { apiClient } from './apiClient'
import type { RequestOptions } from './apiClient'
import type {
  GovernmentDashboardOverview,
  GovernmentDashboardGrievanceItem,
  GovernmentDashboardGrievanceDetail,
  GovernmentDashboardPriorityItem,
  GovernmentDashboardVerificationItem,
  GovernmentDashboardWorkOrderItem,
  GovernmentDashboardContractorSummary,
  GovernmentRoadOperation,
  GovernmentReviewCreatePayload,
  GovernmentReviewItem,
  WorkOrderCreatePayload,
  WorkOrderSummary,
  GovernmentVerificationCreatePayload,
  GovernmentVerificationItem,
  RoadOperationCreatePayload,
  GrievanceStatus,
  WorkOrderStatus,
  RoadOperationStatus,
  RoadOperationType,
} from '../types/government'

export interface GrievanceFilterParams {
  status?: GrievanceStatus | ''
  issue_category?: string
  priority?: string
  severity?: string
  risk_level?: string
  search?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  skip?: number
  limit?: number
}

export interface PriorityQueueParams {
  min_priority?: string
  skip?: number
  limit?: number
}

export interface WorkOrderFilterParams {
  status?: WorkOrderStatus | ''
  priority?: string
  assigned_contractor_id?: string
  skip?: number
  limit?: number
}

export interface RoadOperationFilterParams {
  status?: RoadOperationStatus | ''
  operation_type?: RoadOperationType | ''
  road_id?: string
  skip?: number
  limit?: number
}

function buildQueryString(params: Record<string, string | number | undefined | null>): string {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== '') {
      query.append(key, String(val))
    }
  })
  const qs = query.toString()
  return qs ? `?${qs}` : ''
}

export const governmentService = {
  /**
   * Fetch aggregate dashboard overview statistics
   */
  async getOverview(options?: RequestOptions): Promise<GovernmentDashboardOverview> {
    return apiClient.get<GovernmentDashboardOverview>('/api/v1/government/dashboard/overview', options)
  },

  /**
   * List grievances with dashboard filters and search
   */
  async listGrievances(
    params: GrievanceFilterParams = {},
    options?: RequestOptions
  ): Promise<GovernmentDashboardGrievanceItem[]> {
    const qs = buildQueryString({
      status: params.status,
      issue_category: params.issue_category,
      priority: params.priority,
      severity: params.severity,
      risk_level: params.risk_level,
      search: params.search,
      sort_by: params.sort_by,
      sort_order: params.sort_order,
      skip: params.skip,
      limit: params.limit,
    })
    return apiClient.get<GovernmentDashboardGrievanceItem[]>(
      `/api/v1/government/dashboard/grievances${qs}`,
      options
    )
  },

  /**
   * Fetch complete case details for a specific grievance
   */
  async getGrievanceDetail(
    grievanceId: string,
    options?: RequestOptions
  ): Promise<GovernmentDashboardGrievanceDetail> {
    return apiClient.get<GovernmentDashboardGrievanceDetail>(
      `/api/v1/government/dashboard/grievances/${grievanceId}`,
      options
    )
  },

  /**
   * Submit an official government review decision (ACCEPT / REJECT)
   */
  async submitReview(
    grievanceId: string,
    payload: GovernmentReviewCreatePayload,
    options?: RequestOptions
  ): Promise<GovernmentReviewItem> {
    return apiClient.post<GovernmentReviewItem>(
      `/api/v1/government/grievances/${grievanceId}/review`,
      payload,
      options
    )
  },

  /**
   * Create and assign a maintenance work order for a grievance
   */
  async createWorkOrder(
    grievanceId: string,
    payload: WorkOrderCreatePayload,
    options?: RequestOptions
  ): Promise<WorkOrderSummary> {
    return apiClient.post<WorkOrderSummary>(
      `/api/v1/government/grievances/${grievanceId}/work-orders`,
      payload,
      options
    )
  },

  /**
   * Fetch prioritized maintenance queue ordered by ML priority score
   */
  async getPriorityQueue(
    params: PriorityQueueParams = {},
    options?: RequestOptions
  ): Promise<GovernmentDashboardPriorityItem[]> {
    const qs = buildQueryString({
      min_priority: params.min_priority,
      skip: params.skip,
      limit: params.limit,
    })
    return apiClient.get<GovernmentDashboardPriorityItem[]>(
      `/api/v1/government/dashboard/priority-queue${qs}`,
      options
    )
  },

  /**
   * Fetch work orders awaiting officer completion verification
   */
  async getVerificationQueue(
    params: { skip?: number; limit?: number } = {},
    options?: RequestOptions
  ): Promise<GovernmentDashboardVerificationItem[]> {
    const qs = buildQueryString(params)
    return apiClient.get<GovernmentDashboardVerificationItem[]>(
      `/api/v1/government/dashboard/verification-queue${qs}`,
      options
    )
  },

  /**
   * Verify work order completion (APPROVE or REJECT)
   */
  async verifyWorkOrder(
    workOrderId: string,
    payload: GovernmentVerificationCreatePayload,
    options?: RequestOptions
  ): Promise<GovernmentVerificationItem> {
    return apiClient.post<GovernmentVerificationItem>(
      `/api/v1/government/work-orders/${workOrderId}/verify`,
      payload,
      options
    )
  },

  /**
   * Monitor maintenance work orders across the municipality
   */
  async listWorkOrders(
    params: WorkOrderFilterParams = {},
    options?: RequestOptions
  ): Promise<GovernmentDashboardWorkOrderItem[]> {
    const qs = buildQueryString({
      status: params.status,
      priority: params.priority,
      assigned_contractor_id: params.assigned_contractor_id,
      skip: params.skip,
      limit: params.limit,
    })
    return apiClient.get<GovernmentDashboardWorkOrderItem[]>(
      `/api/v1/government/dashboard/work-orders${qs}`,
      options
    )
  },

  /**
   * Fetch contractor workload and progress statistics
   */
  async listContractors(
    params: { skip?: number; limit?: number } = {},
    options?: RequestOptions
  ): Promise<GovernmentDashboardContractorSummary[]> {
    const qs = buildQueryString(params)
    return apiClient.get<GovernmentDashboardContractorSummary[]>(
      `/api/v1/government/dashboard/contractors${qs}`,
      options
    )
  },

  /**
   * Fetch municipal road operations, closures, and detours
   */
  async listRoadOperations(
    params: RoadOperationFilterParams = {},
    options?: RequestOptions
  ): Promise<GovernmentRoadOperation[]> {
    const qs = buildQueryString({
      status: params.status,
      operation_type: params.operation_type,
      road_id: params.road_id,
      skip: params.skip,
      limit: params.limit,
    })
    return apiClient.get<GovernmentRoadOperation[]>(
      `/api/v1/government/road-operations${qs}`,
      options
    )
  },

  /**
   * Create a new road operation or closure
   */
  async createRoadOperation(
    payload: RoadOperationCreatePayload,
    options?: RequestOptions
  ): Promise<GovernmentRoadOperation> {
    return apiClient.post<GovernmentRoadOperation>(
      '/api/v1/government/road-operations',
      payload,
      options
    )
  },

  /**
   * Activate a planned road operation (PLANNED -> ACTIVE)
   */
  async activateRoadOperation(
    operationId: string,
    notes?: string,
    options?: RequestOptions
  ): Promise<GovernmentRoadOperation> {
    const qs = notes ? `?notes=${encodeURIComponent(notes)}` : ''
    return apiClient.post<GovernmentRoadOperation>(
      `/api/v1/government/road-operations/${operationId}/activate${qs}`,
      undefined,
      options
    )
  },

  /**
   * Complete an active road operation (ACTIVE -> COMPLETED)
   */
  async completeRoadOperation(
    operationId: string,
    notes?: string,
    options?: RequestOptions
  ): Promise<GovernmentRoadOperation> {
    const qs = notes ? `?notes=${encodeURIComponent(notes)}` : ''
    return apiClient.post<GovernmentRoadOperation>(
      `/api/v1/government/road-operations/${operationId}/complete${qs}`,
      undefined,
      options
    )
  },

  /**
   * Cancel a road operation
   */
  async cancelRoadOperation(
    operationId: string,
    notes?: string,
    options?: RequestOptions
  ): Promise<GovernmentRoadOperation> {
    const qs = notes ? `?notes=${encodeURIComponent(notes)}` : ''
    return apiClient.post<GovernmentRoadOperation>(
      `/api/v1/government/road-operations/${operationId}/cancel${qs}`,
      undefined,
      options
    )
  },
}
