import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { RootLayout } from '../layouts/RootLayout'
import { AuthLayout } from '../layouts/AuthLayout'
import { ProtectedRoute } from './ProtectedRoute'
import { HomePage } from '../pages/HomePage'
import { LoginPage } from '../pages/LoginPage'
import { UnauthorizedPage } from '../pages/UnauthorizedPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { CitizenPortalPage } from '../pages/CitizenPortalPage'
import { GovernmentDashboardPage } from '../pages/GovernmentDashboardPage'
import { ContractorDashboardPage } from '../pages/ContractorDashboardPage'

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Standalone Authentication Layout */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
      </Route>

      {/* Main Application Shell Layout */}
      <Route element={<RootLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/unauthorized" element={<UnauthorizedPage />} />

        {/* Citizen Portal Protected Route */}
        <Route element={<ProtectedRoute allowedRoles={['CITIZEN']} />}>
          <Route path="/citizen/*" element={<CitizenPortalPage />} />
        </Route>

        {/* Government Officer Dashboard Protected Route */}
        <Route element={<ProtectedRoute allowedRoles={['GOVERNMENT_OFFICER']} />}>
          <Route path="/government/*" element={<GovernmentDashboardPage />} />
        </Route>

        {/* Contractor Portal Protected Route */}
        <Route element={<ProtectedRoute allowedRoles={['CONTRACTOR']} />}>
          <Route path="/contractor/*" element={<ContractorDashboardPage />} />
        </Route>

        {/* 404 Fallback Catch-All */}
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
