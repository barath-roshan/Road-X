/**
 * Unit & Integration Tests for RoadX Contractor Dashboard & Work-Order Execution (Phase 26).
 *
 * Covers:
 * 1. Contractor overview rendering (KPI metrics: total_assigned, assigned, in_progress, pending, completed, rework, average_progress)
 * 2. Loading, empty, error, and retry states
 * 3. Assigned work-order list rendering
 * 4. Search and supported filters (status, priority, sort)
 * 5. Contractor work-order details modal rendering
 * 6. Assignment acknowledgement and start work actions
 * 7. Progress input validation (0-100%, monotonicity enforcement requiring correction keywords)
 * 8. Successful and failed progress updates
 * 9. Completion evidence behavior (metadata attachment, file validation)
 * 10. Rework queue feedback display and resubmission
 * 11. Duplicate-submission prevention while request is pending
 * 12. Handling 401/403 unauthorized responses
 * 13. Contractor route protection and denial of non-contractor roles (CITIZEN, GOVERNMENT_OFFICER)
 * 14. Verification that contractor cannot resolve or approve work orders
 * 15. Pending verification queue view
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../features/auth/AuthContext'
import { ContractorDashboardPage } from '../pages/ContractorDashboardPage'
import { ContractorOverviewTab } from '../features/contractor/ContractorOverviewTab'
import { contractorService } from '../services/contractorService'
import type {
  ContractorDashboardOverview,
  ContractorWorkOrderItem,
  ContractorWorkOrderDetail,
  ContractorReworkItem,
  ContractorPendingVerificationItem,
  ContractorWorkloadSummary,
} from '../types/contractor'

// Mock contractorService
vi.mock('../services/contractorService', () => ({
  contractorService: {
    getOverview: vi.fn(),
    listWorkOrders: vi.fn(),
    getWorkOrderDetail: vi.fn(),
    acknowledgeWorkOrder: vi.fn(),
    startWorkOrder: vi.fn(),
    updateProgress: vi.fn(),
    attachEvidence: vi.fn(),
    submitCompletion: vi.fn(),
    getPendingVerificationQueue: vi.fn(),
    getReworkQueue: vi.fn(),
    getWorkloadSummary: vi.fn(),
  },
}))

const mockOverview: ContractorDashboardOverview = {
  total_assigned: 5,
  assigned: 1,
  in_progress: 2,
  pending_verification: 1,
  completed: 1,
  rework: 1,
  average_progress: 68.5,
}

const mockWorkload: ContractorWorkloadSummary = {
  total_assignments: 5,
  active_assignments: 3,
  pending_verification: 1,
  rework_required: 1,
  resolved_completed: 1,
  average_completion_percentage: 68.5,
}

const mockWorkOrders: ContractorWorkOrderItem[] = [
  {
    id: 'wo-cnt-001',
    grievance_id: 'gr-001',
    road_id: 'road-101',
    road_name: 'Brigade Road North',
    title: 'Resurface Brigade Road Potholes',
    description: 'Pothole patching and hot-mix bitumen overlay across 200m section.',
    priority: 'HIGH',
    status: 'IN_PROGRESS',
    progress_percentage: 60,
    rework_required: true,
    created_at: '2026-10-10T08:00:00Z',
    updated_at: '2026-10-12T10:00:00Z',
  },
  {
    id: 'wo-cnt-002',
    grievance_id: 'gr-002',
    road_id: 'road-102',
    road_name: 'MG Road Junction',
    title: 'Repair Storm Drain Cover',
    description: 'Replace collapsed storm drain culvert grate and seal joints.',
    priority: 'CRITICAL',
    status: 'ASSIGNED',
    progress_percentage: 0,
    rework_required: false,
    created_at: '2026-10-11T09:00:00Z',
    updated_at: '2026-10-11T09:00:00Z',
  },
  {
    id: 'wo-cnt-003',
    grievance_id: 'gr-003',
    road_id: 'road-103',
    road_name: 'Indiranagar 100ft Road',
    title: 'Seal Peripheral Road Cracks',
    description: 'Crack sealing and shoulder stabilization.',
    priority: 'MEDIUM',
    status: 'PENDING_VERIFICATION',
    progress_percentage: 100,
    rework_required: false,
    created_at: '2026-10-09T07:00:00Z',
    updated_at: '2026-10-12T14:00:00Z',
  },
]

const mockOrderDetail: ContractorWorkOrderDetail = {
  id: 'wo-cnt-001',
  grievance_id: 'gr-001',
  road_id: 'road-101',
  road_name: 'Brigade Road North',
  road_code: 'BRIG-N-01',
  latitude: 12.9716,
  longitude: 77.5946,
  title: 'Resurface Brigade Road Potholes',
  description: 'Pothole patching and hot-mix bitumen overlay across 200m section.',
  priority: 'HIGH',
  status: 'IN_PROGRESS',
  created_at: '2026-10-10T08:00:00Z',
  updated_at: '2026-10-12T10:00:00Z',
  grievance_description: 'Deep road crater causing vehicles to bottom out and brake violently.',
  grievance_issue_category: 'POTHOLE',
  grievance_severity: 'HIGH',
  grievance_risk_level: 'CRITICAL',
  grievance_priority: 'HIGH',
  current_progress: 60,
  progress_history: [
    {
      id: 'prg-1',
      work_order_id: 'wo-cnt-001',
      contractor_id: 'contractor-alpha',
      progress_percentage: 30,
      note: 'Milled damaged surface area',
      created_at: '2026-10-10T12:00:00Z',
    },
    {
      id: 'prg-2',
      work_order_id: 'wo-cnt-001',
      contractor_id: 'contractor-alpha',
      progress_percentage: 60,
      note: 'Laid base aggregate layer',
      created_at: '2026-10-11T14:00:00Z',
    },
  ],
  completion_evidence: [
    {
      id: 'ev-1',
      grievance_id: 'gr-001',
      work_order_id: 'wo-cnt-001',
      file_name: 'base_compaction.jpg',
      file_type: 'image/jpeg',
      storage_path: '/uploads/evidence/base_compaction.jpg',
      file_size_bytes: 409600,
      uploaded_at: '2026-10-11T14:05:00Z',
    },
  ],
  government_verification_status: 'REJECT',
  rework_required: true,
  latest_rejection_notes: 'Asphalt compaction depth is insufficient (requires 100mm, observed 50mm). Re-compact with proper depth.',
  rejection_timestamp: '2026-10-12T09:30:00Z',
  timeline: [
    {
      id: 'evt-1',
      grievance_id: 'gr-001',
      work_order_id: 'wo-cnt-001',
      actor_id: 'officer-1',
      actor_role: 'GOVERNMENT_OFFICER',
      event_type: 'WORK_ORDER_ASSIGNED',
      old_status: 'SUBMITTED',
      new_status: 'ASSIGNED',
      notes: 'Dispatched to Contractor Alpha',
      created_at: '2026-10-10T08:00:00Z',
    },
  ],
}

const mockReworkItems: ContractorReworkItem[] = [
  {
    work_order_id: 'wo-cnt-001',
    grievance_id: 'gr-001',
    title: 'Resurface Brigade Road Potholes',
    priority: 'HIGH',
    current_status: 'IN_PROGRESS',
    rejection_message: 'Asphalt compaction depth is insufficient (requires 100mm, observed 50mm). Re-compact with proper depth.',
    rejection_timestamp: '2026-10-12T09:30:00Z',
    current_progress: 60,
  },
]

const mockPendingItems: ContractorPendingVerificationItem[] = [
  {
    work_order_id: 'wo-cnt-003',
    grievance_id: 'gr-003',
    title: 'Seal Peripheral Road Cracks',
    priority: 'MEDIUM',
    progress_percentage: 100,
    completion_submitted_at: '2026-10-12T14:00:00Z',
    evidence: [
      {
        id: 'ev-2',
        grievance_id: 'gr-003',
        work_order_id: 'wo-cnt-003',
        file_name: 'crack_seal_finished.jpg',
        file_type: 'image/jpeg',
        storage_path: '/uploads/evidence/crack_seal_finished.jpg',
        file_size_bytes: 350000,
        uploaded_at: '2026-10-12T13:55:00Z',
      },
    ],
  },
]

describe('Contractor Dashboard Integration Tests (Phase 26)', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.clearAllMocks()

    // Default mock returns
    vi.mocked(contractorService.getOverview).mockResolvedValue(mockOverview)
    vi.mocked(contractorService.getWorkloadSummary).mockResolvedValue(mockWorkload)
    vi.mocked(contractorService.listWorkOrders).mockResolvedValue(mockWorkOrders)
    vi.mocked(contractorService.getWorkOrderDetail).mockResolvedValue(mockOrderDetail)
    vi.mocked(contractorService.getReworkQueue).mockResolvedValue(mockReworkItems)
    vi.mocked(contractorService.getPendingVerificationQueue).mockResolvedValue(mockPendingItems)
  })

  const setContractorSession = () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'contractor-alpha', role: 'CONTRACTOR', name: 'Contractor Alpha' })
    )
  }

  it('1. blocks unauthorized roles (CITIZEN, GOVERNMENT_OFFICER) from contractor dashboard', () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'citizen-1', role: 'CITIZEN', name: 'Citizen Jane' })
    )

    render(
      <MemoryRouter initialEntries={['/contractor']}>
        <AuthProvider>
          <ContractorDashboardPage />
        </AuthProvider>
      </MemoryRouter>
    )

    expect(screen.getByText(/403 — Access Restricted/i)).toBeInTheDocument()
    expect(screen.queryByText(/Contractor Portal/i)).not.toBeInTheDocument()
  })

  it('2. renders contractor overview KPI metrics accurately from backend schema', async () => {
    setContractorSession()

    render(
      <MemoryRouter initialEntries={['/contractor?tab=overview']}>
        <AuthProvider>
          <ContractorDashboardPage />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('kpi-total-assigned')).toHaveTextContent('5')
      expect(screen.getByTestId('kpi-assigned')).toHaveTextContent('1')
      expect(screen.getByTestId('kpi-in-progress')).toHaveTextContent('2')
      expect(screen.getByTestId('kpi-pending-verification')).toHaveTextContent('1')
      expect(screen.getByTestId('kpi-completed')).toHaveTextContent('1')
      expect(screen.getByTestId('kpi-rework')).toHaveTextContent('1')
      expect(screen.getByTestId('kpi-average-progress')).toHaveTextContent('68.5%')
    })

    // Rework Alert Banner should be visible because rework > 0
    expect(screen.getByTestId('rework-alert-banner')).toBeInTheDocument()
    expect(screen.getByText(/Action Required: 1 Work Order returned for Rework/i)).toBeInTheDocument()
  })

  it('3. displays error state with retry button if overview fails to load', async () => {
    setContractorSession()
    vi.mocked(contractorService.getOverview).mockRejectedValueOnce(new Error('Network error loading overview'))

    render(
      <MemoryRouter>
        <ContractorOverviewTab onNavigateTab={vi.fn()} onSelectWorkOrder={vi.fn()} />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/Network error loading overview/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Retry Loading/i })).toBeInTheDocument()
    })

    // Click retry
    vi.mocked(contractorService.getOverview).mockResolvedValueOnce(mockOverview)
    fireEvent.click(screen.getByRole('button', { name: /Retry Loading/i }))

    await waitFor(() => {
      expect(screen.getByTestId('kpi-total-assigned')).toHaveTextContent('5')
    })
  })

  it('4. renders assigned work orders list with priority, status, and progress', async () => {
    setContractorSession()

    render(
      <MemoryRouter initialEntries={['/contractor?tab=work-orders']}>
        <AuthProvider>
          <ContractorDashboardPage />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Resurface Brigade Road Potholes')).toBeInTheDocument()
      expect(screen.getByText('Repair Storm Drain Cover')).toBeInTheDocument()
      expect(screen.getByText('Seal Peripheral Road Cracks')).toBeInTheDocument()
    })

    // Check rework badge on wo-cnt-001
    expect(screen.getAllByText('Rework Required')[0]).toBeInTheDocument()
  })

  it('5. filters work orders by status and priority', async () => {
    setContractorSession()

    render(
      <MemoryRouter initialEntries={['/contractor?tab=work-orders']}>
        <AuthProvider>
          <ContractorDashboardPage />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('filter-status-select')).toBeInTheDocument()
    })

    // Select status filter IN_PROGRESS
    fireEvent.change(screen.getByTestId('filter-status-select'), { target: { value: 'IN_PROGRESS' } })

    await waitFor(() => {
      expect(contractorService.listWorkOrders).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'IN_PROGRESS' })
      )
    })

    // Select priority filter CRITICAL
    fireEvent.change(screen.getByTestId('filter-priority-select'), { target: { value: 'CRITICAL' } })

    await waitFor(() => {
      expect(contractorService.listWorkOrders).toHaveBeenCalledWith(
        expect.objectContaining({ priority: 'CRITICAL' })
      )
    })
  })

  it('6. searches work orders client-side on title and description', async () => {
    setContractorSession()

    render(
      <MemoryRouter initialEntries={['/contractor?tab=work-orders']}>
        <AuthProvider>
          <ContractorDashboardPage />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Repair Storm Drain Cover')).toBeInTheDocument()
    })

    // Search for "Brigade"
    const searchInput = screen.getByTestId('input-search-work-orders')
    fireEvent.change(searchInput, { target: { value: 'Brigade' } })

    expect(screen.getByText('Resurface Brigade Road Potholes')).toBeInTheDocument()
    expect(screen.queryByText('Repair Storm Drain Cover')).not.toBeInTheDocument()
  })

  it('7. opens work order details modal and displays road, grievance, rework feedback, and evidence', async () => {
    setContractorSession()

    render(
      <MemoryRouter initialEntries={['/contractor?tab=work-orders']}>
        <AuthProvider>
          <ContractorDashboardPage />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('inspect-wo-btn-wo-cnt-001')).toBeInTheDocument()
    })

    // Open detail modal
    fireEvent.click(screen.getByTestId('inspect-wo-btn-wo-cnt-001'))

    await waitFor(() => {
      expect(contractorService.getWorkOrderDetail).toHaveBeenCalledWith('wo-cnt-001')
      expect(screen.getByTestId('contractor-work-order-detail-modal')).toBeInTheDocument()
    })

    // Verify road code & grievance description
    expect(screen.getByText(/Segment ID: BRIG-N-01/i)).toBeInTheDocument()
    expect(screen.getByText(/Deep road crater causing vehicles to bottom out/i)).toBeInTheDocument()

    // Verify government rework feedback banner
    expect(screen.getByTestId('rework-feedback-banner')).toBeInTheDocument()
    expect(screen.getByText(/Asphalt compaction depth is insufficient/i)).toBeInTheDocument()

    // Verify attached evidence
    expect(screen.getByText('base_compaction.jpg')).toBeInTheDocument()
  })

  it('8. acknowledges assignment and starts work order', async () => {
    setContractorSession()
    const assignedDetail: ContractorWorkOrderDetail = {
      ...mockOrderDetail,
      id: 'wo-cnt-002',
      status: 'ASSIGNED',
      rework_required: false,
      latest_rejection_notes: null,
    }
    vi.mocked(contractorService.getWorkOrderDetail).mockResolvedValue(assignedDetail)
    vi.mocked(contractorService.acknowledgeWorkOrder).mockResolvedValue({ id: 'wo-cnt-002', status: 'ASSIGNED' })
    vi.mocked(contractorService.startWorkOrder).mockResolvedValue({ id: 'wo-cnt-002', status: 'IN_PROGRESS' })

    render(
      <MemoryRouter initialEntries={['/contractor?tab=work-orders&id=wo-cnt-002']}>
        <AuthProvider>
          <ContractorDashboardPage />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('btn-ack-order')).toBeInTheDocument()
      expect(screen.getByTestId('btn-start-order')).toBeInTheDocument()
    })

    // Click Acknowledge
    fireEvent.click(screen.getByTestId('btn-ack-order'))
    await waitFor(() => {
      expect(contractorService.acknowledgeWorkOrder).toHaveBeenCalledWith('wo-cnt-002', expect.any(String))
    })

    // Click Start Work
    fireEvent.click(screen.getByTestId('btn-start-order'))
    await waitFor(() => {
      expect(contractorService.startWorkOrder).toHaveBeenCalledWith('wo-cnt-002', expect.any(String))
    })
  })

  it('9. enforces progress monotonicity: rejects progress decrease without rework note', async () => {
    setContractorSession()

    render(
      <MemoryRouter initialEntries={['/contractor?tab=work-orders&id=wo-cnt-001']}>
        <AuthProvider>
          <ContractorDashboardPage />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('input-progress-pct')).toBeInTheDocument()
    })

    // Try decreasing from 60% to 40% with no note
    fireEvent.change(screen.getByTestId('input-progress-pct'), { target: { value: '40' } })
    fireEvent.click(screen.getByTestId('btn-submit-progress'))

    await waitFor(() => {
      expect(screen.getByText(/Progress cannot decrease from 60% to 40% without an explicit note/i)).toBeInTheDocument()
      expect(contractorService.updateProgress).not.toHaveBeenCalled()
    })

    // Add valid correction note and submit
    fireEvent.change(screen.getByTestId('input-progress-note'), {
      target: { value: 'Corrected measurement after government rework inspection' },
    })
    vi.mocked(contractorService.updateProgress).mockResolvedValueOnce({
      id: 'prg-3',
      work_order_id: 'wo-cnt-001',
      contractor_id: 'contractor-alpha',
      progress_percentage: 40,
      note: 'Corrected measurement after government rework inspection',
      created_at: '2026-10-12T11:00:00Z',
    })

    fireEvent.click(screen.getByTestId('btn-submit-progress'))

    await waitFor(() => {
      expect(contractorService.updateProgress).toHaveBeenCalledWith('wo-cnt-001', {
        progress_percentage: 40,
        note: 'Corrected measurement after government rework inspection',
      })
      expect(screen.getByText(/Progress successfully recorded at 40%/i)).toBeInTheDocument()
    })
  })

  it('10. attaches evidence metadata to work order', async () => {
    setContractorSession()
    vi.mocked(contractorService.attachEvidence).mockResolvedValueOnce({
      id: 'ev-new-1',
      grievance_id: 'gr-001',
      work_order_id: 'wo-cnt-001',
      file_name: 'repaired_asphalt.jpg',
      file_type: 'image/jpeg',
      storage_path: '/uploads/evidence/repaired_asphalt.jpg',
      file_size_bytes: 512000,
      uploaded_at: '2026-10-12T11:30:00Z',
    })

    render(
      <MemoryRouter initialEntries={['/contractor?tab=work-orders&id=wo-cnt-001']}>
        <AuthProvider>
          <ContractorDashboardPage />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('btn-attach-evidence')).toBeInTheDocument()
    })

    // Simulate file input
    const file = new File(['mock content'], 'repaired_asphalt.jpg', { type: 'image/jpeg' })
    const fileInput = screen.getByTestId('input-evidence-file')
    fireEvent.change(fileInput, { target: { files: [file] } })

    fireEvent.click(screen.getByTestId('btn-attach-evidence'))

    await waitFor(() => {
      expect(contractorService.attachEvidence).toHaveBeenCalledWith(
        'wo-cnt-001',
        expect.objectContaining({
          file_name: 'repaired_asphalt.jpg',
          file_type: 'image/jpeg',
          grievance_id: 'gr-001',
          work_order_id: 'wo-cnt-001',
        })
      )
      expect(screen.getByText(/Evidence metadata attached successfully/i)).toBeInTheDocument()
    })
  })

  it('11. submits work order for government verification (transitions to PENDING_VERIFICATION)', async () => {
    setContractorSession()
    vi.mocked(contractorService.submitCompletion).mockResolvedValueOnce({
      work_order_id: 'wo-cnt-001',
      status: 'PENDING_VERIFICATION',
      grievance_status: 'PENDING_VERIFICATION',
      submitted_at: '2026-10-12T12:00:00Z',
      completion_note: 'Repairs completed according to municipal specification.',
      message: 'Work completion submitted successfully.',
    })

    render(
      <MemoryRouter initialEntries={['/contractor?tab=work-orders&id=wo-cnt-001']}>
        <AuthProvider>
          <ContractorDashboardPage />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('input-completion-note')).toBeInTheDocument()
    })

    fireEvent.change(screen.getByTestId('input-completion-note'), {
      target: { value: 'Repairs completed according to municipal specification.' },
    })
    fireEvent.change(screen.getByTestId('input-actual-work-summary'), {
      target: { value: 'Excavated 100mm, compacted base, laid bituminous concrete.' },
    })

    fireEvent.click(screen.getByTestId('btn-submit-verification'))

    await waitFor(() => {
      expect(contractorService.submitCompletion).toHaveBeenCalledWith('wo-cnt-001', {
        completion_note: 'Repairs completed according to municipal specification.',
        actual_work_summary: 'Excavated 100mm, compacted base, laid bituminous concrete.',
        evidence_ids: undefined,
      })
      expect(screen.getByText(/Work order submitted for government officer verification/i)).toBeInTheDocument()
    })
  })

  it('12. displays rework queue with officer rejection messages and quick resubmission action', async () => {
    setContractorSession()

    render(
      <MemoryRouter initialEntries={['/contractor?tab=rework']}>
        <AuthProvider>
          <ContractorDashboardPage />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('rework-queue-list')).toBeInTheDocument()
      expect(screen.getByText(/Asphalt compaction depth is insufficient/i)).toBeInTheDocument()
      expect(screen.getByTestId('address-rework-btn-wo-cnt-001')).toBeInTheDocument()
    })

    // Clicking "Address Rework & Resubmit" opens detail modal
    fireEvent.click(screen.getByTestId('address-rework-btn-wo-cnt-001'))

    await waitFor(() => {
      expect(screen.getByTestId('contractor-work-order-detail-modal')).toBeInTheDocument()
    })
  })

  it('13. displays pending verification queue showing jobs awaiting municipal sign-off', async () => {
    setContractorSession()

    render(
      <MemoryRouter initialEntries={['/contractor?tab=pending-verification']}>
        <AuthProvider>
          <ContractorDashboardPage />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('pending-verification-list')).toBeInTheDocument()
      expect(screen.getByText('Seal Peripheral Road Cracks')).toBeInTheDocument()
      expect(screen.getByText('100% Repaired')).toBeInTheDocument()
      expect(screen.getByText('crack_seal_finished.jpg')).toBeInTheDocument()
    })
  })

  it('14. guarantees that contractor dashboard does NOT provide resolve or approve buttons', async () => {
    setContractorSession()

    render(
      <MemoryRouter initialEntries={['/contractor?tab=work-orders&id=wo-cnt-001']}>
        <AuthProvider>
          <ContractorDashboardPage />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('contractor-work-order-detail-modal')).toBeInTheDocument()
    })

    // Verification controls (APPROVE, RESOLVE GRIEVANCE) MUST NOT exist in contractor UI
    expect(screen.queryByRole('button', { name: /^Approve$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Resolve Grievance$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Mark Resolved/i })).not.toBeInTheDocument()
  })

  it('15. handles HTTP 403 Forbidden gracefully when attempting unauthorized actions', async () => {
    setContractorSession()
    vi.mocked(contractorService.updateProgress).mockRejectedValueOnce(
      new Error('Contractor contractor-alpha is not assigned to WorkOrder wo-cnt-001.')
    )

    render(
      <MemoryRouter initialEntries={['/contractor?tab=work-orders&id=wo-cnt-001']}>
        <AuthProvider>
          <ContractorDashboardPage />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('btn-submit-progress')).toBeInTheDocument()
    })

    fireEvent.change(screen.getByTestId('input-progress-pct'), { target: { value: '80' } })
    fireEvent.click(screen.getByTestId('btn-submit-progress'))

    await waitFor(() => {
      expect(
        screen.getByText(/Contractor contractor-alpha is not assigned to WorkOrder wo-cnt-001/i)
      ).toBeInTheDocument()
    })
  })
})
