import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { RootLayout } from '../layouts/RootLayout'
import { AuthLayout } from '../layouts/AuthLayout'
import { ProtectedRoute } from './ProtectedRoute'
import { HomePage } from '../pages/HomePage'
import { LoginPage } from '../pages/LoginPage'
import { UnauthorizedPage } from '../pages/UnauthorizedPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { CitizenDashboardPlaceholder } from '../pages/CitizenDashboardPlaceholder'
import { GovernmentDashboardPlaceholder } from '../pages/GovernmentDashboardPlaceholder'
import { ContractorDashboardPlaceholder } from '../pages/ContractorDashboardPlaceholder'

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
          <Route path="/citizen/*" element={<CitizenDashboardPlaceholder />} />
        </Route>

        {/* Government Officer Dashboard Protected Route */}
        <Route element={<ProtectedRoute allowedRoles={['GOVERNMENT_OFFICER']} />}>
          <Route path="/government/*" element={<GovernmentDashboardPlaceholder />} />
        </Route>

        {/* Contractor Portal Protected Route */}
        <Route element={<ProtectedRoute allowedRoles={['CONTRACTOR']} />}>
          <Route path="/contractor/*" element={<ContractorDashboardPlaceholder />} />
        </Route>

        {/* 404 Fallback Catch-All */}
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
