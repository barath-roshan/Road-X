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

> **Security Note:** All `VITE_*` variables are bundled into the public client application. Never place database credentials, private API keys, or server secrets in client environment files.

### 3. Run Development Server
```bash
npm run dev
```
The application will launch at: [http://127.0.0.1:3000](http://127.0.0.1:3000)

### 4. Build for Production
```bash
npm run build
```
Generates optimized, minified production assets in `frontend/dist/`.

---

## 4. Testing & Type-Checking Commands

| Command | Action |
|---|---|
| `npm test` | Runs the Vitest test suite (`16 passed, 0 failed`) |
| `npm run typecheck` | Validates TypeScript types across the project with zero emissions |
| `npm run build` | Compiles TypeScript and builds the production bundle |

---

## 5. Authentication Architecture & Backend Contract

### Contract Discovery
The existing RoadX FastAPI backend enforces role-based access control through request headers (`api/dependencies.py:get_current_actor`):
- `X-Actor-User-ID`: The string UUID or identifier of the active user.
- `X-Actor-Role`: The governance role: `CITIZEN`, `GOVERNMENT_OFFICER`, or `CONTRACTOR`.

### Frontend Implementation
1. **Centralized Header Injection:** [`apiClient.ts`](src/services/apiClient.ts) automatically attaches `X-Actor-User-ID` and `X-Actor-Role` to all outgoing API requests from the active session.
2. **Session Storage:** Actor credentials are stored in browser `sessionStorage` (isolated to the tab session and cleared upon explicit logout). **Passwords are never stored in browser storage.**
3. **Role Enforcement:** [`ProtectedRoute.tsx`](src/app/ProtectedRoute.tsx) guards client-side routes according to `allowedRoles`. When a citizen attempts to visit `/government`, they are redirected to `/unauthorized`.
4. **Authoritative Backend Protection:** Frontend route guards are purely for UX; the FastAPI backend strictly validates `actor.require_role()` on every protected API endpoint and returns HTTP 403 `UNAUTHORIZED_ACCESS` if role boundaries are violated.

### Known Backend Contract Gaps & Security Limitations
- **Header-Based Identity in Development:** In the current phase, user identity is communicated via HTTP headers without a cryptographically signed token (JWT) or server-set `HttpOnly` session cookie.
- **No Native `/auth/login` Endpoint:** The backend lacks a dedicated password-verification endpoint. In accordance with Phase 23 specifications, no fake JWT or unprompted backend endpoints were created; authentication directly integrates with the real `get_current_actor` header contract.
- **Future Production Recommendation:** Implement secure server-set `HttpOnly`, `SameSite=Lax` session cookies with signed sessions or OAuth2/OIDC for production municipal deployments.

---

## 6. Implemented Routes

| Route | Access | Component / Description |
|---|---|---|
| `/` | Public | Home landing page with platform overview and portal switcher |
| `/login` | Public | Authentication page with role tabs and demo presets |
| `/unauthorized` | Authenticated | HTTP 403 Forbidden explanation with return links |
| `/citizen/*` | Protected (`CITIZEN`) | Citizen Platform (Phase 24 placeholder) |
| `/government/*` | Protected (`GOVERNMENT_OFFICER`) | Government Operations Dashboard (Phase 24 placeholder) |
| `/contractor/*` | Protected (`CONTRACTOR`) | Contractor Portal (Phase 24 placeholder) |
| `*` | Public | 404 Not Found fallback |
