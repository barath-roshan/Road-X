import React from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../features/auth/AuthContext'
import { Button, Card, CardContent } from '../components'
import { Compass, Shield, HardHat, User, ArrowRight, Activity } from 'lucide-react'

export const HomePage: React.FC = () => {
  const { user, isAuthenticated } = useAuth()

  // Redirect authenticated actors directly to their respective portal
  if (isAuthenticated && user) {
    if (user.role === 'GOVERNMENT_OFFICER') {
      return <Navigate to="/government" replace />
    }
    if (user.role === 'CONTRACTOR') {
      return <Navigate to="/contractor" replace />
    }
    return <Navigate to="/citizen" replace />
  }

  return (
    <div className="py-10 max-w-4xl mx-auto space-y-12">
      {/* Hero Section */}
      <div className="text-center space-y-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-semibold">
          <Activity className="h-3.5 w-3.5" />
          <span>Municipal Road Intelligence & AI Risk Engine</span>
        </div>
        <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight sm:text-5xl">
          Intelligent Road Grievance & Maintenance Management
        </h1>
        <p className="text-lg text-slate-600 max-w-2xl mx-auto leading-relaxed">
          RoadX coordinates municipal officers, repair contractors, and citizens using machine learning to predict pavement failures, prioritize urgent road repairs, and track verified completion.
        </p>
        <div className="pt-2">
          <Link to="/login">
            <Button size="lg" className="flex items-center gap-2 mx-auto">
              <span>Sign In to Your Portal</span>
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </div>

      {/* Role Portal Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card hoverable className="border-slate-200">
          <CardContent className="p-6 space-y-3">
            <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
              <User className="h-5 w-5" />
            </div>
            <h3 className="font-bold text-slate-900">Citizen Platform</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Report potholes and damaged pavement, track live repair statuses, and query the municipal AI chatbot.
            </p>
            <Link to="/login" className="inline-block pt-2 text-xs font-semibold text-indigo-600 hover:text-indigo-800">
              Sign In as Citizen &rarr;
            </Link>
          </CardContent>
        </Card>

        <Card hoverable className="border-slate-200">
          <CardContent className="p-6 space-y-3">
            <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
              <Shield className="h-5 w-5" />
            </div>
            <h3 className="font-bold text-slate-900">Government Dashboard</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Analyze AI road risk predictions, evaluate citizen grievances, issue contractor work orders, and verify repairs.
            </p>
            <Link to="/login" className="inline-block pt-2 text-xs font-semibold text-indigo-600 hover:text-indigo-800">
              Sign In as Officer &rarr;
            </Link>
          </CardContent>
        </Card>

        <Card hoverable className="border-slate-200">
          <CardContent className="p-6 space-y-3">
            <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
              <HardHat className="h-5 w-5" />
            </div>
            <h3 className="font-bold text-slate-900">Contractor Portal</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Manage assigned maintenance work orders, record work progress, and submit photo evidence for verification.
            </p>
            <Link to="/login" className="inline-block pt-2 text-xs font-semibold text-indigo-600 hover:text-indigo-800">
              Sign In as Contractor &rarr;
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Platform Architecture Note */}
      <div className="p-5 bg-white rounded-xl border border-slate-200/80 flex items-start gap-4">
        <div className="p-2.5 rounded-lg bg-indigo-50 text-indigo-600 shrink-0">
          <Compass className="h-6 w-6" />
        </div>
        <div className="text-xs text-slate-600 leading-relaxed space-y-1">
          <div className="font-bold text-slate-900 text-sm">Phase 23 Shared Foundation</div>
          <p>
            This frontend foundation establishes centralized API communications with the FastAPI service (`http://127.0.0.1:8000`), header-based actor identity routing, and responsive civic UI components.
          </p>
        </div>
      </div>
    </div>
  )
}
