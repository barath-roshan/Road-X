/**
 * Citizen Platform TypeScript types matching backend schemas.
 * References:
 * - backend/schemas/citizen.py
 * - backend/schemas/evidence.py
 * - backend/schemas/chat.py
 * - backend/schemas/road_operation.py
 * - backend/schemas/grievance.py
 */

import type { GrievanceStatus, RoadOperationStatus, RoadOperationType } from './government'

export type DefectCategory = 'POTHOLE' | 'WATERLOGGING' | 'STREETLIGHT' | 'ROAD_CRACK' | string

export interface EvidenceCreatePayload {
  grievance_id: string
  work_order_id?: string | null
  file_name: string
  file_type: string
  storage_path: string
  file_size_bytes?: number | null
}

export interface EvidenceItem {
  id: string
  grievance_id: string
  work_order_id?: string | null
  file_name: string
  file_type: string
  storage_path: string
  file_size_bytes?: number | null
  uploaded_at: string
}

export interface CitizenGrievanceCreatePayload {
  issue_category: DefectCategory
  description: string
  latitude: number
  longitude: number
  road_id?: string | null
  road_segment_id?: string | null
  evidence_items?: EvidenceCreatePayload[] | null
}

export interface CitizenGrievanceItem {
  id: string
  citizen_id: string
  road_id?: string | null
  issue_category: string
  description: string
  latitude: number
  longitude: number
  status: GrievanceStatus
  created_at: string
  updated_at: string
}

export interface CitizenMLSummary {
  detected_issue?: string | null
  severity_level?: string | null
  risk_level?: string | null
  priority_level?: string | null
}

export interface CitizenWorkProgress {
  work_order_id?: string | null
  status?: string | null
  progress_percentage?: number | null
  last_updated_at?: string | null
  status_display?: string | null
}

export interface CitizenRejectionInfo {
  is_reverted_for_rework: boolean
  public_message?: string | null
}

export interface CitizenTimelineItem {
  event_type: string
  status?: string | null
  timestamp: string
  public_message: string
}

export interface CitizenGrievanceDetail {
  id: string
  citizen_id: string
  road_id?: string | null
  road_name?: string | null
  issue_category: string
  description: string
  latitude: number
  longitude: number
  status: GrievanceStatus
  created_at: string
  updated_at: string
  evidence_items: EvidenceItem[]
  ml_summary?: CitizenMLSummary | null
  work_progress?: CitizenWorkProgress | null
  rejection_info?: CitizenRejectionInfo | null
  timeline: CitizenTimelineItem[]
}

export interface CitizenRoadOperation {
  id: string
  road_id?: string | null
  road_name?: string | null
  title: string
  description: string
  reason: string
  operation_type: RoadOperationType
  status: RoadOperationStatus
  start_time: string
  expected_end_time: string
  actual_end_time?: string | null
  alternative_route_name?: string | null
  alternative_route_instructions?: string | null
  alternative_road_name?: string | null
  alternative_distance_km?: number | null
  created_at: string
  updated_at: string
}

export interface ChatSource {
  title: string
  category: string
  source: string
  document_id?: string | null
  chunk_id?: string | null
  relevance_score?: number | null
}

export interface ChatMessage {
  id: string
  conversation_id: string
  role: 'USER' | 'ASSISTANT' | 'SYSTEM'
  content: string
  sources?: ChatSource[] | null
  created_at: string
}

export interface ChatConversationSummary {
  id: string
  citizen_id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export interface ChatConversation {
  id: string
  citizen_id: string
  title: string
  created_at: string
  updated_at: string
  messages: ChatMessage[]
}

export interface ChatResponse {
  conversation_id: string
  user_message: ChatMessage
  assistant_message: ChatMessage
  sources: ChatSource[]
}
