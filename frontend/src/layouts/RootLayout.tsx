import React from 'react'
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../features/auth/AuthContext'
import { RoleBadge } from '../components/Badge'
import { Button } from '../components/Button'
import { Activity, LogOut, Compass, Shield, HardHat, User, CheckCircle2 } from 'lucide-react'

export const RootLayout: React.FC = () => {
  const { user, isAuthenticated, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const roleNavItems = [
    {
      role: 'CITIZEN',
      label: 'Citizen Portal',
      to: '/citizen',
      icon: <User className="h-4 w-4 mr-1.5" />,
    },
    {
      role: 'GOVERNMENT_OFFICER',
      label: 'Government Dashboard',
      to: '/government',
      icon: <Shield className="h-4 w-4 mr-1.5" />,
    },
    {
      role: 'CONTRACTOR',
      label: 'Contractor Portal',
      to: '/contractor',
      icon: <HardHat className="h-4 w-4 mr-1.5" />,
    },
  ]

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      {/* Top Header / Navigation */}
      <header className="sticky top-0 z-40 bg-white border-b border-slate-200/90 shadow-2xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Brand Logo & Title */}
            <div className="flex items-center space-x-3">
              <Link to="/" className="flex items-center space-x-2.5 group">
                <div className="h-9 w-9 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-xs group-hover:bg-indigo-700 transition-colors">
                  <Compass className="h-5 w-5" />
                </div>
                <div>
                  <span className="text-lg font-bold tracking-tight text-slate-900 flex items-center gap-1.5">
                    Road<span className="text-indigo-600">X</span>
                  </span>
                  <span className="hidden sm:block text-[11px] text-slate-400 font-medium uppercase tracking-wider">
                    Road Grievance & ML Platform
                  </span>
                </div>
              </Link>

              {/* Navigation Tabs based on Role */}
              {isAuthenticated && user && (
                <nav className="hidden md:flex items-center ml-8 space-x-1" aria-label="Main Navigation">
                  {roleNavItems
                    .filter((item) => item.role === user.role)
                    .map((item) => {
                      const isActive = location.pathname.startsWith(item.to)
                      return (
                        <Link
                          key={item.to}
                          to={item.to}
                          className={`flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                            isActive
                              ? 'bg-indigo-50 text-indigo-700 font-semibold'
                              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                          }`}
                        >
                          {item.icon}
                          {item.label}
                        </Link>
                      )
                    })}
                </nav>
              )}
            </div>

            {/* Right Side Actor Info & Controls */}
            <div className="flex items-center space-x-3">
              {isAuthenticated && user ? (
                <>
                  <div className="hidden sm:flex flex-col items-end text-right">
                    <span className="text-xs font-semibold text-slate-800">{user.name || user.id}</span>
                    <span className="text-[11px] text-slate-400 font-mono">ID: {user.id}</span>
                  </div>
                  <RoleBadge role={user.role} />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleLogout}
                    className="flex items-center gap-1.5 text-slate-600 hover:text-rose-600 hover:border-rose-200"
                    aria-label="Sign out"
                  >
                    <LogOut className="h-3.5 w-3.5" />
                    <span className="hidden sm:inline">Sign Out</span>
                  </Button>
                </>
              ) : (
                <Link to="/login">
                  <Button size="sm">Sign In</Button>
                </Link>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-slate-700">RoadX</span>
            <span>&bull;</span>
            <span>Municipal Infrastructure & Failure Prediction</span>
            <span>&bull;</span>
            <span className="flex items-center gap-1 text-emerald-600 font-medium">
              <CheckCircle2 className="h-3.5 w-3.5" /> API Connected
            </span>
          </div>
          <div className="flex items-center space-x-4">
            <a
              href="http://127.0.0.1:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo-600 hover:text-indigo-800 flex items-center gap-1 font-medium"
            >
              <Activity className="h-3.5 w-3.5" /> Backend Swagger Docs
            </a>
            <span>&bull;</span>
            <span>Phase 23 Foundation</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
