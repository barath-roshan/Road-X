/**
 * TypeScript type definitions for Contractor Dashboard and Work-Order Execution.
 * Matches backend schemas in backend/schemas/contractor_dashboard.py,
 * backend/schemas/work_progress.py, backend/schemas/completion_submission.py,
 * and backend/schemas/evidence.py.
 */

import type { WorkOrderStatus, EvidenceItem, WorkflowEventItem } from './government'

export interface ContractorDashboardOverview {
  total_assigned: number
  assigned: number
  in_progress: number
  pending_verification: number
  completed: number
  rework: number
  average_progress: number
}

export interface ContractorWorkOrderItem {
  id: string
  grievance_id: string
  road_id?: string | null
  road_name?: string | null
  title: string
  description: string
  priority: string
  status: WorkOrderStatus
  progress_percentage: number
  rework_required: boolean
  created_at: string
  updated_at: string
}

export interface WorkProgressItem {
  id: string
  work_order_id: string
  contractor_id: string
  progress_percentage: number
  note?: string | null
  created_at: string
}

export interface ContractorWorkOrderDetail {
  id: string
  grievance_id: string
  road_id?: string | null
  title: string
  description: string
  priority: string
  status: WorkOrderStatus
  created_at: string
  updated_at: string

  // Location & Road info
  road_name?: string | null
  road_code?: string | null
  latitude?: number | null
  longitude?: number | null

  // Grievance reference (contractor-safe)
  grievance_description?: string | null
  grievance_issue_category?: string | null
  grievance_severity?: string | null
  grievance_risk_level?: string | null
  grievance_priority?: string | null

  // Progress & Evidence
  current_progress: number
  progress_history: WorkProgressItem[]
  completion_evidence: EvidenceItem[]

  // Government Feedback & Verification
  government_verification_status?: string | null
  rework_required: boolean
  latest_rejection_notes?: string | null
  rejection_timestamp?: string | null

  // Workflow Audit Timeline
  timeline: WorkflowEventItem[]
}

export interface ContractorPendingVerificationItem {
  work_order_id: string
  grievance_id: string
  title: string
  priority: string
  progress_percentage: number
  completion_submitted_at: string
  evidence: EvidenceItem[]
}

export interface ContractorReworkItem {
  work_order_id: string
  grievance_id: string
  title: string
  priority: string
  current_status: WorkOrderStatus
  rejection_message: string
  rejection_timestamp?: string | null
  current_progress: number
}

export interface ContractorWorkloadSummary {
  total_assignments: number
  active_assignments: number
  pending_verification: number
  rework_required: number
  resolved_completed: number
  average_completion_percentage: number
}

export interface WorkProgressCreatePayload {
  progress_percentage: number
  note?: string | null
}

export interface ContractorEvidenceCreatePayload {
  file_name: string
  file_type: string
  storage_path: string
  file_size_bytes?: number | null
  grievance_id: string
  work_order_id?: string | null
}

export interface CompletionSubmissionCreatePayload {
  completion_note: string
  actual_work_summary?: string | null
  evidence_ids?: string[] | null
}

export interface CompletionSubmissionResponse {
  work_order_id: string
  status: string
  grievance_status: string
  submitted_at: string
  completion_note: string
  message: string
}
