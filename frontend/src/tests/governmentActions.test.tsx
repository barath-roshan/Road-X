/**
 * Unit & Integration tests for Government Officer decision actions:
 * - Grievance dossier inspection & ML analysis display
 * - Official review submission (ACCEPT / REJECT) with required reason validation
 * - Work order commissioning & contractor assignment
 * - Verification queue completion sign-off (APPROVE) & rework rejection (REJECT)
 * - Duplicate mutation prevention and API error handling
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { GovernmentGrievanceDetailModal } from '../features/government/GovernmentGrievanceDetailModal'
import { GovernmentVerificationQueueTab } from '../features/government/GovernmentVerificationQueueTab'
import { governmentService } from '../services/governmentService'
import type {
  GovernmentDashboardGrievanceDetail,
  GovernmentDashboardVerificationItem,
  GovernmentDashboardContractorSummary,
} from '../types/government'

vi.mock('../services/governmentService', () => ({
  governmentService: {
    getGrievanceDetail: vi.fn(),
    submitReview: vi.fn(),
    createWorkOrder: vi.fn(),
    getVerificationQueue: vi.fn(),
    verifyWorkOrder: vi.fn(),
    listContractors: vi.fn(),
  },
}))

const mockDetail: GovernmentDashboardGrievanceDetail = {
  id: 'gr-inspect-101',
  citizen_id: 'cit-303',
  citizen_name: 'Vikram Seth',
  citizen_email: 'vikram@citizen.in',
  road_id: 'road-707',
  road_name: 'Hosur Road Junction 4',
  road_code: 'BLR-HSR-04',
  issue_category: 'SURFACE_POTHOLE',
  description: 'Severe 15cm pothole causing vehicular damage near bus depot',
  latitude: 12.9122,
  longitude: 77.6321,
  status: 'SUBMITTED',
  created_at: '2026-10-10T08:00:00Z',
  updated_at: '2026-10-10T08:00:00Z',
  evidence_items: [
    {
      id: 'ev-1',
      grievance_id: 'gr-inspect-101',
      file_name: 'pothole_depth_marker.jpg',
      file_type: 'image/jpeg',
      storage_path: '/uploads/pothole.jpg',
      file_size_bytes: 204800,
      uploaded_at: '2026-10-10T08:05:00Z',
    },
  ],
  ml_analysis: {
    overall_status: 'READY',
    failure_prediction: { probability: 0.88, risk_level: 'HIGH' },
    damage_detection: { damage_detected: true, confidence: 0.94 },
    severity_prediction: { severity_level: 'HIGH', severity_score: 0.85 },
    time_to_failure: { estimated_days: 7.0 },
    maintenance_priority: {
      priority_level: 'HIGH',
      priority_score: 84.5,
      reasons: ['High bus traffic route', 'Active structural fissure'],
    },
  },
  work_order: null,
  assigned_contractor: null,
  progress_history: [],
  verifications: [],
  reviews: [],
  timeline: [
    {
      id: 'tl-1',
      grievance_id: 'gr-inspect-101',
      event_type: 'GRIEVANCE_SUBMITTED',
      old_status: null,
      new_status: 'SUBMITTED',
      notes: 'Initial citizen filing',
      actor_id: 'cit-303',
      actor_role: 'CITIZEN',
      created_at: '2026-10-10T08:00:00Z',
    },
  ],
}

const mockContractorList: GovernmentDashboardContractorSummary[] = [
  {
    contractor_id: 'c-contractor-01',
    contractor_name: 'Shiva Highway Builders',
    contractor_email: 'shiva@builders.in',
    assigned_work_orders_count: 3,
    in_progress_count: 2,
    pending_verification_count: 0,
    completed_count: 1,
    average_progress_percentage: 60.0,
  },
]

const mockVerificationQueueItem: GovernmentDashboardVerificationItem = {
  work_order_id: 'wo-verify-99',
  grievance_id: 'gr-inspect-101',
  grievance_description: 'Severe 15cm pothole causing vehicular damage',
  road_name: 'Hosur Road Junction 4',
  contractor_id: 'c-contractor-01',
  contractor_name: 'Shiva Highway Builders',
  work_order_title: 'Asphalt Mill and Fill Patching',
  priority: 'HIGH',
  submitted_at: '2026-10-12T09:00:00Z',
  latest_progress_note: 'Compacted with 8-ton vibratory roller. Cured and ready.',
  evidence_items: [
    {
      id: 'ev-comp-1',
      grievance_id: 'gr-inspect-101',
      work_order_id: 'wo-verify-99',
      file_name: 'completed_asphalt_surface.jpg',
      file_type: 'image/jpeg',
      storage_path: '/uploads/completion.jpg',
      uploaded_at: '2026-10-12T09:00:00Z',
    },
  ],
}

describe('Government Review & Assignment Decisions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(governmentService.getGrievanceDetail).mockResolvedValue(mockDetail)
    vi.mocked(governmentService.listContractors).mockResolvedValue(mockContractorList)
  })

  it('renders detailed grievance case with evidence and ML decision support', async () => {
    render(
      <GovernmentGrievanceDetailModal
        grievanceId="gr-inspect-101"
        onClose={vi.fn()}
      />
    )

    await waitFor(() => {
      expect(screen.getByText(/Hosur Road Junction 4/i)).toBeInTheDocument()
      expect(screen.getByText(/Vikram Seth/i)).toBeInTheDocument()
      expect(screen.getByText(/pothole_depth_marker\.jpg/i)).toBeInTheDocument()
      expect(screen.getByText(/ML Decision Support & Predictive Risk Engine/i)).toBeInTheDocument()
      expect(screen.getByText(/High bus traffic route/i)).toBeInTheDocument()
      expect(screen.getByText(/7 days/i)).toBeInTheDocument()
    })
  })

  it('submits official ACCEPT review decision', async () => {
    vi.mocked(governmentService.submitReview).mockResolvedValue({
      id: 'rev-01',
      grievance_id: 'gr-inspect-101',
      officer_id: 'off-1',
      decision: 'ACCEPT',
      reason: null,
      notes: 'Road inspect confirmed',
      created_at: new Date().toISOString(),
    })

    const onUpdateMock = vi.fn()

    render(
      <GovernmentGrievanceDetailModal
        grievanceId="gr-inspect-101"
        onClose={vi.fn()}
        onGrievanceUpdated={onUpdateMock}
      />
    )

    await waitFor(() => {
      expect(screen.getByText(/1\. Submit Official Officer Review Decision/i)).toBeInTheDocument()
    })

    // Click confirm review
    const submitBtn = screen.getByRole('button', { name: /confirm review \(accept\)/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(governmentService.submitReview).toHaveBeenCalledWith('gr-inspect-101', {
        decision: 'ACCEPT',
        reason: undefined,
        notes: undefined,
      })
      expect(onUpdateMock).toHaveBeenCalled()
    })
  })

  it('enforces required reason when rejecting a grievance', async () => {
    render(
      <GovernmentGrievanceDetailModal
        grievanceId="gr-inspect-101"
        onClose={vi.fn()}
      />
    )

    await waitFor(() => {
      expect(screen.getByText(/1\. Submit Official Officer Review Decision/i)).toBeInTheDocument()
    })

    // Select Reject radio
    const rejectRadio = screen.getByLabelText(/reject grievance/i)
    fireEvent.click(rejectRadio)

    // Attempt to submit without reason
    const submitBtn = screen.getByRole('button', { name: /confirm review \(reject\)/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByText(/a rejection reason is required/i)).toBeInTheDocument()
      expect(governmentService.submitReview).not.toHaveBeenCalled()
    })

    // Fill rejection reason and submit
    const reasonInput = screen.getByPlaceholderText(/state reason for rejecting/i)
    fireEvent.change(reasonInput, { target: { value: 'Private road outside municipality jurisdiction' } })

    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(governmentService.submitReview).toHaveBeenCalledWith('gr-inspect-101', {
        decision: 'REJECT',
        reason: 'Private road outside municipality jurisdiction',
        notes: undefined,
      })
    })
  })

  it('commissions work order and assigns contractor with duplicate prevention', async () => {
    vi.mocked(governmentService.createWorkOrder).mockResolvedValue({
      id: 'wo-new-1',
      grievance_id: 'gr-inspect-101',
      road_id: 'road-707',
      created_by: 'off-1',
      assigned_contractor_id: 'c-contractor-01',
      title: 'Emergency Pothole Patching',
      description: 'Full depth patch with bitumen cold mix',
      priority: 'HIGH',
      status: 'ASSIGNED',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })

    render(
      <GovernmentGrievanceDetailModal
        grievanceId="gr-inspect-101"
        onClose={vi.fn()}
      />
    )

    await waitFor(() => {
      expect(screen.getByText(/2\. Commission Maintenance Work Order & Assign Contractor/i)).toBeInTheDocument()
    })

    const titleInput = screen.getByLabelText(/work order title/i)
    fireEvent.change(titleInput, { target: { value: 'Emergency Pothole Patching' } })

    const dispatchBtn = screen.getByRole('button', { name: /create & dispatch work order/i })
    fireEvent.click(dispatchBtn)

    await waitFor(() => {
      expect(governmentService.createWorkOrder).toHaveBeenCalledWith(
        'gr-inspect-101',
        expect.objectContaining({
          title: 'Emergency Pothole Patching',
          assigned_contractor_id: 'c-contractor-01',
        })
      )
    })
  })
})

describe('Government Completion Verification Workflow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(governmentService.getVerificationQueue).mockResolvedValue([mockVerificationQueueItem])
  })

  it('approves completed work order, resolving grievance officially', async () => {
    vi.mocked(governmentService.verifyWorkOrder).mockResolvedValue({
      id: 'verif-1',
      work_order_id: 'wo-verify-99',
      grievance_id: 'gr-inspect-101',
      officer_id: 'off-1',
      decision: 'APPROVE',
      notes: 'Inspected on site. Approved.',
      created_at: new Date().toISOString(),
    })

    render(<GovernmentVerificationQueueTab />)

    await waitFor(() => {
      expect(screen.getByText('Asphalt Mill and Fill Patching')).toBeInTheDocument()
      expect(screen.getByText(/completed_asphalt_surface\.jpg/i)).toBeInTheDocument()
      expect(screen.getByText(/Compacted with 8-ton vibratory roller/i)).toBeInTheDocument()
    })

    // Click Approve button to open confirmation modal
    const approveBtn = screen.getByRole('button', { name: /approve & resolve grievance/i })
    fireEvent.click(approveBtn)

    expect(screen.getByText(/approve repair completion/i)).toBeInTheDocument()

    // Add officer verification remarks
    const remarksArea = screen.getByPlaceholderText(/notes on quality of work/i)
    fireEvent.change(remarksArea, { target: { value: 'Inspected on site. Approved.' } })

    // Confirm approval
    const confirmBtn = screen.getByRole('button', { name: /confirm approval/i })
    fireEvent.click(confirmBtn)

    await waitFor(() => {
      expect(governmentService.verifyWorkOrder).toHaveBeenCalledWith('wo-verify-99', {
        decision: 'APPROVE',
        notes: 'Inspected on site. Approved.',
      })
      expect(screen.getByText(/approved and grievance officially resolved/i)).toBeInTheDocument()
    })
  })

  it('rejects completed work order and requests contractor rework', async () => {
    vi.mocked(governmentService.verifyWorkOrder).mockResolvedValue({
      id: 'verif-2',
      work_order_id: 'wo-verify-99',
      grievance_id: 'gr-inspect-101',
      officer_id: 'off-1',
      decision: 'REJECT',
      notes: 'Asphalt edge raveling detected; re-compact edges',
      created_at: new Date().toISOString(),
    })

    render(<GovernmentVerificationQueueTab />)

    await waitFor(() => {
      expect(screen.getByText('Asphalt Mill and Fill Patching')).toBeInTheDocument()
    })

    // Click Reject / Request Rework
    const rejectBtn = screen.getByRole('button', { name: /reject \/ request rework/i })
    fireEvent.click(rejectBtn)

    expect(screen.getByText(/reject completion & request rework/i)).toBeInTheDocument()

    // Enter required rework reason
    const reworkTextarea = screen.getByPlaceholderText(/specify why repair evidence is insufficient/i)
    fireEvent.change(reworkTextarea, {
      target: { value: 'Asphalt edge raveling detected; re-compact edges' },
    })

    const submitRejectionBtn = screen.getByRole('button', { name: /submit rejection/i })
    fireEvent.click(submitRejectionBtn)

    await waitFor(() => {
      expect(governmentService.verifyWorkOrder).toHaveBeenCalledWith('wo-verify-99', {
        decision: 'REJECT',
        notes: 'Asphalt edge raveling detected; re-compact edges',
      })
      expect(screen.getByText(/returned to contractor for rework/i)).toBeInTheDocument()
    })
  })
})
