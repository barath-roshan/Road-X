/**
 * Government Officer Dashboard TypeScript types matching backend schemas.
 * References:
 * - backend/schemas/government_dashboard.py
 * - backend/schemas/government_review.py
 * - backend/schemas/government_verification.py
 * - backend/schemas/work_order.py
 * - backend/schemas/road_operation.py
 * - backend/schemas/evidence.py
 * - backend/schemas/workflow_event.py
 */

export type GrievanceStatus =
  | 'SUBMITTED'
  | 'UNDER_REVIEW'
  | 'IN_PROGRESS'
  | 'PENDING_VERIFICATION'
  | 'RESOLVED'
  | 'REJECTED'

export type WorkOrderStatus =
  | 'OPEN'
  | 'ASSIGNED'
  | 'IN_PROGRESS'
  | 'PENDING_VERIFICATION'
  | 'COMPLETED'
  | 'CANCELLED'

export type RoadOperationStatus = 'PLANNED' | 'ACTIVE' | 'COMPLETED' | 'CANCELLED'

export type RoadOperationType =
  | 'ROAD_CLOSURE'
  | 'LANE_RESTRICTION'
  | 'MAINTENANCE_WORK'
  | 'DETOUR'
  | 'HAZARD_BLOCK'

export type ReviewDecision = 'ACCEPT' | 'REJECT'

export type VerificationDecision = 'APPROVE' | 'REJECT'

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

export interface WorkflowEventItem {
  id: string
  grievance_id: string
  work_order_id?: string | null
  actor_id?: string | null
  actor_role?: string | null
  event_type: string
  old_status?: string | null
  new_status?: string | null
  notes?: string | null
  created_at: string
}

export interface WorkProgressItem {
  id: string
  work_order_id: string
  progress_percentage: number
  notes?: string | null
  submitted_by?: string | null
  created_at: string
}

export interface GovernmentReviewItem {
  id: string
  grievance_id: string
  officer_id?: string | null
  decision: ReviewDecision
  reason?: string | null
  notes?: string | null
  created_at: string
}

export interface GovernmentVerificationItem {
  id: string
  work_order_id: string
  grievance_id: string
  officer_id?: string | null
  decision: VerificationDecision
  notes?: string | null
  created_at: string
}

export interface MLAnalysisDict {
  id?: string
  pipeline_version?: string
  overall_status?: string
  failure_prediction?: {
    probability?: number
    prediction?: number
    risk_level?: string
    confidence?: number
    [key: string]: unknown
  }
  damage_detection?: {
    damage_detected?: boolean
    damage_type?: string
    confidence?: number
    detections?: Array<{ label: string; confidence: number; box?: number[] }>
    [key: string]: unknown
  }
  severity_prediction?: {
    severity_level?: string
    severity_score?: number
    [key: string]: unknown
  }
  complaint_analysis?: {
    category?: string
    urgency?: string
    summary?: string
    [key: string]: unknown
  }
  duplicate_detection?: {
    is_duplicate?: boolean
    similarity_score?: number
    [key: string]: unknown
  }
  time_to_failure?: {
    estimated_days?: number
    time_to_failure_days?: number
    [key: string]: unknown
  }
  maintenance_priority?: {
    priority_level?: string
    priority_score?: number
    reasons?: string[]
    [key: string]: unknown
  }
  created_at?: string
  [key: string]: unknown
}

export interface GovernmentDashboardOverview {
  total_grievances: number
  status_counts: Record<string, number>
  priority_counts: Record<string, number>
  severity_counts: Record<string, number>
  work_order_counts: Record<string, number>
  active_contractors_count: number
  pending_verifications_count: number
}

export interface GovernmentDashboardGrievanceItem {
  id: string
  citizen_id: string
  citizen_name?: string | null
  road_id?: string | null
  road_name?: string | null
  issue_category: string
  description: string
  latitude: number
  longitude: number
  status: GrievanceStatus
  created_at: string
  updated_at: string
  priority?: string | null
  severity?: string | null
  risk_level?: string | null
  work_order_status?: string | null
  assigned_contractor_name?: string | null
}

export interface WorkOrderSummary {
  id: string
  grievance_id: string
  road_id?: string | null
  created_by?: string | null
  assigned_contractor_id?: string | null
  title: string
  description: string
  priority: string
  status: WorkOrderStatus
  created_at: string
  updated_at: string
}

export interface ContractorUserSummary {
  id: string
  name: string
  email: string
  role: string
  phone?: string | null
}

export interface GovernmentDashboardGrievanceDetail {
  id: string
  citizen_id: string
  citizen_name?: string | null
  citizen_email?: string | null
  road_id?: string | null
  road_name?: string | null
  road_code?: string | null
  issue_category: string
  description: string
  latitude: number
  longitude: number
  status: GrievanceStatus
  created_at: string
  updated_at: string
  evidence_items: EvidenceItem[]
  ml_analysis?: MLAnalysisDict | null
  work_order?: WorkOrderSummary | null
  assigned_contractor?: ContractorUserSummary | null
  progress_history: WorkProgressItem[]
  verifications: GovernmentVerificationItem[]
  reviews: GovernmentReviewItem[]
  timeline: WorkflowEventItem[]
}

export interface GovernmentDashboardPriorityItem {
  grievance_id: string
  road_name?: string | null
  issue_category: string
  description: string
  status: GrievanceStatus
  priority_score?: number | null
  priority_level: string
  severity_level?: string | null
  risk_level?: string | null
  estimated_time_to_failure_days?: number | null
  reasons: string[]
  created_at: string
}

export interface GovernmentDashboardVerificationItem {
  work_order_id: string
  grievance_id: string
  grievance_description: string
  road_name?: string | null
  contractor_id: string
  contractor_name?: string | null
  work_order_title: string
  priority: string
  submitted_at: string
  latest_progress_note?: string | null
  evidence_items: EvidenceItem[]
}

export interface GovernmentDashboardWorkOrderItem {
  id: string
  grievance_id: string
  road_name?: string | null
  assigned_contractor_id?: string | null
  contractor_name?: string | null
  title: string
  description: string
  priority: string
  status: WorkOrderStatus
  current_progress_percentage: number
  created_at: string
  updated_at: string
}

export interface GovernmentDashboardContractorSummary {
  contractor_id: string
  contractor_name: string
  contractor_email: string
  assigned_work_orders_count: number
  in_progress_count: number
  pending_verification_count: number
  completed_count: number
  average_progress_percentage: number
}

export interface GovernmentRoadOperation {
  id: string
  road_id?: string | null
  road_name?: string | null
  grievance_id?: string | null
  work_order_id?: string | null
  created_by?: string | null
  creator_name?: string | null
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
  alternative_road_id?: string | null
  alternative_distance_km?: number | null
  created_at: string
  updated_at: string
}

// Request schemas
export interface GovernmentReviewCreatePayload {
  decision: ReviewDecision
  reason?: string | null
  notes?: string | null
}

export interface WorkOrderCreatePayload {
  title: string
  description: string
  priority?: string
  assigned_contractor_id?: string | null
}

export interface GovernmentVerificationCreatePayload {
  decision: VerificationDecision
  notes?: string | null
}

export interface RoadOperationCreatePayload {
  title: string
  description: string
  reason: string
  operation_type: RoadOperationType
  road_id?: string | null
  grievance_id?: string | null
  work_order_id?: string | null
  start_time: string
  expected_end_time: string
  status?: RoadOperationStatus
  alternative_route_name?: string | null
  alternative_route_instructions?: string | null
  alternative_road_id?: string | null
  alternative_distance_km?: number | null
}
