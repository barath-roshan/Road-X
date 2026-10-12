import React from 'react'
import { Outlet, Link } from 'react-router-dom'
import { Compass } from 'lucide-react'

export const AuthLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <Link to="/" className="inline-flex items-center space-x-2.5 mb-2">
          <div className="h-10 w-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-md">
            <Compass className="h-6 w-6" />
          </div>
          <span className="text-2xl font-bold tracking-tight text-slate-900">
            Road<span className="text-indigo-600">X</span>
          </span>
        </Link>
        <p className="text-sm text-slate-500 font-medium">
          Intelligent Road Grievance & Maintenance Management
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <Outlet />
      </div>

      <div className="mt-8 text-center text-xs text-slate-400">
        <p>Municipal Public Works & Infrastructure Administration</p>
      </div>
    </div>
  )
}
