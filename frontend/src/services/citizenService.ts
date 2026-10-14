/**
 * Citizen Service for communicating with backend Citizen Platform endpoints (/api/v1/citizen/...).
 *
 * Implements:
 * - Grievance intake & metadata
 * - My Grievances list & details
 * - Visual evidence attachment
 * - Municipal road operations & detours
 * - Citizen Chatbot & Grounded RAG Assistant
 */

import { apiClient } from './apiClient'
import type {
  CitizenGrievanceCreatePayload,
  CitizenGrievanceItem,
  CitizenGrievanceDetail,
  EvidenceCreatePayload,
  EvidenceItem,
  CitizenRoadOperation,
  ChatConversationSummary,
  ChatConversation,
  ChatResponse,
} from '../types/citizen'
import type { GrievanceStatus, RoadOperationStatus, RoadOperationType } from '../types/government'

export interface ListGrievancesParams {
  status?: GrievanceStatus
  issue_category?: string
  skip?: number
  limit?: number
}

export interface ListRoadOperationsParams {
  status?: RoadOperationStatus
  road_id?: string
  operation_type?: RoadOperationType
  active_only?: boolean
  skip?: number
  limit?: number
}

class CitizenService {
  /**
   * Submit a new road defect grievance report.
   * Path: POST /api/v1/citizen/grievances
   */
  public async createGrievance(payload: CitizenGrievanceCreatePayload): Promise<CitizenGrievanceItem> {
    return await apiClient.post<CitizenGrievanceItem>('/api/v1/citizen/grievances', payload)
  }

  /**
   * Retrieve grievances submitted by the current citizen.
   * Path: GET /api/v1/citizen/grievances
   */
  public async listGrievances(params?: ListGrievancesParams): Promise<CitizenGrievanceItem[]> {
    const searchParams = new URLSearchParams()
    if (params?.status) searchParams.append('status', params.status)
    if (params?.issue_category) searchParams.append('issue_category', params.issue_category)
    if (params?.skip !== undefined) searchParams.append('skip', String(params.skip))
    if (params?.limit !== undefined) searchParams.append('limit', String(params.limit))

    const queryString = searchParams.toString()
    const path = queryString ? `/api/v1/citizen/grievances?${queryString}` : '/api/v1/citizen/grievances'
    return await apiClient.get<CitizenGrievanceItem[]>(path)
  }

  /**
   * Retrieve detailed citizen-safe grievance information, road info, timeline, and ML summary.
   * Path: GET /api/v1/citizen/grievances/{grievance_id}
   */
  public async getGrievanceDetails(grievanceId: string): Promise<CitizenGrievanceDetail> {
    return await apiClient.get<CitizenGrievanceDetail>(`/api/v1/citizen/grievances/${grievanceId}`)
  }

  /**
   * Attach additional evidence metadata to an owned citizen grievance report.
   * Path: POST /api/v1/citizen/grievances/{grievance_id}/evidence
   */
  public async attachEvidence(grievanceId: string, payload: EvidenceCreatePayload): Promise<EvidenceItem> {
    return await apiClient.post<EvidenceItem>(`/api/v1/citizen/grievances/${grievanceId}/evidence`, payload)
  }

  /**
   * Retrieve public active and planned municipal road operations, restrictions, and detours.
   * Path: GET /api/v1/citizen/road-operations
   */
  public async listRoadOperations(params?: ListRoadOperationsParams): Promise<CitizenRoadOperation[]> {
    const searchParams = new URLSearchParams()
    if (params?.status) searchParams.append('status', params.status)
    if (params?.road_id) searchParams.append('road_id', params.road_id)
    if (params?.operation_type) searchParams.append('operation_type', params.operation_type)
    if (params?.active_only !== undefined) searchParams.append('active_only', String(params.active_only))
    if (params?.skip !== undefined) searchParams.append('skip', String(params.skip))
    if (params?.limit !== undefined) searchParams.append('limit', String(params.limit))

    const queryString = searchParams.toString()
    const path = queryString ? `/api/v1/citizen/road-operations?${queryString}` : '/api/v1/citizen/road-operations'
    return await apiClient.get<CitizenRoadOperation[]>(path)
  }

  /**
   * Retrieve public details for a road operation including schedule and alternative detour route.
   * Path: GET /api/v1/citizen/road-operations/{operation_id}
   */
  public async getRoadOperation(operationId: string): Promise<CitizenRoadOperation> {
    return await apiClient.get<CitizenRoadOperation>(`/api/v1/citizen/road-operations/${operationId}`)
  }

  /**
   * Create a new citizen chat conversation session.
   * Path: POST /api/v1/citizen/chat/conversations
   */
  public async createChatConversation(title?: string): Promise<ChatConversation> {
    return await apiClient.post<ChatConversation>('/api/v1/citizen/chat/conversations', {
      title: title || 'Citizen Assistance Session',
    })
  }

  /**
   * List chat sessions owned by the authenticated citizen.
   * Path: GET /api/v1/citizen/chat/conversations
   */
  public async listChatConversations(params?: { skip?: number; limit?: number }): Promise<ChatConversationSummary[]> {
    const searchParams = new URLSearchParams()
    if (params?.skip !== undefined) searchParams.append('skip', String(params.skip))
    if (params?.limit !== undefined) searchParams.append('limit', String(params.limit))

    const queryString = searchParams.toString()
    const path = queryString ? `/api/v1/citizen/chat/conversations?${queryString}` : '/api/v1/citizen/chat/conversations'
    return await apiClient.get<ChatConversationSummary[]>(path)
  }

  /**
   * Retrieve detailed chat session view and message history.
   * Path: GET /api/v1/citizen/chat/conversations/{conversation_id}
   */
  public async getChatConversation(conversationId: string): Promise<ChatConversation> {
    return await apiClient.get<ChatConversation>(`/api/v1/citizen/chat/conversations/${conversationId}`)
  }

  /**
   * Submit a question/message to the conversational RAG chatbot.
   * Path: POST /api/v1/citizen/chat/conversations/{conversation_id}/messages
   */
  public async sendChatMessage(conversationId: string, content: string): Promise<ChatResponse> {
    return await apiClient.post<ChatResponse>(`/api/v1/citizen/chat/conversations/${conversationId}/messages`, {
      content: content.trim(),
    })
  }
}

export const citizenService = new CitizenService()
