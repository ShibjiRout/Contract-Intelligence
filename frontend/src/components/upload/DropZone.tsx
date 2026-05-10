import { useState, useRef } from 'react'
import type { DragEvent, ChangeEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { contractsApi } from '../../api/contracts'

const MAX_FILE_SIZE = 50 * 1024 * 1024 // 50MB
const ACCEPTED_TYPES = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']

export default function DropZone() {
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [jurisdiction, setJurisdiction] = useState('UK')
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  const validateFile = (file: File): string | null => {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      return 'Only PDF and DOCX files are accepted.'
    }
    if (file.size > MAX_FILE_SIZE) {
      return 'File size must not exceed 50MB.'
    }
    return null
  }

  const handleFile = async (file: File) => {
    const validationError = validateFile(file)
    if (validationError) {
      setError(validationError)
      return
    }
    setError(null)
    setUploading(true)
    try {
      const res = await contractsApi.upload(file, jurisdiction)
      navigate(`/review/${res.data.contract_id}`)
    } catch {
      setError('Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const onInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }

  return (
    <div className="space-y-4 soft-appear">
      <div className="premium-panel p-5 flex items-center gap-3">
        <label className="text-sm font-semibold text-slate-700">Jurisdiction</label>
        <select
          value={jurisdiction}
          onChange={(e) => setJurisdiction(e.target.value)}
          className="field max-w-48"
        >
          <option value="UK">UK</option>
          <option value="US">US</option>
          <option value="EU">EU</option>
          <option value="SG">Singapore</option>
          <option value="AU">Australia</option>
        </select>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => !uploading && inputRef.current?.click()}
        className={`premium-panel border-2 border-dashed p-12 text-center cursor-pointer transition-all ${
          dragging
            ? 'border-amber-500 bg-amber-50/80 scale-[1.01]'
            : 'border-slate-300 hover:border-amber-400 hover:bg-white'
        } ${uploading ? 'pointer-events-none opacity-60' : ''}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx"
          className="hidden"
          onChange={onInputChange}
        />

        {uploading ? (
          <div className="flex flex-col items-center gap-3">
            <div className="w-10 h-10 border-4 border-teal-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-slate-600">Uploading contract...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-100 to-teal-100 text-teal-800 flex items-center justify-center shadow-sm">
            <svg className="w-9 h-9" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            </div>
            <div>
              <p className="text-base font-semibold text-slate-800">Drop your contract here</p>
              <p className="text-sm text-slate-500 mt-1">PDF or DOCX, up to 50MB</p>
            </div>
            <span className="text-sm text-teal-700 font-semibold">or click to browse</span>
          </div>
        )}
      </div>

      {error && (
        <p className="text-sm text-red-700 flex items-center gap-1">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          {error}
        </p>
      )}
    </div>
  )
}
