# RoadX Frontend — Web Application & Authentication Foundation (Phase 23)

The shared frontend client for **RoadX**, an intelligent municipal road grievance, failure prediction, and maintenance management platform.

---

## 1. Architecture & Technology Stack

- **Framework:** React 19 + TypeScript (Strict Mode)
- **Bundler:** Vite 8
- **Routing:** React Router 7 (`react-router-dom`)
- **Styling:** Tailwind CSS v4 (`@tailwindcss/vite`) + Inter typography
- **Icons:** Lucide React (`lucide-react`)
- **Testing:** Vitest 5 + React Testing Library + `@testing-library/jest-dom` + `jsdom`
- **Node.js Requirement:** Node.js `>= 20.0.0` (Tested on Node.js `v24.13.1` on Windows x64)

---

## 2. Directory Structure

```text
frontend/
├── .env.example              # Public client environment template
├── index.html                # Application entry HTML with Inter font & meta tags
├── package.json              # Dependencies and lifecycle scripts
├── tsconfig.json             # TypeScript root project references
├── tsconfig.app.json         # Application TypeScript compiler settings
├── tsconfig.node.json        # Vite config TypeScript compiler settings
├── vite.config.ts            # Vite + Vitest + Tailwind configuration
└── src/
    ├── main.tsx              # React DOM mounting
    ├── App.tsx               # Root application with BrowserRouter & AuthProvider
    ├── index.css             # Tailwind base styles and civic tech design system
    ├── app/
    │   ├── AppRoutes.tsx     # Route tree and layout mappings
    │   └── ProtectedRoute.tsx# Role boundary enforcement and session guards
    ├── components/           # Reusable UI component library
    │   ├── Alert.tsx         # Contextual alert notifications (info, success, warning, error)
    │   ├── Badge.tsx         # Status & RoleBadge indicators
    │   ├── Button.tsx        # Accessible action buttons with loading states
    │   ├── Card.tsx          # Card container and header/body/footer components
    │   ├── EmptyState.tsx    # Empty data state illustrations and action prompts
    │   ├── Input.tsx         # Accessible form input with helperText and errors
    │   ├── LoadingSpinner.tsx# Screen-reader polite loading spinners
    │   └── index.ts          # Components barrel export
    ├── features/auth/        # Authentication domain logic
    │   ├── AuthContext.tsx   # Session management, login, logout, and role helpers
    │   └── LoginForm.tsx     # Role-aware login form with validation and demo presets
    ├── layouts/
    │   ├── AuthLayout.tsx    # Centered branding shell for login
    │   └── RootLayout.tsx    # Header, navigation tabs, user badge, and footer
    ├── pages/
    │   ├── HomePage.tsx      # Landing page routing to role-specific portals
    │   ├── LoginPage.tsx     # Authentication page
    │   ├── UnauthorizedPage.tsx # 403 Forbidden role mismatch page
    │   ├── NotFoundPage.tsx  # 404 Not Found fallback page
    │   ├── CitizenDashboardPlaceholder.tsx    # Citizen portal placeholder (Phase 24+)
    │   ├── GovernmentDashboardPlaceholder.tsx # Government dashboard placeholder (Phase 24+)
    │   └── ContractorDashboardPlaceholder.tsx # Contractor portal placeholder (Phase 24+)
    ├── services/
    │   └── apiClient.ts      # Centralized HTTP client injecting actor headers
    ├── tests/
    │   ├── setup.ts          # Vitest jest-dom setup and cleanup hooks
    │   ├── apiClient.test.ts # Header injection and error handling tests
    │   ├── auth.test.tsx     # AuthProvider and session restoration tests
    │   ├── loginForm.test.tsx# Form validation and role selector tests
    │   └── routing.test.tsx  # Role-aware protected route enforcement tests
    └── types/
        ├── api.ts            # APIErrorResponse and health check schemas
        └── auth.ts           # UserRole, AuthUser, and session types
```

---

## 3. Installation & Getting Started

