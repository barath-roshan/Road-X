import React, { useEffect, useState } from 'react'
import {
  RefreshCw,
  Plus,
  Play,
  CheckCircle2,
  XCircle,
  MapPin,
  Compass,
} from 'lucide-react'
import { Card, CardContent } from '../../components/Card'
import { Button } from '../../components/Button'
import { Input } from '../../components/Input'
import { Badge } from '../../components/Badge'
import { Alert } from '../../components/Alert'
import { Modal } from '../../components/Modal'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { EmptyState } from '../../components/EmptyState'
import { governmentService } from '../../services/governmentService'
import type { RoadOperationFilterParams } from '../../services/governmentService'
import type {
  GovernmentRoadOperation,
  RoadOperationStatus,
  RoadOperationType,
  RoadOperationCreatePayload,
} from '../../types/government'

export const GovernmentRoadOperationsTab: React.FC = () => {
  const [operations, setOperations] = useState<GovernmentRoadOperation[]>([])
  const [statusFilter, setStatusFilter] = useState<RoadOperationStatus | ''>('')
  const [typeFilter, setTypeFilter] = useState<RoadOperationType | ''>('')
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)

  // Create Modal State
  const [isCreateOpen, setIsCreateOpen] = useState<boolean>(false)
  const [isSubmittingCreate, setIsSubmittingCreate] = useState<boolean>(false)
  const [createForm, setCreateForm] = useState<{
    title: string
    description: string
    reason: string
    operation_type: RoadOperationType
    start_time: string
    expected_end_time: string
    alternative_route_name: string
    alternative_route_instructions: string
  }>({
    title: '',
    description: '',
    reason: '',
    operation_type: 'ROAD_CLOSURE',
    start_time: new Date().toISOString().slice(0, 16),
    expected_end_time: new Date(Date.now() + 86400000).toISOString().slice(0, 16),
    alternative_route_name: '',
    alternative_route_instructions: '',
  })

  // Action State (Activate, Complete, Cancel)
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null)

  const fetchOperations = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const params: RoadOperationFilterParams = {
        status: statusFilter || undefined,
        operation_type: typeFilter || undefined,
      }
      const data = await governmentService.listRoadOperations(params)
      setOperations(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch road operations.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchOperations()
  }, [statusFilter, typeFilter])

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!createForm.title.trim() || !createForm.description.trim() || !createForm.reason.trim()) {
      setError('Title, description, and closure reason are required.')
      return
    }

    if (new Date(createForm.expected_end_time) <= new Date(createForm.start_time)) {
      setError('Expected completion time must be strictly after the start time.')
      return
    }

    setIsSubmittingCreate(true)
    setError(null)
    setActionSuccess(null)

    try {
      const payload: RoadOperationCreatePayload = {
        title: createForm.title.trim(),
        description: createForm.description.trim(),
        reason: createForm.reason.trim(),
        operation_type: createForm.operation_type,
        start_time: new Date(createForm.start_time).toISOString(),
        expected_end_time: new Date(createForm.expected_end_time).toISOString(),
        alternative_route_name: createForm.alternative_route_name.trim() || undefined,
        alternative_route_instructions: createForm.alternative_route_instructions.trim() || undefined,
      }

      await governmentService.createRoadOperation(payload)
      setActionSuccess('Road operation published successfully!')
      setIsCreateOpen(false)
      setCreateForm({
        title: '',
        description: '',
        reason: '',
        operation_type: 'ROAD_CLOSURE',
        start_time: new Date().toISOString().slice(0, 16),
        expected_end_time: new Date(Date.now() + 86400000).toISOString().slice(0, 16),
        alternative_route_name: '',
        alternative_route_instructions: '',
      })
      await fetchOperations()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create road operation.')
    } finally {
      setIsSubmittingCreate(false)
    }
  }

  const handleActivate = async (id: string) => {
    setActionLoadingId(id)
    setError(null)
    setActionSuccess(null)
    try {
      await governmentService.activateRoadOperation(id, 'Activated by municipal officer.')
      setActionSuccess('Road operation activated successfully.')
      await fetchOperations()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to activate road operation.')
    } finally {
      setActionLoadingId(null)
    }
  }

  const handleComplete = async (id: string) => {
    setActionLoadingId(id)
    setError(null)
    setActionSuccess(null)
    try {
      await governmentService.completeRoadOperation(id, 'Completed by municipal officer.')
      setActionSuccess('Road operation completed and closed successfully.')
      await fetchOperations()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to complete road operation.')
    } finally {
      setActionLoadingId(null)
    }
  }

  const handleCancel = async (id: string) => {
    setActionLoadingId(id)
    setError(null)
    setActionSuccess(null)
    try {
      await governmentService.cancelRoadOperation(id, 'Cancelled by municipal officer.')
      setActionSuccess('Road operation cancelled.')
      await fetchOperations()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to cancel road operation.')
    } finally {
      setActionLoadingId(null)
    }
  }

  const getStatusBadge = (st: RoadOperationStatus): 'default' | 'officer' | 'warning' | 'danger' | 'success' => {
    switch (st) {
      case 'ACTIVE':
        return 'danger'
      case 'PLANNED':
        return 'officer'
      case 'COMPLETED':
        return 'success'
      case 'CANCELLED':
        return 'default'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            Road Operations & Closures
          </h2>
          <p className="text-xs text-slate-500">
            Publish and manage official municipal road closures, lane restrictions, detours, and emergency blocks.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            size="sm"
            onClick={() => setIsCreateOpen(true)}
            className="bg-indigo-600 hover:bg-indigo-700 text-white flex items-center gap-1.5"
          >
            <Plus className="h-4 w-4" />
            Publish Operation
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchOperations}
            className="flex items-center gap-1.5 text-slate-600"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </Button>
        </div>
      </div>

      {actionSuccess && (
        <Alert
          variant="success"
          title="Operation Updated"
          onDismiss={() => setActionSuccess(null)}
        >
          {actionSuccess}
        </Alert>
      )}

      {error && !isCreateOpen && (
        <Alert variant="error" title="Road Operation Error" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Filter Bar */}
      <Card className="shadow-2xs">
        <CardContent className="p-4 flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-500">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as RoadOperationStatus | '')}
              className="rounded-md border border-slate-200 p-1.5 bg-white text-slate-700"
            >
              <option value="">All Statuses</option>
              <option value="PLANNED">PLANNED</option>
              <option value="ACTIVE">ACTIVE</option>
              <option value="COMPLETED">COMPLETED</option>
              <option value="CANCELLED">CANCELLED</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-500">Type:</span>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value as RoadOperationType | '')}
              className="rounded-md border border-slate-200 p-1.5 bg-white text-slate-700"
            >
              <option value="">All Types</option>
              <option value="ROAD_CLOSURE">ROAD_CLOSURE</option>
              <option value="LANE_RESTRICTION">LANE_RESTRICTION</option>
              <option value="MAINTENANCE_WORK">MAINTENANCE_WORK</option>
              <option value="DETOUR">DETOUR</option>
              <option value="HAZARD_BLOCK">HAZARD_BLOCK</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Content */}
      {isLoading ? (
        <div className="py-16 flex justify-center">
          <LoadingSpinner size="lg" message="Loading road operations..." />
        </div>
      ) : operations.length === 0 ? (
        <EmptyState
          title="No Road Operations Found"
          description="There are currently no active or planned road closures matching the filters."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {operations.map((op) => (
            <Card key={op.id} className="hover:border-slate-300 transition-all shadow-2xs">
              <CardContent className="p-5 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <Badge variant={getStatusBadge(op.status)}>{op.status}</Badge>
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                        {op.operation_type.replace('_', ' ')}
                      </span>
                    </div>
                    <h3 className="text-base font-bold text-slate-900 mt-1.5">{op.title}</h3>
                    <p className="text-xs text-slate-600 mt-0.5">{op.description}</p>
                    <p className="text-xs text-slate-500 italic mt-0.5">Reason: {op.reason}</p>
                  </div>

                  <div className="text-xs text-slate-500 space-y-1 sm:text-right shrink-0">
                    {op.road_name && (
                      <div className="flex sm:justify-end items-center gap-1 font-medium text-slate-800">
                        <MapPin className="h-3.5 w-3.5 text-slate-400" />
                        {op.road_name}
                      </div>
                    )}
                    <div className="text-[11px] text-slate-400">
                      {new Date(op.start_time).toLocaleDateString()} — {new Date(op.expected_end_time).toLocaleDateString()}
                    </div>
                  </div>
                </div>

                {/* Detour Information */}
                {op.alternative_route_instructions && (
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs flex items-start gap-2 text-slate-700">
                    <Compass className="h-4 w-4 text-indigo-600 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold text-slate-800">
                        Detour: {op.alternative_route_name || 'Alternative Route'}
                      </span>
                      <p className="text-slate-600 mt-0.5">{op.alternative_route_instructions}</p>
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                {(op.status === 'PLANNED' || op.status === 'ACTIVE') && (
                  <div className="pt-2 border-t border-slate-100 flex items-center justify-end gap-2">
                    {op.status === 'PLANNED' && (
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={actionLoadingId === op.id}
                        onClick={() => handleActivate(op.id)}
                        className="text-emerald-700 border-emerald-300 hover:bg-emerald-50 text-xs"
                      >
                        <Play className="h-3.5 w-3.5 mr-1" />
                        Activate Closure
                      </Button>
                    )}

                    {op.status === 'ACTIVE' && (
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={actionLoadingId === op.id}
                        onClick={() => handleComplete(op.id)}
                        className="text-indigo-700 border-indigo-300 hover:bg-indigo-50 text-xs"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                        Mark Completed
                      </Button>
                    )}

                    <Button
                      size="sm"
                      variant="outline"
                      disabled={actionLoadingId === op.id}
                      onClick={() => handleCancel(op.id)}
                      className="text-rose-600 border-rose-200 hover:bg-rose-50 text-xs"
                    >
                      <XCircle className="h-3.5 w-3.5 mr-1" />
                      Cancel
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Publish Road Operation Modal */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => !isSubmittingCreate && setIsCreateOpen(false)}
        title="Publish Municipal Road Operation"
        description="Notify civic agencies and update municipal detour networks."
        maxWidth="lg"
      >
        <form onSubmit={handleCreateSubmit} className="space-y-4">
          {error && (
            <Alert variant="error" title="Validation Error" onDismiss={() => setError(null)}>
              {error}
            </Alert>
          )}

          <Input
            label="Operation Title"
            value={createForm.title}
            onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
            placeholder="e.g. Ring Road Section 4 Resurfacing Closure"
            required
          />

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Operation Classification
            </label>
            <select
              value={createForm.operation_type}
              onChange={(e) =>
                setCreateForm({
                  ...createForm,
                  operation_type: e.target.value as RoadOperationType,
                })
              }
              className="w-full rounded-lg border border-slate-300 p-2 text-xs bg-white text-slate-900 focus:ring-2 focus:ring-indigo-500 outline-none"
            >
              <option value="ROAD_CLOSURE">ROAD_CLOSURE</option>
              <option value="LANE_RESTRICTION">LANE_RESTRICTION</option>
              <option value="MAINTENANCE_WORK">MAINTENANCE_WORK</option>
              <option value="DETOUR">DETOUR</option>
              <option value="HAZARD_BLOCK">HAZARD_BLOCK</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Operational Scope & Description
            </label>
            <textarea
              rows={2}
              value={createForm.description}
              onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
              placeholder="Detailed description of road closure boundaries and machinery on site..."
              className="w-full rounded-lg border border-slate-300 p-2.5 text-xs text-slate-900 focus:ring-2 focus:ring-indigo-500 outline-none"
              required
            />
          </div>

          <Input
            label="Closure Reason"
            value={createForm.reason}
            onChange={(e) => setCreateForm({ ...createForm, reason: e.target.value })}
            placeholder="e.g. Emergency pothole filling & asphalt resurfacing"
            required
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              type="datetime-local"
              label="Start Time"
              value={createForm.start_time}
              onChange={(e) => setCreateForm({ ...createForm, start_time: e.target.value })}
              required
            />
            <Input
              type="datetime-local"
              label="Expected End Time"
              value={createForm.expected_end_time}
              onChange={(e) => setCreateForm({ ...createForm, expected_end_time: e.target.value })}
              required
            />
          </div>

          <div className="pt-2 border-t border-slate-200 space-y-2">
            <h5 className="text-xs font-bold text-slate-700">Alternative Route / Detour (Optional)</h5>
            <Input
              label="Detour Route Name"
              value={createForm.alternative_route_name}
              onChange={(e) =>
                setCreateForm({ ...createForm, alternative_route_name: e.target.value })
              }
              placeholder="e.g. 5th Main Parallel Bypass"
            />
            <textarea
              rows={2}
              value={createForm.alternative_route_instructions}
              onChange={(e) =>
                setCreateForm({ ...createForm, alternative_route_instructions: e.target.value })
              }
              placeholder="Detour instructions: Divert via 80ft road through junction 2..."
              className="w-full rounded-lg border border-slate-300 p-2.5 text-xs text-slate-900 focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>

          <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-200">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={isSubmittingCreate}
              onClick={() => setIsCreateOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isSubmittingCreate}
              className="bg-indigo-600 hover:bg-indigo-700 text-white"
            >
              {isSubmittingCreate ? <LoadingSpinner size="sm" /> : 'Confirm & Publish'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
