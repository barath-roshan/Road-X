import React, { useState } from 'react'
import {
  AlertTriangle,
  MapPin,
  Camera,
  Upload,
  CheckCircle2,
  X,
  Navigation,
  FileText,
  Loader2,
} from 'lucide-react'
import { citizenService } from '../../services/citizenService'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/Card'
import { Button } from '../../components/Button'
import { Alert } from '../../components/Alert'
import type { DefectCategory, CitizenGrievanceItem, EvidenceCreatePayload } from '../../types/citizen'

const MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024 // 10MB backend limit
const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg']

interface ReportGrievanceTabProps {
  onGrievanceCreated?: (grievance: CitizenGrievanceItem) => void
  onNavigateToMyGrievances?: () => void
}

export const ReportGrievanceTab: React.FC<ReportGrievanceTabProps> = ({
  onGrievanceCreated,
  onNavigateToMyGrievances,
}) => {
  // Form fields
  const [category, setCategory] = useState<DefectCategory>('POTHOLE')
  const [description, setDescription] = useState('')
  const [latitude, setLatitude] = useState<string>('')
  const [longitude, setLongitude] = useState<string>('')
  const [roadSegmentId, setRoadSegmentId] = useState('')

  // Evidence state
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)

  // Geolocation state
  const [isLocating, setIsLocating] = useState(false)
  const [locationSuccess, setLocationSuccess] = useState<string | null>(null)
  const [locationError, setLocationError] = useState<string | null>(null)

  // Submission state
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [submittedGrievance, setSubmittedGrievance] = useState<CitizenGrievanceItem | null>(null)

  const categories: Array<{ id: DefectCategory; label: string; description: string; icon: string }> = [
    {
      id: 'POTHOLE',
      label: 'Pothole',
      description: 'Road surface crater or sunken asphalt impacting vehicular travel',
      icon: '🕳️',
    },
    {
      id: 'WATERLOGGING',
      label: 'Waterlogging',
      description: 'Standing water accumulation, blocked storm drain, or flooded pavement',
      icon: '🌊',
    },
    {
      id: 'STREETLIGHT',
      label: 'Streetlight',
      description: 'Dark roadway, broken lamp post, or damaged electrical street fixture',
      icon: '💡',
    },
    {
      id: 'ROAD_CRACK',
      label: 'Road Crack',
      description: 'Structural fissure, longitudinal crack, or alligator pavement cracking',
      icon: '⚡',
    },
  ]

  // Geolocation handler
  const handleDetectLocation = () => {
    setLocationError(null)
    setLocationSuccess(null)

    if (!('geolocation' in navigator)) {
      setLocationError('Geolocation is not supported by your browser. Please enter coordinates manually.')
      return
    }

    setIsLocating(true)
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setIsLocating(false)
        const lat = position.coords.latitude.toFixed(6)
        const lng = position.coords.longitude.toFixed(6)
        setLatitude(lat)
        setLongitude(lng)
        setLocationSuccess(`Location detected with accuracy of ±${Math.round(position.coords.accuracy)}m`)
      },
      (err) => {
        setIsLocating(false)
        switch (err.code) {
          case err.PERMISSION_DENIED:
            setLocationError('Location access was denied. Please allow location permissions or enter coordinates manually.')
            break
          case err.POSITION_UNAVAILABLE:
            setLocationError('Location information is unavailable. Please enter coordinates manually.')
            break
          case err.TIMEOUT:
            setLocationError('Location request timed out. Please try again or enter coordinates manually.')
            break
          default:
            setLocationError('Unable to detect location. Please enter coordinates manually.')
        }
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    )
  }

  // File selection & validation
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFileError(null)
    const file = e.target.files?.[0]
    if (!file) return

    // 1. MIME type validation
    if (!ALLOWED_MIME_TYPES.includes(file.type.toLowerCase())) {
      setFileError('Invalid file format. Supported formats are JPEG, PNG, and WebP.')
      e.target.value = ''
      return
    }

    // 2. File size validation (10MB limit)
    if (file.size > MAX_IMAGE_SIZE_BYTES) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(1)
      setFileError(`File size (${sizeMB} MB) exceeds the maximum allowed 10 MB limit.`)
      e.target.value = ''
      return
    }

    setSelectedFile(file)
    const objectUrl = URL.createObjectURL(file)
    setPreviewUrl(objectUrl)
  }

  const handleRemoveFile = () => {
    setSelectedFile(null)
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
      setPreviewUrl(null)
    }
    setFileError(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    // Validation
    const cleanDesc = description.trim()
    if (cleanDesc.length < 5) {
      setFormError('Description must be at least 5 characters in length.')
      return
    }
    if (cleanDesc.length > 2000) {
      setFormError('Description cannot exceed 2000 characters.')
      return
    }

    const latNum = parseFloat(latitude)
    const lngNum = parseFloat(longitude)

    if (isNaN(latNum) || latNum < -90 || latNum > 90) {
      setFormError('Please enter a valid latitude coordinate between -90.0 and +90.0.')
      return
    }

    if (isNaN(lngNum) || lngNum < -180 || lngNum > 180) {
      setFormError('Please enter a valid longitude coordinate between -180.0 and +180.0.')
      return
    }

    // Construct evidence payload if file selected
    let initialEvidence: EvidenceCreatePayload[] | undefined = undefined
    if (selectedFile) {
      // Create citizen evidence metadata matching EvidenceCreate schema
      const sanitizedName = selectedFile.name.replace(/[^a-zA-Z0-9._-]/g, '_')
      const storagePath = `/uploads/citizen_${Date.now()}_${sanitizedName}`
      initialEvidence = [
        {
          grievance_id: '', // Backend assigns the grievance ID upon creation
          file_name: selectedFile.name,
          file_type: selectedFile.type,
          storage_path: storagePath,
          file_size_bytes: selectedFile.size,
        },
      ]
    }

    setIsSubmitting(true)
    try {
      const result = await citizenService.createGrievance({
        issue_category: category,
        description: cleanDesc,
        latitude: latNum,
        longitude: lngNum,
        road_segment_id: roadSegmentId.trim() || undefined,
        evidence_items: initialEvidence,
      })

      setSubmittedGrievance(result)
      if (onGrievanceCreated) {
        onGrievanceCreated(result)
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to submit grievance. Please try again.'
      setFormError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleResetForm = () => {
    setCategory('POTHOLE')
    setDescription('')
    setLatitude('')
    setLongitude('')
    setRoadSegmentId('')
    handleRemoveFile()
    setSubmittedGrievance(null)
    setFormError(null)
    setLocationSuccess(null)
    setLocationError(null)
  }

  if (submittedGrievance) {
    return (
      <Card className="max-w-2xl mx-auto border-emerald-200 bg-emerald-50/20">
        <CardContent className="p-8 text-center space-y-6">
          <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-10 h-10" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-slate-900">Grievance Submitted Successfully!</h2>
            <p className="text-sm text-slate-600 mt-2">
              Your report has been securely registered in the municipal database with initial lifecycle status{' '}
              <span className="font-semibold text-emerald-700">SUBMITTED</span>.
            </p>
          </div>

          <div className="bg-white p-4 rounded-xl border border-emerald-100 text-left max-w-md mx-auto space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-500">Report ID:</span>
              <span className="font-mono font-medium text-slate-800 text-xs">{submittedGrievance.id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Category:</span>
              <span className="font-semibold text-slate-800">{submittedGrievance.issue_category}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Coordinates:</span>
              <span className="font-mono text-slate-700 text-xs">
                {submittedGrievance.latitude.toFixed(5)}, {submittedGrievance.longitude.toFixed(5)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Status:</span>
              <span className="px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-800">
                {submittedGrievance.status}
              </span>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
            {onNavigateToMyGrievances && (
              <Button variant="primary" onClick={onNavigateToMyGrievances}>
                View in My Grievances
              </Button>
            )}
            <Button variant="secondary" onClick={handleResetForm}>
              Report Another Defect
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2.5 rounded-lg bg-blue-50 text-blue-600">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">Report a Road Defect</h1>
            <p className="text-sm text-slate-500">
              Submit damage details, precise GPS coordinates, and photos directly to municipal road maintenance.
            </p>
          </div>
        </div>
      </div>

      {formError && (
        <Alert variant="error" title="Submission Failed" onDismiss={() => setFormError(null)}>
          {formError}
        </Alert>
      )}

      <form onSubmit={handleSubmit} noValidate className="space-y-6">
        {/* Step 1: Issue Category Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center font-bold">
                1
              </span>
              Select Defect Category
            </CardTitle>
            <CardDescription>Choose the primary defect category matching your observation.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {categories.map((cat) => (
                <button
                  type="button"
                  key={cat.id}
                  onClick={() => setCategory(cat.id)}
                  className={`p-4 rounded-xl border text-left transition-all flex flex-col justify-between ${
                    category === cat.id
                      ? 'border-blue-600 bg-blue-50/50 shadow-xs ring-1 ring-blue-600'
                      : 'border-slate-200 hover:border-slate-300 bg-white'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-xl" role="img" aria-label={cat.label}>
                      {cat.icon}
                    </span>
                    <span className="font-semibold text-slate-900 text-sm">{cat.label}</span>
                    {category === cat.id && (
                      <CheckCircle2 className="w-4 h-4 text-blue-600 ml-auto shrink-0" />
                    )}
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed">{cat.description}</p>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Step 2: Description */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center font-bold">
                2
              </span>
              Defect Description
            </CardTitle>
            <CardDescription>
              Describe the road problem, its size, approximate lane location, and immediate traffic impact (5-2000 characters).
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <textarea
                id="grievance-description"
                rows={4}
                required
                minLength={5}
                maxLength={2000}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Example: Deep pothole measuring approximately 40cm in diameter on the left lane near the bus stop. Causing sudden vehicle swerving during rush hour."
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <div className="flex justify-between items-center text-xs text-slate-500">
                <span>Natural language context assists ML severity triage</span>
                <span className={description.trim().length < 5 ? 'text-amber-600 font-medium' : 'text-slate-500'}>
                  {description.trim().length} / 2000 characters (min 5)
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Step 3: Location Coordinates */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center font-bold">
                3
              </span>
              Incident Location
            </CardTitle>
            <CardDescription>
              Provide exact GPS coordinates. You can auto-detect your current position with permission or enter coordinates manually.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
              <Button
                type="button"
                variant="secondary"
                onClick={handleDetectLocation}
                disabled={isLocating}
                className="flex items-center gap-2 shrink-0"
              >
                {isLocating ? (
                  <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                ) : (
                  <Navigation className="w-4 h-4 text-blue-600" />
                )}
                <span>{isLocating ? 'Detecting Location...' : 'Detect My Location'}</span>
              </Button>
              <span className="text-xs text-slate-500">
                Requires browser permission. We never store or transmit default fake coordinates.
              </span>
            </div>

            {locationSuccess && (
              <Alert variant="success" onDismiss={() => setLocationSuccess(null)}>
                {locationSuccess}
              </Alert>
            )}

            {locationError && (
              <Alert variant="warning" onDismiss={() => setLocationError(null)}>
                {locationError}
              </Alert>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="latitude" className="block text-xs font-semibold text-slate-700 mb-1">
                  Latitude (-90.0 to +90.0) <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <MapPin className="h-4 w-4" />
                  </div>
                  <input
                    id="latitude"
                    type="number"
                    step="any"
                    required
                    min="-90"
                    max="90"
                    value={latitude}
                    onChange={(e) => setLatitude(e.target.value)}
                    placeholder="e.g. 12.971598"
                    className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="longitude" className="block text-xs font-semibold text-slate-700 mb-1">
                  Longitude (-180.0 to +180.0) <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <MapPin className="h-4 w-4" />
                  </div>
                  <input
                    id="longitude"
                    type="number"
                    step="any"
                    required
                    min="-180"
                    max="180"
                    value={longitude}
                    onChange={(e) => setLongitude(e.target.value)}
                    placeholder="e.g. 77.594562"
                    className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>
            </div>

            <div>
              <label htmlFor="road-segment-id" className="block text-xs font-semibold text-slate-700 mb-1">
                Road Segment Identifier <span className="text-slate-400 font-normal">(Optional)</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <FileText className="h-4 w-4" />
                </div>
                <input
                  id="road-segment-id"
                  type="text"
                  value={roadSegmentId}
                  onChange={(e) => setRoadSegmentId(e.target.value)}
                  placeholder="e.g. SEG-BLR-101"
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Step 4: Photo Evidence Upload */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center font-bold">
                4
              </span>
              Photo Evidence
            </CardTitle>
            <CardDescription>
              Upload a clear photo of the road damage for ML defect detection and verification (JPEG, PNG, WebP up to 10MB).
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {fileError && (
              <Alert variant="error" onDismiss={() => setFileError(null)}>
                {fileError}
              </Alert>
            )}

            {!previewUrl ? (
              <label
                htmlFor="photo-upload"
                className="border-2 border-dashed border-slate-300 hover:border-blue-500 rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer transition-colors bg-slate-50/50 hover:bg-blue-50/20"
              >
                <div className="p-3 bg-white rounded-full shadow-xs border border-slate-200 mb-3 text-slate-500">
                  <Camera className="w-6 h-6 text-blue-600" />
                </div>
                <span className="text-sm font-semibold text-slate-800 mb-1">Click to select photo or drag here</span>
                <span className="text-xs text-slate-500">Supported formats: JPEG, PNG, WebP (Max 10 MB)</span>
                <input
                  id="photo-upload"
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/jpg"
                  onChange={handleFileChange}
                  className="sr-only"
                />
              </label>
            ) : (
              <div className="flex flex-col sm:flex-row items-center gap-4 p-4 rounded-xl border border-slate-200 bg-white">
                <img
                  src={previewUrl}
                  alt="Evidence preview"
                  className="w-32 h-24 object-cover rounded-lg border border-slate-200"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-900 truncate">{selectedFile?.name}</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Size: {selectedFile ? (selectedFile.size / (1024 * 1024)).toFixed(2) : 0} MB • Type: {selectedFile?.type}
                  </p>
                  <p className="text-xs text-emerald-600 font-medium mt-1 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Validated against municipal upload limits
                  </p>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleRemoveFile}
                  className="text-rose-600 hover:bg-rose-50"
                  aria-label="Remove photo"
                >
                  <X className="w-4 h-4 mr-1" /> Remove
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Submit Action */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <Button
            type="button"
            variant="ghost"
            onClick={handleResetForm}
            disabled={isSubmitting}
          >
            Clear Form
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={isSubmitting}
            className="min-w-[180px] flex items-center justify-center gap-2"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Registering Report...</span>
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" />
                <span>Submit Grievance</span>
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}
