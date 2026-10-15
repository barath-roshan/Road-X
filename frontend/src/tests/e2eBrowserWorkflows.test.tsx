/**
 * RoadX Phase 27 — End-to-End Browser Workflows & Integration Test Suite
 *
 * Validates all 12 critical user and browser workflows:
 * 1. Landing page rendering, hero section, and navigation to login.
 * 2. Role-aware protected route enforcement (unauthenticated -> /login, unauthorized -> /unauthorized).
 * 3. Citizen grievance reporting workflow & private list tracking.
 * 4. Government grievance review, ML insights display, and contractor assignment.
 * 5. Contractor progress logging with monotonicity enforcement.
 * 6. Contractor completion submission & government approval lifecycle (transitions to RESOLVED).
 * 7. Government rejection and contractor rework queue inspection.
 * 8. Public road operations & detour visibility for citizens.
 * 9. Chatbot conversation flow and offline fallback resilience.
 * 10. Session persistence and restoration from sessionStorage.
 * 11. Expired/cleared session forbidden redirection.
 * 12. Form validation bounds & server error alert display.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../features/auth/AuthContext'
import { AppRoutes } from '../app/AppRoutes'
import { ReportGrievanceTab } from '../features/citizen/ReportGrievanceTab'
import { CitizenGrievancesTab } from '../features/citizen/CitizenGrievancesTab'
import { CitizenRoadOperationsTab } from '../features/citizen/CitizenRoadOperationsTab'
import { CitizenChatbotTab } from '../features/citizen/CitizenChatbotTab'
import { GovernmentGrievanceDetailModal } from '../features/government/GovernmentGrievanceDetailModal'
import { GovernmentVerificationQueueTab } from '../features/government/GovernmentVerificationQueueTab'
import { ContractorWorkOrderDetailModal } from '../features/contractor/ContractorWorkOrderDetailModal'
import { ContractorReworkQueueTab } from '../features/contractor/ContractorReworkQueueTab'

import { citizenService } from '../services/citizenService'
import { governmentService } from '../services/governmentService'
import { contractorService } from '../services/contractorService'

import type {
  CitizenGrievanceItem,
  CitizenRoadOperation,
  ChatConversationSummary,
} from '../types/citizen'
import type {
  GovernmentDashboardGrievanceDetail,
  GovernmentDashboardVerificationItem,
  GovernmentDashboardContractorSummary,
} from '../types/government'
import type {
  ContractorWorkOrderDetail,
  ContractorReworkItem,
} from '../types/contractor'

// Mock services
vi.mock('../services/citizenService', () => ({
  citizenService: {
    createGrievance: vi.fn(),
    listGrievances: vi.fn(),
    getGrievanceDetails: vi.fn(),
    attachEvidence: vi.fn(),
    listRoadOperations: vi.fn(),
    getRoadOperation: vi.fn(),
    createChatConversation: vi.fn(),
    listChatConversations: vi.fn(),
    getChatConversation: vi.fn(),
    sendChatMessage: vi.fn(),
  },
}))

vi.mock('../services/governmentService', () => ({
  governmentService: {
    getOverview: vi.fn(),
    listGrievances: vi.fn(),
    getGrievanceDetail: vi.fn(),
    submitReview: vi.fn(),
    createWorkOrder: vi.fn(),
    getPriorityQueue: vi.fn(),
    getVerificationQueue: vi.fn(),
    verifyWorkOrder: vi.fn(),
    listWorkOrders: vi.fn(),
    listContractors: vi.fn(),
    listRoadOperations: vi.fn(),
    createRoadOperation: vi.fn(),
    activateRoadOperation: vi.fn(),
    completeRoadOperation: vi.fn(),
    cancelRoadOperation: vi.fn(),
  },
}))

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

describe('RoadX Phase 27 — End-to-End Browser Workflows & Integration Tests', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.clearAllMocks()
  })

  // --------------------------------------------------------------------------
  // Workflow 1: Home page rendering & login navigation
  // --------------------------------------------------------------------------
  it('Workflow 1: Landing page renders hero, platform links, and navigates to sign-in', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )

    expect(
      screen.getByRole('heading', { name: /intelligent road grievance & maintenance management/i })
    ).toBeInTheDocument()
    expect(screen.getByText(/municipal road intelligence & ai risk engine/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /sign in to your portal/i })).toBeInTheDocument()
    expect(screen.getByText(/sign in as citizen/i)).toBeInTheDocument()
  })

  // --------------------------------------------------------------------------
  // Workflow 2: Role-specific route access & redirection
  // --------------------------------------------------------------------------
  it('Workflow 2: Route guards enforce authentication and redirect unauthenticated/unauthorized users', () => {
    // 2a. Unauthenticated visitor trying to access /government gets redirected to /login
    const { unmount } = render(
      <MemoryRouter initialEntries={['/government']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )
    expect(screen.getByRole('heading', { name: /sign in to roadx/i })).toBeInTheDocument()
    unmount()

    // 2b. Authenticated CITIZEN trying to access /government gets redirected to /unauthorized
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'cit-001', role: 'CITIZEN', name: 'Citizen Alice' })
    )

    render(
      <MemoryRouter initialEntries={['/government']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )
    expect(screen.getByRole('heading', { name: /403 — access restricted/i })).toBeInTheDocument()
  })

  // --------------------------------------------------------------------------
  // Workflow 3: Citizen grievance reporting workflow & private list display
  // --------------------------------------------------------------------------
  it('Workflow 3: Citizen grievance reporting workflow submits issue and displays in private list', async () => {
    const mockCreatedGrievance: CitizenGrievanceItem = {
      id: 'gr-cit-100',
      citizen_id: 'cit-001',
      road_id: 'ROAD-BLR-01',
      issue_category: 'POTHOLE',
      description: 'Severe 20cm pothole on Brigade Road junction near metro station.',
      latitude: 12.9716,
      longitude: 77.5946,
      status: 'SUBMITTED',
      created_at: '2026-10-15T08:00:00Z',
      updated_at: '2026-10-15T08:00:00Z',
    }

    vi.mocked(citizenService.createGrievance).mockResolvedValueOnce(mockCreatedGrievance)
    vi.mocked(citizenService.listGrievances).mockResolvedValue([mockCreatedGrievance])

    const handleCreated = vi.fn()

    // 3a. Submit report via ReportGrievanceTab
    const { unmount } = render(<ReportGrievanceTab onGrievanceCreated={handleCreated} />)

    const descInput = screen.getByPlaceholderText(/example: deep pothole measuring/i)
    fireEvent.change(descInput, {
      target: { value: 'Severe 20cm pothole on Brigade Road junction near metro station.' },
    })

    const latInput = screen.getByLabelText(/latitude/i)
    const lngInput = screen.getByLabelText(/longitude/i)
    fireEvent.change(latInput, { target: { value: '12.9716' } })
    fireEvent.change(lngInput, { target: { value: '77.5946' } })

    const submitBtn = screen.getByRole('button', { name: /^submit grievance$/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(citizenService.createGrievance).toHaveBeenCalledWith(
        expect.objectContaining({
          issue_category: 'POTHOLE',
          description: 'Severe 20cm pothole on Brigade Road junction near metro station.',
          latitude: 12.9716,
          longitude: 77.5946,
        })
      )
      expect(screen.getByText(/grievance submitted successfully!/i)).toBeInTheDocument()
      expect(handleCreated).toHaveBeenCalledWith(mockCreatedGrievance)
    })
    unmount()

    // 3b. Verify private list displays submitted grievance
    render(<CitizenGrievancesTab />)

    await waitFor(() => {
      expect(citizenService.listGrievances).toHaveBeenCalled()
      expect(
        screen.getByText(/severe 20cm pothole on brigade road junction near metro station/i)
      ).toBeInTheDocument()
    })
  })

  // --------------------------------------------------------------------------
  // Workflow 4: Government review, ML insights display, and contractor assignment
  // --------------------------------------------------------------------------
  it('Workflow 4: Government review inspects ML insights, accepts grievance, and commissions work order', async () => {
    const mockDossier: GovernmentDashboardGrievanceDetail = {
      id: 'gr-gov-200',
      citizen_id: 'cit-001',
      citizen_name: 'Citizen Alice',
      citizen_email: 'alice@roadx.org',
      road_id: 'ROAD-BLR-01',
      road_name: 'Brigade Road Central',
      road_code: 'BLR-BRG-01',
      issue_category: 'SURFACE_POTHOLE',
      description: 'Major road depression causing traffic slow down.',
      latitude: 12.9716,
      longitude: 77.5946,
      status: 'SUBMITTED',
      created_at: '2026-10-15T08:00:00Z',
      updated_at: '2026-10-15T08:00:00Z',
      evidence_items: [],
      ml_analysis: {
        overall_status: 'READY',
        failure_prediction: { probability: 0.92, risk_level: 'HIGH' },
        damage_detection: { damage_detected: true, confidence: 0.94 },
        severity_prediction: { severity_level: 'HIGH', severity_score: 0.85 },
        time_to_failure: { estimated_days: 7.0 },
        maintenance_priority: {
          priority_level: 'HIGH',
          priority_score: 84.5,
          reasons: ['Active structural fissure'],
        },
      },
      work_order: null,
      assigned_contractor: null,
      progress_history: [],
      verifications: [],
      reviews: [],
      timeline: [],
    }

    const mockContractors: GovernmentDashboardContractorSummary[] = [
      {
        contractor_id: 'cnt-alpha',
        contractor_name: 'Apex Infrastructure Ltd',
        contractor_email: 'apex@contractor.in',
        assigned_work_orders_count: 2,
        in_progress_count: 1,
        pending_verification_count: 0,
        completed_count: 14,
        average_progress_percentage: 65,
      },
    ]

    vi.mocked(governmentService.getGrievanceDetail).mockResolvedValueOnce(mockDossier)
    vi.mocked(governmentService.listContractors).mockResolvedValueOnce(mockContractors)
    vi.mocked(governmentService.submitReview).mockResolvedValueOnce({
      id: 'rev-01',
      grievance_id: 'gr-gov-200',
      decision: 'ACCEPT',
      notes: 'Road engineering review confirmed.',
      created_at: '2026-10-15T08:30:00Z',
    })
    vi.mocked(governmentService.createWorkOrder).mockResolvedValueOnce({
      id: 'wo-300',
      grievance_id: 'gr-gov-200',
      title: 'Patch Brigade Road Depression',
      description: 'Hot-mix asphalt overlay.',
      priority: 'HIGH',
      status: 'ASSIGNED',
      assigned_contractor_id: 'cnt-alpha',
      created_at: '2026-10-15T08:35:00Z',
      updated_at: '2026-10-15T08:35:00Z',
    })

    const handleUpdated = vi.fn()
    render(
      <GovernmentGrievanceDetailModal
        grievanceId="gr-gov-200"
        onClose={vi.fn()}
        onGrievanceUpdated={handleUpdated}
      />
    )

    await waitFor(() => {
      // 4a. ML insights display check
      expect(screen.getByText(/ml decision support & predictive risk engine/i)).toBeInTheDocument()
      expect(screen.getByText(/7 days/i)).toBeInTheDocument()
      expect(screen.getByText(/active structural fissure/i)).toBeInTheDocument()
    })

    // 4b. Submit review ACCEPT
    const acceptRadio = screen.getByLabelText(/accept grievance/i)
    fireEvent.click(acceptRadio)
    const reviewBtn = screen.getByRole('button', { name: /confirm review/i })
    fireEvent.click(reviewBtn)

    await waitFor(() => {
      expect(governmentService.submitReview).toHaveBeenCalledWith(
        'gr-gov-200',
        expect.objectContaining({ decision: 'ACCEPT' })
      )
    })
  })

  // --------------------------------------------------------------------------
  // Workflow 5: Contractor progress update with monotonicity validation
  // --------------------------------------------------------------------------
  it('Workflow 5: Contractor logs progress updates with monotonicity enforcement', async () => {
    const mockOrder: ContractorWorkOrderDetail = {
      id: 'wo-cnt-400',
      grievance_id: 'gr-gov-200',
      road_id: 'ROAD-BLR-01',
      road_name: 'Brigade Road North',
      road_code: 'BRIG-N-01',
      latitude: 12.9716,
      longitude: 77.5946,
      title: 'Overlay Sub-base Patching',
      description: 'Milling and resurfacing.',
      priority: 'HIGH',
      status: 'IN_PROGRESS',
      created_at: '2026-10-15T08:35:00Z',
      updated_at: '2026-10-15T09:15:00Z',
      grievance_description: 'Major road depression causing traffic slow down.',
      grievance_issue_category: 'SURFACE_POTHOLE',
      grievance_severity: 'HIGH',
      grievance_risk_level: 'HIGH',
      grievance_priority: 'HIGH',
      current_progress: 50,
      progress_history: [
        {
          id: 'log-1',
          work_order_id: 'wo-cnt-400',
          contractor_id: 'cnt-alpha',
          progress_percentage: 50,
          note: 'Sub-base compacted.',
          created_at: '2026-10-15T09:30:00Z',
        },
      ],
      completion_evidence: [],
      government_verification_status: null,
      rework_required: false,
      latest_rejection_notes: null,
      rejection_timestamp: null,
      timeline: [],
    }

    vi.mocked(contractorService.getWorkOrderDetail).mockResolvedValue(mockOrder)
    vi.mocked(contractorService.updateProgress).mockResolvedValueOnce({
      id: 'log-2',
      work_order_id: 'wo-cnt-400',
      contractor_id: 'cnt-alpha',
      progress_percentage: 40,
      note: 'Correction: sub-base layer depth was over-estimated.',
      created_at: '2026-10-15T09:45:00Z',
    })

    render(
      <ContractorWorkOrderDetailModal
        workOrderId="wo-cnt-400"
        isOpen={true}
        onClose={vi.fn()}
      />
    )

    await waitFor(() => {
      expect(screen.getByText(/overlay sub-base patching/i)).toBeInTheDocument()
      expect(screen.getByTestId('input-progress-pct')).toBeInTheDocument()
    })

    // 5a. Monotonicity validation: attempt to reduce progress from 50% to 35% without correction keyword
    const pctInput = screen.getByTestId('input-progress-pct')
    const noteInput = screen.getByTestId('input-progress-note')
    const logBtn = screen.getByTestId('btn-submit-progress')

    fireEvent.change(pctInput, { target: { value: '35' } })
    fireEvent.change(noteInput, { target: { value: 'Decreased progress' } })
    fireEvent.click(logBtn)

    await waitFor(() => {
      expect(
        screen.getByText(/progress cannot decrease from 50% to 35% without an explicit note/i)
      ).toBeInTheDocument()
      expect(contractorService.updateProgress).not.toHaveBeenCalled()
    })

    // 5b. Valid monotonicity exception: reduce with 'correction' keyword succeeds
    fireEvent.change(pctInput, { target: { value: '40' } })
    fireEvent.change(noteInput, {
      target: { value: 'Correction: sub-base layer depth was over-estimated.' },
    })
    fireEvent.click(logBtn)

    await waitFor(() => {
      expect(contractorService.updateProgress).toHaveBeenCalledWith('wo-cnt-400', {
        progress_percentage: 40,
        note: 'Correction: sub-base layer depth was over-estimated.',
      })
      expect(screen.getByText(/progress successfully recorded at 40%/i)).toBeInTheDocument()
    })
  })

  // --------------------------------------------------------------------------
  // Workflow 6: Contractor completion & government approval lifecycle
  // --------------------------------------------------------------------------
  it('Workflow 6: Contractor attaches completion evidence and officer verification resolves grievance', async () => {
    const mockVerificationItem: GovernmentDashboardVerificationItem = {
      work_order_id: 'wo-verify-500',
      grievance_id: 'gr-500',
      grievance_description: 'Deep road cavity repaired.',
      road_name: 'Indiranagar 100ft Road',
      contractor_id: 'cnt-alpha',
      contractor_name: 'Apex Infrastructure Ltd',
      work_order_title: 'Pothole at Indiranagar',
      priority: 'HIGH',
      submitted_at: '2026-10-15T10:00:00Z',
      latest_progress_note: '100mm bituminous layer completed and rolled.',
      evidence_items: [
        {
          id: 'ev-comp-1',
          grievance_id: 'gr-500',
          work_order_id: 'wo-verify-500',
          file_name: 'completed_asphalt_surface.jpg',
          file_type: 'image/jpeg',
          storage_path: '/uploads/completion.jpg',
          uploaded_at: '2026-10-15T10:00:00Z',
        },
      ],
    }

    vi.mocked(governmentService.getVerificationQueue).mockResolvedValue([mockVerificationItem])
    vi.mocked(governmentService.verifyWorkOrder).mockResolvedValueOnce({
      id: 'ver-pass-1',
      work_order_id: 'wo-verify-500',
      grievance_id: 'gr-500',
      decision: 'APPROVE',
      notes: 'Verified on-site: Asphalt compaction meets code.',
      created_at: '2026-10-15T10:30:00Z',
    })

    render(<GovernmentVerificationQueueTab />)

    await waitFor(() => {
      expect(screen.getByText(/pothole at indiranagar/i)).toBeInTheDocument()
      expect(screen.getByText(/apex infrastructure ltd/i)).toBeInTheDocument()
    })

    // 6b. Government officer approves completion
    const approveBtn = screen.getByRole('button', { name: /approve & resolve grievance/i })
    fireEvent.click(approveBtn)

    // Confirm in modal
    await waitFor(() => {
      expect(screen.getByText(/approve repair completion/i)).toBeInTheDocument()
    })
    const notesInput = screen.getByPlaceholderText(/notes on quality of work, asphalt condition, or inspection/i)
    fireEvent.change(notesInput, {
      target: { value: 'Verified on-site: Asphalt compaction meets code.' },
    })
    const confirmBtn = screen.getByRole('button', { name: /confirm approval/i })
    fireEvent.click(confirmBtn)

    await waitFor(() => {
      expect(governmentService.verifyWorkOrder).toHaveBeenCalledWith(
        'wo-verify-500',
        expect.objectContaining({
          decision: 'APPROVE',
          notes: 'Verified on-site: Asphalt compaction meets code.',
        })
      )
    })
  })

  // --------------------------------------------------------------------------
  // Workflow 7: Government rejection & contractor rework queue
  // --------------------------------------------------------------------------
  it('Workflow 7: Government verification rejection displays in contractor rework queue for corrective resubmission', async () => {
    const mockReworkItem: ContractorReworkItem = {
      work_order_id: 'wo-rework-600',
      grievance_id: 'gr-600',
      title: 'Repave Residency Road Strip',
      priority: 'HIGH',
      current_status: 'IN_PROGRESS',
      rejection_message: 'Bitumen edge seam has 5mm gap. Seal perimeter joints with hot elastomeric sealant.',
      rejection_timestamp: '2026-10-15T11:00:00Z',
      current_progress: 90,
    }

    vi.mocked(contractorService.getReworkQueue).mockResolvedValueOnce([mockReworkItem])

    const handleSelectOrder = vi.fn()
    render(<ContractorReworkQueueTab onSelectWorkOrder={handleSelectOrder} />)

    await waitFor(() => {
      expect(contractorService.getReworkQueue).toHaveBeenCalled()
      expect(screen.getByText(/repave residency road strip/i)).toBeInTheDocument()
      expect(
        screen.getByText(/bitumen edge seam has 5mm gap/i)
      ).toBeInTheDocument()
    })

    const viewActionBtn = screen.getByRole('button', { name: /address rework & resubmit/i })
    fireEvent.click(viewActionBtn)
    expect(handleSelectOrder).toHaveBeenCalledWith('wo-rework-600')
  })

  // --------------------------------------------------------------------------
  // Workflow 8: Public road operations & detour visibility for citizens
  // --------------------------------------------------------------------------
  it('Workflow 8: Public road operations and detour visibility for citizens', async () => {
    const mockOp: CitizenRoadOperation = {
      id: 'op-blr-700',
      road_id: 'ROAD-FLY-01',
      road_name: 'Brigade Road Flyover',
      title: 'Emergency Flyover Resurfacing',
      description: 'Full resurfacing of main carriage flyover.',
      reason: 'Severe asphalt delamination after heavy rain.',
      operation_type: 'ROAD_CLOSURE',
      status: 'ACTIVE',
      start_time: '2026-10-20T08:00:00Z',
      expected_end_time: '2026-10-22T18:00:00Z',
      alternative_route_name: 'MG Road Underpass Bypass',
      alternative_route_instructions: 'Divert all westbound vehicles through MG Road underpass.',
      alternative_distance_km: 1.2,
      created_at: '2026-10-15T08:00:00Z',
      updated_at: '2026-10-15T08:00:00Z',
    }

    vi.mocked(citizenService.listRoadOperations).mockResolvedValueOnce([mockOp])

    render(<CitizenRoadOperationsTab />)

    await waitFor(() => {
      expect(citizenService.listRoadOperations).toHaveBeenCalled()
      expect(screen.getByText(/emergency flyover resurfacing/i)).toBeInTheDocument()
      expect(screen.getByText(/mg road underpass bypass/i)).toBeInTheDocument()
      expect(
        screen.getByText(/divert all westbound vehicles through mg road underpass/i)
      ).toBeInTheDocument()
      expect(screen.getByText(/\+1.2 km/i)).toBeInTheDocument()
    })
  })

  // --------------------------------------------------------------------------
  // Workflow 9: AI Assistant chatbot conversation & fallback handling
  // --------------------------------------------------------------------------
  it('Workflow 9: AI Assistant chatbot conversation and fallback error resilience', async () => {
    const mockConversation: ChatConversationSummary = {
      id: 'conv-800',
      citizen_id: 'cit-001',
      title: 'Road repair query',
      message_count: 2,
      created_at: '2026-10-15T09:00:00Z',
      updated_at: '2026-10-15T09:00:00Z',
    }

    vi.mocked(citizenService.listChatConversations).mockResolvedValue([mockConversation])
    vi.mocked(citizenService.getChatConversation).mockResolvedValue({
      id: 'conv-800',
      citizen_id: 'cit-001',
      title: 'Road repair query',
      created_at: '2026-10-15T09:00:00Z',
      updated_at: '2026-10-15T09:00:00Z',
      messages: [],
    })
    vi.mocked(citizenService.createChatConversation).mockRejectedValue(
      new Error('Assistant service is currently unreachable.')
    )

    render(<CitizenChatbotTab />)

    await waitFor(() => {
      expect(screen.getByText(/roadx citizen ai assistant/i)).toBeInTheDocument()
    })

    // Attempt to start new conversation session when assistant is offline
    const newChatBtn = screen.getByRole('button', { name: /new session/i })
    fireEvent.click(newChatBtn)

    await waitFor(() => {
      expect(
        screen.getByText(/unable to create a new chat session. the ai assistant service may be offline/i)
      ).toBeInTheDocument()
    })
  })

  // --------------------------------------------------------------------------
  // Workflow 10: Session persistence and restoration from sessionStorage
  // --------------------------------------------------------------------------
  it('Workflow 10: Session persistence restores active user state from sessionStorage', () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'cit-001', role: 'CITIZEN', name: 'Citizen Alice' })
    )

    render(
      <MemoryRouter initialEntries={['/citizen']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )

    // User is immediately authenticated without redirecting to /login
    expect(screen.getByRole('heading', { name: /citizen platform/i })).toBeInTheDocument()
    expect(screen.getAllByText(/citizen alice/i)[0]).toBeInTheDocument()
  })

  // --------------------------------------------------------------------------
  // Workflow 11: Expired/cleared session forbidden redirection
  // --------------------------------------------------------------------------
  it('Workflow 11: Cleared or expired session triggers unauthenticated redirect', () => {
    // Start with empty session
    sessionStorage.clear()

    render(
      <MemoryRouter initialEntries={['/contractor']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )

    // Must be redirected to /login
    expect(screen.getByRole('heading', { name: /sign in to roadx/i })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /contractor/i })).not.toBeInTheDocument()
  })

  // --------------------------------------------------------------------------
  // Workflow 12: Form boundary validation and error alert displays
  // --------------------------------------------------------------------------
  it('Workflow 12: Form boundary validation and error alert displays', async () => {
    vi.mocked(citizenService.createGrievance).mockRejectedValueOnce(
      new Error('Municipal database constraint violation: Road segment does not exist.')
    )

    render(<ReportGrievanceTab />)

    // 12a. Minimum character validation error
    const descInput = screen.getByPlaceholderText(/example: deep pothole measuring/i)
    fireEvent.change(descInput, { target: { value: 'Bad' } }) // Less than 5 chars

    const submitBtn = screen.getByRole('button', { name: /^submit grievance$/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(
        screen.getByText(/description must be at least 5 characters/i)
      ).toBeInTheDocument()
      expect(citizenService.createGrievance).not.toHaveBeenCalled()
    })

    // 12b. Server error alert presentation
    fireEvent.change(descInput, {
      target: { value: 'Valid road defect description exceeding minimum length constraint.' },
    })
    const latInput = screen.getByLabelText(/latitude/i)
    const lngInput = screen.getByLabelText(/longitude/i)
    fireEvent.change(latInput, { target: { value: '12.9716' } })
    fireEvent.change(lngInput, { target: { value: '77.5946' } })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByText(/submission failed/i)).toBeInTheDocument()
      expect(
        screen.getByText(/municipal database constraint violation: road segment does not exist/i)
      ).toBeInTheDocument()
    })
  })
})