### Prerequisites
- Node.js `>= 20.0.0`
- RoadX FastAPI backend service running at `http://127.0.0.1:8000`

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env.local`:
```bash
cp .env.example .env.local
```

| Variable | Default Value | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000` | Target URL for the running RoadX FastAPI backend |

> **Security Note:** All `VITE_*` variables are bundled into the public client application. Never place databas### 4. Testing & Type-Checking Commands

| Command | Action |
|---|---|
| `npm test` | Runs the full Vitest test suite (`28 passed, 0 failed`) |
| `npm run typecheck` | Validates TypeScript types across the project with zero errors |
| `npm run build` | Compiles TypeScript and builds the production bundle (`dist/`) |

---

## 5. Authentication Architecture & Backend Contract

### Contract Discovery
The existing RoadX FastAPI backend enforces role-based access control through request headers (`api/dependencies.py:get_current_actor`):
- `X-Actor-User-ID`: The string UUID or identifier of the active user.
- `X-Actor-Role`: The governance role: `CITIZEN`, `GOVERNMENT_OFFICER`, or `CONTRACTOR`.

### Frontend Implementation
1. **Centralized Header Injection:** [`apiClient.ts`](src/services/apiClient.ts) automatically attaches `X-Actor-User-ID` and `X-Actor-Role` to all outgoing API requests from the active session. Supports `get`, `post`, `put`, `patch`, `delete`, and `upload`.
2. **Session Storage:** Actor credentials are stored in browser `sessionStorage` (isolated to the tab session and cleared upon explicit logout). **Passwords are never stored in browser storage.**
3. **Role Enforcement:** [`ProtectedRoute.tsx`](src/app/ProtectedRoute.tsx) guards client-side routes according to `allowedRoles`. When a citizen attempts to visit `/government`, they are redirected to `/unauthorized`.
4. **Authoritative Backend Protection:** Frontend route guards are purely for UX; the FastAPI backend strictly validates `actor.require_role()` on every protected API endpoint and returns HTTP 403 `UNAUTHORIZED_ACCESS` if role boundaries are violated.

---

## 6. Phase 24 — Government Officer Dashboard

The Government Officer Dashboard provides authorized municipal personnel with administrative control over the grievance lifecycle, ML predictive insights, contractor dispatch, and completion sign-off:

### Dashboard Modules & Sub-Tabs

1. **Executive Overview (`/government?tab=overview`):**
   - Integrates with `GET /api/v1/government/dashboard/overview`.
   - Real-time aggregate KPI cards: Total Grievances, Pending Officer Reviews, In-Progress Work Orders, Active Contractors.
   - Pending Verifications Callout: Actionable banner directing officers to pending work order reviews.
   - Detailed breakdowns: Grievance lifecycle stage distribution, ML Decision Support priority tiers (Critical, High, Medium, Low), Damage severity distribution, and Work order lifecycle counts.

2. **Grievance Management (`/government?tab=grievances`):**
   - Integrates with `GET /api/v1/government/dashboard/grievances`.
   - Comprehensive filter toolbar: Search (keywords across description and road name), lifecycle status, category, ML priority, and ML damage severity.
   - Grievance Case Inspection Modal (`GET /api/v1/government/dashboard/grievances/{id}`):
     - Complete citizen report metadata and road segment geo-coordinates.
     - Visual evidence viewer displaying attached photographs and file metadata.
     - ML Decision Support Card: Failure risk probability, detected damage confidence, damage severity rating, estimated time-to-failure (days), and ML justification rationale reasons.
     - Chronological workflow audit timeline (`timeline`).
     - Review Decision Form: Submit `ACCEPT` (transitions to `UNDER_REVIEW`) or `REJECT` (requires mandatory rejection reason).
     - Work Order Commissioning Form: Specify title, engineering instructions, priority tier, and assign a contractor from the municipal contractor registry.

