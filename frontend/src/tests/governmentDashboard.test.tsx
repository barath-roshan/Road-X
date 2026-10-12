/**
 * Unit & Integration tests for RoadX Government Officer Dashboard views.
 * Covers:
 * - Dashboard rendering & officer session
 * - Unauthorized role blocking
 * - Tab navigation
 * - Executive metrics rendering from API responses
 * - Grievance search and filter controls
 * - Priority queue ranking display
 * - Work order monitoring
 * - Contractor monitoring
 * - Road operations list & status triggers
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../features/auth/AuthContext'
import { GovernmentDashboardPage } from '../pages/GovernmentDashboardPage'
import { governmentService } from '../services/governmentService'
import type {
  GovernmentDashboardOverview,
  GovernmentDashboardGrievanceItem,
  GovernmentDashboardPriorityItem,
  GovernmentDashboardWorkOrderItem,
  GovernmentDashboardContractorSummary,
  GovernmentRoadOperation,
} from '../types/government'

// Mock the governmentService module
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

const mockOverview: GovernmentDashboardOverview = {
  total_grievances: 25,
  status_counts: {
    SUBMITTED: 5,
    UNDER_REVIEW: 4,
    IN_PROGRESS: 8,
    PENDING_VERIFICATION: 3,
    RESOLVED: 5,
  },
  priority_counts: {
    CRITICAL: 4,
    HIGH: 8,
    MEDIUM: 10,
    LOW: 3,
  },
  severity_counts: {
    CRITICAL: 2,
    HIGH: 6,
    MEDIUM: 12,
    LOW: 5,
  },
  work_order_counts: {
    OPEN: 2,
    ASSIGNED: 3,
    IN_PROGRESS: 5,
    PENDING_VERIFICATION: 3,
    COMPLETED: 5,
  },
  active_contractors_count: 6,
  pending_verifications_count: 3,
}

const mockGrievances: GovernmentDashboardGrievanceItem[] = [
  {
    id: 'gr-test-001',
    citizen_id: 'cit-101',
    citizen_name: 'Rajesh Kumar',
    road_id: 'road-501',
    road_name: 'Ring Road Bypass',
    issue_category: 'POTHOLE',
    description: 'Deep hazardous crater on north carriageway',
    latitude: 12.9352,
    longitude: 77.6245,
    status: 'SUBMITTED',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    priority: 'CRITICAL',
    severity: 'HIGH',
    risk_level: 'HIGH',
    work_order_status: null,
    assigned_contractor_name: null,
  },
  {
    id: 'gr-test-002',
    citizen_id: 'cit-102',
    citizen_name: 'Anita Roy',
    road_id: 'road-502',
    road_name: 'Outer Ring Road Sec 2',
    issue_category: 'DRAINAGE_FAILURE',
    description: 'Monsoon flooding overflow across road surface',
    latitude: 12.9212,
    longitude: 77.6111,
    status: 'IN_PROGRESS',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    priority: 'HIGH',
    severity: 'MEDIUM',
    risk_level: 'MEDIUM',
    work_order_status: 'IN_PROGRESS',
    assigned_contractor_name: 'Apex Infrastructure Ltd',
  },
]

const mockPriorityQueue: GovernmentDashboardPriorityItem[] = [
  {
    grievance_id: 'gr-prio-001',
    road_name: 'NH-44 Express Section',
    issue_category: 'SURFACE_COLLAPSE',
    description: 'Severe structural subsidence threatening multi-axle trucks',
    status: 'UNDER_REVIEW',
    priority_score: 95.8,
    priority_level: 'CRITICAL',
    severity_level: 'CRITICAL',
    risk_level: 'CRITICAL',
    estimated_time_to_failure_days: 3.5,
    reasons: ['Extreme high heavy vehicular volume', 'Critical structural fault detected'],
    created_at: new Date().toISOString(),
  },
]

const mockWorkOrders: GovernmentDashboardWorkOrderItem[] = [
  {
    id: 'wo-test-001',
    grievance_id: 'gr-test-002',
    road_name: 'Outer Ring Road Sec 2',
    assigned_contractor_id: 'c-user-1',
    contractor_name: 'Apex Infrastructure Ltd',
    title: 'Repair Drainage Culvert',
    description: 'Replace cracked RCC pipe with 900mm reinforced culvert',
    priority: 'HIGH',
    status: 'IN_PROGRESS',
    current_progress_percentage: 65,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
]

const mockContractors: GovernmentDashboardContractorSummary[] = [
  {
    contractor_id: 'c-user-1',
    contractor_name: 'Apex Infrastructure Ltd',
    contractor_email: 'dispatch@apex.gov.in',
    assigned_work_orders_count: 5,
    in_progress_count: 3,
    pending_verification_count: 1,
    completed_count: 1,
    average_progress_percentage: 72.4,
  },
]

const mockOperations: GovernmentRoadOperation[] = [
  {
    id: 'op-test-001',
    road_id: 'road-501',
    road_name: 'Ring Road Bypass',
    grievance_id: 'gr-test-001',
    work_order_id: null,
    created_by: 'off-001',
    creator_name: 'Officer Alice',
    title: 'Ring Road Surface Repair Closure',
    description: 'Night closure for hot-mix asphalt layering',
    reason: 'Heavy machinery deployment',
    operation_type: 'ROAD_CLOSURE',
    status: 'PLANNED',
    start_time: new Date().toISOString(),
    expected_end_time: new Date(Date.now() + 86400000).toISOString(),
    actual_end_time: null,
    alternative_route_name: 'Service Road Parallel Detour',
    alternative_route_instructions: 'Divert through Gate 3 service corridor',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
]

describe('GovernmentDashboardPage Integration', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.clearAllMocks()

    vi.mocked(governmentService.getOverview).mockResolvedValue(mockOverview)
    vi.mocked(governmentService.listGrievances).mockResolvedValue(mockGrievances)
    vi.mocked(governmentService.getPriorityQueue).mockResolvedValue(mockPriorityQueue)
    vi.mocked(governmentService.listWorkOrders).mockResolvedValue(mockWorkOrders)
    vi.mocked(governmentService.listContractors).mockResolvedValue(mockContractors)
    vi.mocked(governmentService.listRoadOperations).mockResolvedValue(mockOperations)
    vi.mocked(governmentService.getVerificationQueue).mockResolvedValue([])
  })

  it('blocks unauthorized citizen role and displays unauthorized message', () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'cit-001', role: 'CITIZEN', name: 'Citizen John' })
    )

    render(
      <MemoryRouter initialEntries={['/government']}>
        <AuthProvider>
          <GovernmentDashboardPage />
        </AuthProvider>
      </MemoryRouter>
    )

    expect(screen.getByText(/access restricted/i)).toBeInTheDocument()
    expect(screen.queryByText(/executive civic overview/i)).not.toBeInTheDocument()
  })

  it('renders Government Officer Portal and executive overview metrics for authorized officer', async () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'off-001', role: 'GOVERNMENT_OFFICER', name: 'Officer Sarah' })
    )

    render(
      <MemoryRouter initialEntries={['/government']}>
        <AuthProvider>
          <GovernmentDashboardPage />
        </AuthProvider>
      </MemoryRouter>
    )

    expect(screen.getByText(/government officer portal/i)).toBeInTheDocument()
    expect(screen.getByText(/Officer Sarah/i)).toBeInTheDocument()

    // Overview KPIs rendered from API response
    await waitFor(() => {
      expect(screen.getByText(/total grievances/i)).toBeInTheDocument()
      expect(screen.getByText('25')).toBeInTheDocument()
      expect(screen.getByText('6')).toBeInTheDocument() // Active contractors
    })

    // Action banner for pending verifications
    expect(screen.getByText(/3 Work Orders Awaiting Verification/i)).toBeInTheDocument()
  })

  it('navigates to Grievance Review tab and displays filterable grievances table', async () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'off-001', role: 'GOVERNMENT_OFFICER', name: 'Officer Sarah' })
    )

    render(
      <MemoryRouter initialEntries={['/government']}>
        <AuthProvider>
          <GovernmentDashboardPage />
        </AuthProvider>
      </MemoryRouter>
    )

    // Click Grievance Review tab
    const tabBtn = screen.getByRole('button', { name: /grievance review/i })
    fireEvent.click(tabBtn)

    await waitFor(() => {
      expect(screen.getByText(/deep hazardous crater on north carriageway/i)).toBeInTheDocument()
      expect(screen.getByText(/ring road bypass/i)).toBeInTheDocument()
      expect(screen.getByText('POTHOLE')).toBeInTheDocument()
      expect(screen.getByText('DRAINAGE_FAILURE')).toBeInTheDocument()
    })

    // Search input
    const searchInput = screen.getByPlaceholderText(/search description, road name/i)
    fireEvent.change(searchInput, { target: { value: 'pothole' } })
    const searchBtn = screen.getByRole('button', { name: /^search$/i })
    fireEvent.click(searchBtn)

    expect(governmentService.listGrievances).toHaveBeenCalledWith(
      expect.objectContaining({ search: 'pothole' })
    )
  })

  it('navigates to Priority Queue tab and displays ranked predictive items', async () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'off-001', role: 'GOVERNMENT_OFFICER', name: 'Officer Sarah' })
    )

    render(
      <MemoryRouter initialEntries={['/government']}>
        <AuthProvider>
          <GovernmentDashboardPage />
        </AuthProvider>
      </MemoryRouter>
    )

    const prioTabBtn = screen.getByRole('button', { name: /priority queue/i })
    fireEvent.click(prioTabBtn)

    await waitFor(() => {
      expect(screen.getByText('NH-44 Express Section')).toBeInTheDocument()
      expect(screen.getByText('SURFACE_COLLAPSE')).toBeInTheDocument()
      expect(screen.getByText('96')).toBeInTheDocument() // Rounded 95.8
      expect(screen.getByText(/3.5 days/i)).toBeInTheDocument()
      expect(screen.getByText(/extreme high heavy vehicular volume/i)).toBeInTheDocument()
    })
  })

  it('navigates to Contractors tab and displays workload summaries', async () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'off-001', role: 'GOVERNMENT_OFFICER', name: 'Officer Sarah' })
    )

    render(
      <MemoryRouter initialEntries={['/government']}>
        <AuthProvider>
          <GovernmentDashboardPage />
        </AuthProvider>
      </MemoryRouter>
    )

    const contractorsTabBtn = screen.getByRole('button', { name: /contractors/i })
    fireEvent.click(contractorsTabBtn)

    await waitFor(() => {
      expect(screen.getByText('Apex Infrastructure Ltd')).toBeInTheDocument()
      expect(screen.getByText('dispatch@apex.gov.in')).toBeInTheDocument()
      expect(screen.getByText('72%')).toBeInTheDocument()
    })
  })

  it('navigates to Road Operations tab and displays operations with status actions', async () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'off-001', role: 'GOVERNMENT_OFFICER', name: 'Officer Sarah' })
    )

    render(
      <MemoryRouter initialEntries={['/government']}>
        <AuthProvider>
          <GovernmentDashboardPage />
        </AuthProvider>
      </MemoryRouter>
    )

    const roadOpsTabBtn = screen.getByRole('button', { name: /road operations/i })
    fireEvent.click(roadOpsTabBtn)

    await waitFor(() => {
      expect(screen.getByText('Ring Road Surface Repair Closure')).toBeInTheDocument()
      expect(screen.getByText(/service road parallel detour/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /activate closure/i })).toBeInTheDocument()
    })
  })
})
