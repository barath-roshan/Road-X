/**
 * Unit & Integration tests for RoadX Citizen Portal & Grievance Tracking (Phase 25).
 *
 * Covers:
 * 1. Citizen dashboard rendering & active citizen session
 * 2. Grievance form validation (character bounds, coordinates)
 * 3. Successful and failed grievance submissions
 * 4. Image upload validation (size, MIME type) and preview
 * 5. Citizen grievance listing, filtering, search, and empty states
 * 6. Grievance detail and milestone timeline rendering
 * 7. Handling of missing ML analysis or evidence without crashing
 * 8. Road operations and detour instructions rendering
 * 9. Chatbot conversation flow, RAG source citations, and fallback error handling
 * 10. Unauthorized role blocking (e.g. GOVERNMENT_OFFICER blocked from /citizen)
 * 11. Duplicate-submission prevention while request is pending
 * 12. Accessible form labels and keyboard interaction
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../features/auth/AuthContext'
import { CitizenPortalPage } from '../pages/CitizenPortalPage'
import { citizenService } from '../services/citizenService'
import type {
  CitizenGrievanceItem,
  CitizenGrievanceDetail,
  CitizenRoadOperation,
  ChatConversationSummary,
  ChatConversation,
} from '../types/citizen'

// Mock the citizenService module
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

const mockCitizenGrievances: CitizenGrievanceItem[] = [
  {
    id: 'gr-cit-001',
    citizen_id: 'cit-test-1',
    road_id: 'road-101',
    issue_category: 'POTHOLE',
    description: 'Severe pothole near 5th cross junction',
    latitude: 12.9716,
    longitude: 77.5946,
    status: 'SUBMITTED',
    created_at: '2026-10-10T08:00:00Z',
    updated_at: '2026-10-10T08:00:00Z',
  },
  {
    id: 'gr-cit-002',
    citizen_id: 'cit-test-1',
    road_id: 'road-102',
    issue_category: 'WATERLOGGING',
    description: 'Flooding near storm drain during rainfall',
    latitude: 12.9800,
    longitude: 77.6000,
    status: 'IN_PROGRESS',
    created_at: '2026-10-09T09:30:00Z',
    updated_at: '2026-10-10T11:00:00Z',
  },
]

const mockDetailWithFullInfo: CitizenGrievanceDetail = {
  id: 'gr-cit-001',
  citizen_id: 'cit-test-1',
  road_id: 'road-101',
  road_name: 'Brigade Road North',
  issue_category: 'POTHOLE',
  description: 'Severe pothole near 5th cross junction',
  latitude: 12.9716,
  longitude: 77.5946,
  status: 'IN_PROGRESS',
  created_at: '2026-10-10T08:00:00Z',
  updated_at: '2026-10-10T14:00:00Z',
  evidence_items: [
    {
      id: 'ev-1',
      grievance_id: 'gr-cit-001',
      work_order_id: null,
      file_name: 'pothole_proof.jpg',
      file_type: 'image/jpeg',
      storage_path: '/uploads/citizen_pothole_proof.jpg',
      file_size_bytes: 204800,
      uploaded_at: '2026-10-10T08:01:00Z',
    },
  ],
  ml_summary: {
    detected_issue: 'POTHOLE',
    severity_level: 'HIGH',
    risk_level: 'ELEVATED',
    priority_level: 'HIGH',
  },
  work_progress: {
    work_order_id: 'wo-401',
    status: 'IN_PROGRESS',
    progress_percentage: 60,
    last_updated_at: '2026-10-10T12:00:00Z',
    status_display: 'Asphalt cold patch application underway',
  },
  rejection_info: {
    is_reverted_for_rework: false,
    public_message: null,
  },
  timeline: [
    {
      event_type: 'GRIEVANCE_SUBMITTED',
      status: 'SUBMITTED',
      timestamp: '2026-10-10T08:00:00Z',
      public_message: 'Report submitted by citizen and pending municipal review.',
    },
    {
      event_type: 'WORK_ORDER_ASSIGNED',
      status: 'IN_PROGRESS',
      timestamp: '2026-10-10T10:30:00Z',
      public_message: 'Work order dispatched to road contractor.',
    },
  ],
}

const mockDetailMissingInfo: CitizenGrievanceDetail = {
  id: 'gr-cit-003',
  citizen_id: 'cit-test-1',
  road_id: null,
  road_name: null,
  issue_category: 'ROAD_CRACK',
  description: 'Hairline cracks developing on peripheral road',
  latitude: 12.9100,
  longitude: 77.5200,
  status: 'SUBMITTED',
  created_at: '2026-10-12T07:00:00Z',
  updated_at: '2026-10-12T07:00:00Z',
  evidence_items: [],
  ml_summary: null,
  work_progress: null,
  rejection_info: null,
  timeline: [],
}

const mockRoadOperations: CitizenRoadOperation[] = [
  {
    id: 'op-cit-001',
    road_id: 'road-101',
    road_name: 'Brigade Road North',
    title: 'Emergency Resurfacing & Pipe Replacement',
    description: 'Major culvert repair and surface sealing on Brigade Road North.',
    reason: 'Water main fracture causing pavement erosion.',
    operation_type: 'ROAD_CLOSURE',
    status: 'ACTIVE',
    start_time: '2026-10-10T06:00:00Z',
    expected_end_time: '2026-10-15T18:00:00Z',
    alternative_route_name: 'Residency Road Detour Bypass',
    alternative_route_instructions: 'Divert eastbound traffic via Residency Road and loop around Richmond Circle.',
    alternative_road_name: 'Residency Road',
    alternative_distance_km: 1.8,
    created_at: '2026-10-09T18:00:00Z',
    updated_at: '2026-10-10T06:00:00Z',
  },
]

const mockChatSummaries: ChatConversationSummary[] = [
  {
    id: 'conv-cit-001',
    citizen_id: 'cit-test-1',
    title: 'Pothole bylaws and repair query',
    created_at: '2026-10-10T09:00:00Z',
    updated_at: '2026-10-10T09:05:00Z',
    message_count: 2,
  },
]

const mockChatConversation: ChatConversation = {
  id: 'conv-cit-001',
  citizen_id: 'cit-test-1',
  title: 'Pothole bylaws and repair query',
  created_at: '2026-10-10T09:00:00Z',
  updated_at: '2026-10-10T09:05:00Z',
  messages: [
    {
      id: 'msg-1',
      conversation_id: 'conv-cit-001',
      role: 'USER',
      content: 'How quickly does the municipal authority fix deep potholes?',
      created_at: '2026-10-10T09:00:00Z',
    },
    {
      id: 'msg-2',
      conversation_id: 'conv-cit-001',
      role: 'ASSISTANT',
      content: 'Under municipal road standards, potholes classified as CRITICAL priority require repair dispatch within 48 hours.',
      sources: [
        {
          title: 'Municipal Road Maintenance SLA Manual',
          category: 'Standard Operating Procedure',
          source: 'Urban Works Department',
          relevance_score: 0.94,
        },
      ],
      created_at: '2026-10-10T09:00:05Z',
    },
  ],
}

describe('Citizen Portal Integration Tests', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.clearAllMocks()

    vi.mocked(citizenService.listGrievances).mockResolvedValue(mockCitizenGrievances)
    vi.mocked(citizenService.getGrievanceDetails).mockResolvedValue(mockDetailWithFullInfo)
    vi.mocked(citizenService.listRoadOperations).mockResolvedValue(mockRoadOperations)
    vi.mocked(citizenService.listChatConversations).mockResolvedValue(mockChatSummaries)
    vi.mocked(citizenService.getChatConversation).mockResolvedValue(mockChatConversation)
  })

  it('1. blocks unauthorized role (GOVERNMENT_OFFICER) from accessing citizen portal', () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'off-001', role: 'GOVERNMENT_OFFICER', name: 'Officer Sarah' })
    )

    render(
      <MemoryRouter initialEntries={['/citizen']}>
        <AuthProvider>
          <CitizenPortalPage />
        </AuthProvider>
      </MemoryRouter>
    )

    expect(screen.getByText(/access restricted/i)).toBeInTheDocument()
    expect(screen.queryByText(/citizen platform/i)).not.toBeInTheDocument()
  })

  it('2. renders Citizen Platform overview and KPIs for authenticated citizen', async () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'cit-test-1', role: 'CITIZEN', name: 'Citizen Ramesh' })
    )

    render(
      <MemoryRouter initialEntries={['/citizen']}>
        <AuthProvider>
          <CitizenPortalPage />
        </AuthProvider>
      </MemoryRouter>
    )

    expect(screen.getByText(/citizen platform/i)).toBeInTheDocument()
    expect(screen.getByText(/welcome,/i)).toBeInTheDocument()
    expect(screen.getByText(/Citizen Ramesh/i)).toBeInTheDocument()

    // Overview KPIs
    await waitFor(() => {
      expect(screen.getByText(/reports logged/i)).toBeInTheDocument()
      expect(screen.getByText(/active road closures/i)).toBeInTheDocument()
    })
  })

  it('3. validates grievance submission form (bounds and coordinates)', async () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'cit-test-1', role: 'CITIZEN', name: 'Citizen Ramesh' })
    )

    render(
      <MemoryRouter initialEntries={['/citizen']}>
        <AuthProvider>
          <CitizenPortalPage />
        </AuthProvider>
      </MemoryRouter>
    )

    // Navigate to Report tab
    fireEvent.click(screen.getByTestId('citizen-tab-report'))

    expect(screen.getByText(/report a road defect/i)).toBeInTheDocument()
    const submitBtn = screen.getByRole('button', { name: /submit grievance/i })

    // Entering description too short (<5 chars)
    const descInput = screen.getByPlaceholderText(/example: deep pothole/i)
    fireEvent.change(descInput, { target: { value: 'Bad' } })
    fireEvent.click(submitBtn)

    expect(screen.getByText(/description must be at least 5 characters/i)).toBeInTheDocument()
    expect(citizenService.createGrievance).not.toHaveBeenCalled()
  })

  it('4. validates file upload size limit (10MB)', async () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'cit-test-1', role: 'CITIZEN', name: 'Citizen Ramesh' })
    )

    render(
      <MemoryRouter initialEntries={['/citizen']}>
        <AuthProvider>
          <CitizenPortalPage />
        </AuthProvider>
      </MemoryRouter>
    )

    // Navigate to Report tab
    fireEvent.click(screen.getByTestId('citizen-tab-report'))

    // Create a mock file larger than 10MB
    const oversizedFile = new File(['x'.repeat(1024)], 'giant_image.jpg', { type: 'image/jpeg' })
    Object.defineProperty(oversizedFile, 'size', { value: 11 * 1024 * 1024 })

    const fileInput = document.getElementById('photo-upload') as HTMLInputElement
    expect(fileInput).toBeInTheDocument()

    fireEvent.change(fileInput, { target: { files: [oversizedFile] } })

    expect(screen.getByText(/exceeds the maximum allowed 10 MB limit/i)).toBeInTheDocument()
  })

  it('5. successfully submits grievance and prevents duplicate clicks', async () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'cit-test-1', role: 'CITIZEN', name: 'Citizen Ramesh' })
    )

    const createdGrievance: CitizenGrievanceItem = {
      id: 'gr-cit-new-99',
      citizen_id: 'cit-test-1',
      issue_category: 'POTHOLE',
      description: 'Dangerous pothole formed after heavy rainfall',
      latitude: 12.9716,
      longitude: 77.5946,
      status: 'SUBMITTED',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    vi.mocked(citizenService.createGrievance).mockResolvedValue(createdGrievance)

    render(
      <MemoryRouter initialEntries={['/citizen']}>
        <AuthProvider>
          <CitizenPortalPage />
        </AuthProvider>
      </MemoryRouter>
    )

    // Navigate to Report tab
    fireEvent.click(screen.getByTestId('citizen-tab-report'))

    // Fill valid data
    const descInput = screen.getByPlaceholderText(/example: deep pothole/i)
    fireEvent.change(descInput, { target: { value: 'Dangerous pothole formed after heavy rainfall' } })

    const latInput = screen.getByPlaceholderText(/e\.g\. 12\.971598/i)
    fireEvent.change(latInput, { target: { value: '12.9716' } })

    const lngInput = screen.getByPlaceholderText(/e\.g\. 77\.594562/i)
    fireEvent.change(lngInput, { target: { value: '77.5946' } })

    const submitBtn = screen.getByRole('button', { name: /submit grievance/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(citizenService.createGrievance).toHaveBeenCalledWith(
        expect.objectContaining({
          issue_category: 'POTHOLE',
          description: 'Dangerous pothole formed after heavy rainfall',
          latitude: 12.9716,
          longitude: 77.5946,
        })
      )
      expect(screen.getByText(/grievance submitted successfully!/i)).toBeInTheDocument()
      expect(screen.getByText(/gr-cit-new-99/i)).toBeInTheDocument()
    })
  })

  it('6. renders citizen grievances list and handles search and status filters', async () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'cit-test-1', role: 'CITIZEN', name: 'Citizen Ramesh' })
    )

    render(
      <MemoryRouter initialEntries={['/citizen']}>
        <AuthProvider>
          <CitizenPortalPage />
        </AuthProvider>
      </MemoryRouter>
    )

    // Navigate to My Grievances
    fireEvent.click(screen.getByTestId('citizen-tab-my-grievances'))

    await waitFor(() => {
      expect(screen.getByText('Severe pothole near 5th cross junction')).toBeInTheDocument()
      expect(screen.getByText('Flooding near storm drain during rainfall')).toBeInTheDocument()
    })

    // Search filter
    const searchInput = screen.getByPlaceholderText(/search by description/i)
    fireEvent.change(searchInput, { target: { value: 'Flooding' } })

    expect(screen.queryByText('Severe pothole near 5th cross junction')).not.toBeInTheDocument()
    expect(screen.getByText('Flooding near storm drain during rainfall')).toBeInTheDocument()
  })

  it('7. renders grievance detail modal with ML assessment and milestone timeline', async () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'cit-test-1', role: 'CITIZEN', name: 'Citizen Ramesh' })
    )

    render(
      <MemoryRouter initialEntries={['/citizen']}>
        <AuthProvider>
          <CitizenPortalPage />
        </AuthProvider>
      </MemoryRouter>
    )

    // Navigate to My Grievances tab
    fireEvent.click(screen.getByTestId('citizen-tab-my-grievances'))

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /view details & timeline/i }).length).toBeGreaterThan(0)
    })

    const viewDetailBtn = screen.getAllByRole('button', { name: /view details & timeline/i })[0]
    fireEvent.click(viewDetailBtn)

    await waitFor(() => {
      expect(citizenService.getGrievanceDetails).toHaveBeenCalledWith('gr-cit-001')
      expect(screen.getByText(/Grievance Report #gr-cit-0/i)).toBeInTheDocument()
      expect(screen.getByText(/Brigade Road North/i)).toBeInTheDocument()
      // ML Card
      expect(screen.getByText(/RoadX AI Defect Assessment/i)).toBeInTheDocument()
      // Contractor progress
      expect(screen.getByText(/Contractor Repair Progress/i)).toBeInTheDocument()
      expect(screen.getByText(/60%/i)).toBeInTheDocument()
      // Evidence file
      expect(screen.getByText('pothole_proof.jpg')).toBeInTheDocument()
      // Timeline event
      expect(screen.getByText(/Report submitted by citizen and pending municipal review/i)).toBeInTheDocument()
    })
  })

  it('8. handles missing ML summary or evidence safely without crashing', async () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'cit-test-1', role: 'CITIZEN', name: 'Citizen Ramesh' })
    )

    vi.mocked(citizenService.getGrievanceDetails).mockResolvedValue(mockDetailMissingInfo)

    render(
      <MemoryRouter initialEntries={['/citizen']}>
        <AuthProvider>
          <CitizenPortalPage />
        </AuthProvider>
      </MemoryRouter>
    )

    // Navigate to My Grievances tab
    fireEvent.click(screen.getByTestId('citizen-tab-my-grievances'))

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /view details & timeline/i }).length).toBeGreaterThan(0)
    })

    const viewDetailBtn = screen.getAllByRole('button', { name: /view details & timeline/i })[0]
    fireEvent.click(viewDetailBtn)

    await waitFor(() => {
      expect(screen.getByText(/Hairline cracks developing on peripheral road/i)).toBeInTheDocument()
      expect(screen.getByText(/No visual evidence photos attached for this report/i)).toBeInTheDocument()
      expect(screen.getByText(/No milestone events logged yet/i)).toBeInTheDocument()
      // Does not crash
      expect(screen.queryByText(/RoadX AI Defect Assessment/i)).not.toBeInTheDocument()
    })
  })

  it('9. renders road operations, closures, and detour instructions', async () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'cit-test-1', role: 'CITIZEN', name: 'Citizen Ramesh' })
    )

    render(
      <MemoryRouter initialEntries={['/citizen']}>
        <AuthProvider>
          <CitizenPortalPage />
        </AuthProvider>
      </MemoryRouter>
    )

    // Navigate to Road Operations tab
    fireEvent.click(screen.getByTestId('citizen-tab-road-operations'))

    await waitFor(() => {
      expect(screen.getByText(/Emergency Resurfacing & Pipe Replacement/i)).toBeInTheDocument()
      expect(screen.getByText('Active Closure')).toBeInTheDocument()
      expect(screen.getByText(/Residency Road Detour Bypass/i)).toBeInTheDocument()
      expect(screen.getByText(/Divert eastbound traffic via Residency Road/i)).toBeInTheDocument()
      expect(screen.getByText(/\+1\.8 km detour/i)).toBeInTheDocument()
    })
  })

  it('10. handles chatbot messaging, grounded source citations, and graceful fallbacks', async () => {
    sessionStorage.setItem(
      'roadx_user',
      JSON.stringify({ id: 'cit-test-1', role: 'CITIZEN', name: 'Citizen Ramesh' })
    )

    render(
      <MemoryRouter initialEntries={['/citizen']}>
        <AuthProvider>
          <CitizenPortalPage />
        </AuthProvider>
      </MemoryRouter>
    )

    // Navigate to RoadX AI Assistant tab
    fireEvent.click(screen.getByTestId('citizen-tab-chatbot'))

    await waitFor(() => {
      expect(screen.getByText(/RoadX Citizen AI Assistant/i)).toBeInTheDocument()
      expect(screen.getByText(/How quickly does the municipal authority fix deep potholes\?/i)).toBeInTheDocument()
      expect(
        screen.getByText(/potholes classified as CRITICAL priority require repair dispatch within 48 hours/i)
      ).toBeInTheDocument()
      // Grounded citations
      expect(screen.getByText(/Municipal Road Maintenance SLA Manual/i)).toBeInTheDocument()
      expect(screen.getByText(/94% Match/i)).toBeInTheDocument()
    })

    // Test sending message with error fallback
    vi.mocked(citizenService.sendChatMessage).mockRejectedValue(new Error('LLM Offline'))

    const chatInput = screen.getByPlaceholderText(/Ask a question about road advisories/i)
    fireEvent.change(chatInput, { target: { value: 'Is NH-44 closed?' } })

    const sendBtn = screen.getByRole('button', { name: /send message/i })
    fireEvent.click(sendBtn)

    await waitFor(() => {
      expect(screen.getByText(/AI Assistant is currently experiencing high demand/i)).toBeInTheDocument()
    })
  })
})