3. **Maintenance Priority Queue (`/government?tab=priority-queue`):**
   - Integrates with `GET /api/v1/government/dashboard/priority-queue`.
   - Ranked queue sorted by the Phase 8 ML Maintenance Priority score (0–100).
   - Filter by minimum priority tier (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
   - Displays priority score badge, road segment, damage category, failure risk, estimated days remaining, and machine learning rationale reason tags.
   - Quick action to inspect case and dispatch repairs directly.

4. **Work Order Monitoring (`/government?tab=work-orders`):**
   - Integrates with `GET /api/v1/government/dashboard/work-orders`.
   - Filter by work order status (`OPEN`, `ASSIGNED`, `IN_PROGRESS`, `PENDING_VERIFICATION`, `COMPLETED`, `CANCELLED`) and priority.
   - Displays repair title, road segment, assigned contractor name, priority pill, and progress percentage bars (0–100%).

5. **Completion Verification Queue (`/government?tab=verifications`):**
   - Integrates with `GET /api/v1/government/dashboard/verification-queue` and `POST /api/v1/government/work-orders/{id}/verify`.
   - **Exclusive Resolution Authority:** Enforces the governance rule that only a government officer `APPROVE` decision can officially transition a citizen grievance to `RESOLVED` and mark a work order `COMPLETED`.
   - Displays submitted completion evidence, contractor completion notes, and submission timestamps.
   - Sign-off Actions:
     - **Approve Completion:** Officially closes the work order and resolves the grievance.
     - **Reject & Request Rework:** Requires officer notes/rework instructions and reverts work order and grievance back to `IN_PROGRESS`.

6. **Contractor Monitoring (`/government?tab=contractors`):**
   - Integrates with `GET /api/v1/government/dashboard/contractors`.
   - Read-only summary cards and audit table showing contractor contact details, active jobs, pending verifications, completed jobs, and average progress percentage across assignments.

7. **Road Operations & Closures (`/government?tab=road-operations`):**
   - Integrates with `GET /api/v1/government/road-operations`, `POST /api/v1/government/road-operations`, and lifecycle transition endpoints (`activate`, `complete`, `cancel`).
   - Filter by status (`PLANNED`, `ACTIVE`, `COMPLETED`, `CANCELLED`) and operation type (`ROAD_CLOSURE`, `LANE_RESTRICTION`, `MAINTENANCE_WORK`, `DETOUR`, `HAZARD_BLOCK`).
   - Modal to publish road operations with start/end schedules, detour bypass route names, and traffic instructions.
   - Officer action controls: Activate closure (`PLANNED` → `ACTIVE`), Mark completed (`ACTIVE` → `COMPLETED`), or Cancel operation.

---

## 7. Phase 25 — Citizen Portal & Grievance Tracking

The Citizen Portal enables civic users to register road defects, attach visual evidence, track repairs across chronological milestones, view municipal traffic advisories and detours, and consult the RoadX Conversational RAG Assistant.

### Citizen Modules & Sub-Tabs

1. **Home & Overview (`/citizen?tab=overview`):**
   - KPI metrics: Reports Logged, In Progress, Resolved Reports, and Active Road Advisories.
   - Quick Action links to Report Problem, Track Grievances, and Ask AI Assistant.
   - Recent Reports summary feed and Active Road Closures preview cards.

2. **Report a Road Defect (`/citizen?tab=report`):**
   - Validated submission form integrating `POST /api/v1/citizen/grievances`.
   - Supported defect categories: `POTHOLE`, `WATERLOGGING`, `STREETLIGHT`, `ROAD_CRACK`.
   - Description field: 5 to 2000 characters with live character counter.
   - Incident Location:
     - Real browser geolocation detection via `navigator.geolocation.getCurrentPosition` (with explicit permission and accuracy metrics).
     - Manual latitude (-90.0 to +90.0) and longitude (-180.0 to +180.0) coordinates input.
     - Optional road segment identifier.
   - Visual Evidence Upload:
     - Supports JPEG, PNG, and WebP up to the backend limit of 10 MB.
     - Thumbnail preview, file metadata extraction, and removal control.
     - Initial `evidence_items` metadata payload attached to submission.
   - Double-submission prevention and confirmed submission success card.

3. **My Grievances (`/citizen?tab=my-grievances`):**
   - Integrates with `GET /api/v1/citizen/grievances`.
   - Citizen-scoped data retrieval (strictly enforces `citizen_id == actor.user_id`).
   - Search bar across descriptions, categories, and report IDs.
   - Filter dropdowns by status (`SUBMITTED`, `UNDER_REVIEW`, `IN_PROGRESS`, `PENDING_VERIFICATION`, `RESOLVED`, `REJECTED`) and defect category.
   - Empty state illustration with quick action button to report a defect.

4. **Grievance Details & Milestone Timeline:**
   - Modal view integrating `GET /api/v1/citizen/grievances/{id}`.
   - Complete report summary, road name, and GPS coordinates.
   - Attached evidence gallery and inline additional photo attachment (`POST /api/v1/citizen/grievances/{id}/evidence`).
   - Citizen-safe ML Decision Support Summary: detected issue, severity tier, road risk level, and maintenance priority.
   - Contractor Repair Progress: work order ID, status display, visual progress bar (0–100%), and last update timestamp.
   - Municipal Audit Rework Notice: Displays public rework message if an officer reverts a work order for contractor correction.
   - Chronological Milestone History: Event types, timestamps, and citizen-friendly status messages.

5. **Road Operations & Detours (`/citizen?tab=road-operations`):**
   - Read-only public traffic advisory feed integrating `GET /api/v1/citizen/road-operations`.
   - Filter by operational status (`ACTIVE`, `PLANNED`, `ALL`, `COMPLETED`) and type (`ROAD_CLOSURE`, `DETOUR`, `LANE_RESTRICTION`, `HAZARD_BLOCK`).
   - Detailed closure title, description, reason, start schedule, and expected end time.
   - Recommended Detour Routes: Alternative route title, instructions, diverting road name, and extra travel distance (+km).

6. **RoadX Citizen AI Assistant (`/citizen?tab=chatbot`):**
   - Grounded RAG assistant integrating `POST /api/v1/citizen/chat/conversations`, `GET /api/v1/citizen/chat/conversations`, and `POST /api/v1/citizen/chat/conversations/{id}/messages`.
   - Session management: Sidebar list of citizen's past chat sessions with new conversation creation.
   - Suggested prompt chips for quick inquiries.
   - Safe text rendering preventing any script or HTML execution.
   - Grounded RAG Source Citations: Expandable attribution cards with source title, category, authority, and similarity score.
   - Graceful offline fallback message if the LLM provider or vector RAG pipeline is temporarily unreachable.

---

## 8. Implemented Routes

| Route | Access | Component / Description |
|---|---|---|
| `/` | Public | Home landing page with platform overview and portal switcher |
| `/login` | Public | Authentication page with role tabs and demo presets |
| `/unauthorized` | Authenticated | HTTP 403 Forbidden explanation with return links |
| `/citizen/*` | Protected (`CITIZEN`) | Citizen Platform & Grievance Tracking (Phase 25 full implementation) |
| `/government/*` | Protected (`GOVERNMENT_OFFICER`) | Government Officer Portal (Phase 24 full implementation) |
| `/contractor/*` | Protected (`CONTRACTOR`) | Contractor Portal (Phase 26 placeholder) |
| `*` | Public | 404 Not Found fallback |

---

## 9. Security Notice: Identity & Header-Based Authentication

**Development Architecture Prerequisite:**
The development environment uses header-based actor context:
- `X-Actor-User-ID`: Client-provided user identifier
- `X-Actor-Role`: Client-provided role (`CITIZEN`, `GOVERNMENT_OFFICER`, `CONTRACTOR`)

**Vulnerability Notice:**
Client-controlled HTTP headers alone do not constitute cryptographically secure authentication in production. While the backend strictly enforces ownership boundaries (e.g., verifying `grievance.citizen_id == actor.user_id`), any client can set arbitrary header values. For production deployment, header injection must be superseded by signed JWT bearer tokens or server-managed secure session cookies.

