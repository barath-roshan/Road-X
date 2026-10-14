/**
 * Contractor API Service communicating with RoadX Contractor Dashboard endpoints (/api/v1/contractor/...).
 *
 * Implements:
 * - Overview KPI metrics
 * - Assigned work orders list & detail
 * - Work order assignment acknowledgement & starting work
 * - Progress logging & history inspection
 * - Evidence metadata attachment
 * - Completion submission for government verification
 * - Rework queue inspection
 * - Pending verification queue inspection
 * - Workload capacity summary
 */

import { apiClient } from './apiClient'
import type {
  ContractorDashboardOverview,
  ContractorWorkOrderItem,
  ContractorWorkOrderDetail,
  ContractorPendingVerificationItem,
  ContractorReworkItem,
  ContractorWorkloadSummary,
  WorkProgressItem,
  WorkProgressCreatePayload,
  ContractorEvidenceCreatePayload,
  CompletionSubmissionCreatePayload,
  CompletionSubmissionResponse,
} from '../types/contractor'
import type { EvidenceItem, WorkOrderStatus } from '../types/government'

export interface ListContractorWorkOrdersParams {
  status?: WorkOrderStatus
  priority?: string
  date_from?: string
  date_to?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  skip?: number
  limit?: number
}

class ContractorService {
  /**
   * Retrieve aggregate overview statistics for the authenticated contractor.
   * Path: GET /api/v1/contractor/dashboard/overview
   */
  public async getOverview(): Promise<ContractorDashboardOverview> {
    return await apiClient.get<ContractorDashboardOverview>('/api/v1/contractor/dashboard/overview')
  }

  /**
   * Retrieve assigned work orders with optional filtering, sorting, and pagination.
   * Path: GET /api/v1/contractor/dashboard/work-orders
   */
  public async listWorkOrders(params?: ListContractorWorkOrdersParams): Promise<ContractorWorkOrderItem[]> {
    const searchParams = new URLSearchParams()
    if (params?.status) searchParams.append('status', params.status)
    if (params?.priority) searchParams.append('priority', params.priority)
    if (params?.date_from) searchParams.append('date_from', params.date_from)
    if (params?.date_to) searchParams.append('date_to', params.date_to)
    if (params?.sort_by) searchParams.append('sort_by', params.sort_by)
    if (params?.sort_order) searchParams.append('sort_order', params.sort_order)
    if (params?.skip !== undefined) searchParams.append('skip', String(params.skip))
    if (params?.limit !== undefined) searchParams.append('limit', String(params.limit))

    const queryString = searchParams.toString()
    const path = queryString ? `/api/v1/contractor/dashboard/work-orders?${queryString}` : '/api/v1/contractor/dashboard/work-orders'
    return await apiClient.get<ContractorWorkOrderItem[]>(path)
  }

  /**
   * Retrieve contractor-safe detailed view of an assigned work order.
   * Path: GET /api/v1/contractor/dashboard/work-orders/{work_order_id}
   */
  public async getWorkOrderDetail(workOrderId: string): Promise<ContractorWorkOrderDetail> {
    return await apiClient.get<ContractorWorkOrderDetail>(`/api/v1/contractor/dashboard/work-orders/${workOrderId}`)
  }

  /**
   * Contractor acknowledges assignment of a work order.
   * Path: POST /api/v1/contractor/work-orders/{work_order_id}/accept
   */
  public async acknowledgeWorkOrder(workOrderId: string, notes?: string): Promise<{ id: string; status: string }> {
    const queryString = notes ? `?notes=${encodeURIComponent(notes)}` : ''
    return await apiClient.post<{ id: string; status: string }>(`/api/v1/contractor/work-orders/${workOrderId}/accept${queryString}`)
  }

  /**
   * Contractor starts work on an assigned work order (ASSIGNED -> IN_PROGRESS).
   * Path: POST /api/v1/contractor/work-orders/{work_order_id}/start
   */
  public async startWorkOrder(workOrderId: string, notes?: string): Promise<{ id: string; status: string }> {
    const queryString = notes ? `?notes=${encodeURIComponent(notes)}` : ''
    return await apiClient.post<{ id: string; status: string }>(`/api/v1/contractor/work-orders/${workOrderId}/start${queryString}`)
  }

  /**
   * Log progress percentage update (0-100%) and optional notes.
   * Path: POST /api/v1/contractor/work-orders/{work_order_id}/progress
   */
  public async updateProgress(workOrderId: string, payload: WorkProgressCreatePayload): Promise<WorkProgressItem> {
    return await apiClient.post<WorkProgressItem>(`/api/v1/contractor/work-orders/${workOrderId}/progress`, payload)
  }

  /**
   * Attach repair photo or proof document metadata to a work order.
   * Path: POST /api/v1/contractor/work-orders/{work_order_id}/evidence
   */
  public async attachEvidence(workOrderId: string, payload: ContractorEvidenceCreatePayload): Promise<EvidenceItem> {
    return await apiClient.post<EvidenceItem>(`/api/v1/contractor/work-orders/${workOrderId}/evidence`, payload)
  }

  /**
   * Submit completed work order for government officer verification.
   * Transitions WorkOrder and Grievance to PENDING_VERIFICATION.
   * Path: POST /api/v1/contractor/work-orders/{work_order_id}/submit
   */
  public async submitCompletion(
    workOrderId: string,
    payload: CompletionSubmissionCreatePayload
  ): Promise<CompletionSubmissionResponse> {
    return await apiClient.post<CompletionSubmissionResponse>(`/api/v1/contractor/work-orders/${workOrderId}/submit`, payload)
  }

  /**
   * Retrieve work orders awaiting government completion verification.
   * Path: GET /api/v1/contractor/dashboard/pending-verification
   */
  public async getPendingVerificationQueue(skip: number = 0, limit: number = 100): Promise<ContractorPendingVerificationItem[]> {
    return await apiClient.get<ContractorPendingVerificationItem[]>(
      `/api/v1/contractor/dashboard/pending-verification?skip=${skip}&limit=${limit}`
    )
  }

  /**
   * Retrieve work orders rejected by government officer requiring contractor rework.
   * Path: GET /api/v1/contractor/dashboard/rework
   */
  public async getReworkQueue(skip: number = 0, limit: number = 100): Promise<ContractorReworkItem[]> {
    return await apiClient.get<ContractorReworkItem[]>(`/api/v1/contractor/dashboard/rework?skip=${skip}&limit=${limit}`)
  }

  /**
   * Retrieve contractor's personal workload summary metrics.
   * Path: GET /api/v1/contractor/dashboard/workload
   */
  public async getWorkloadSummary(): Promise<ContractorWorkloadSummary> {
    return await apiClient.get<ContractorWorkloadSummary>('/api/v1/contractor/dashboard/workload')
  }
}

export const contractorService = new ContractorService()
