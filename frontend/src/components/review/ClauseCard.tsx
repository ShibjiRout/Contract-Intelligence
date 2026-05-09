import { useState } from 'react'
import type { Clause } from '../../types'
import { clausesApi } from '../../api/clauses'
import { useAuth } from '../../hooks/useAuth'
import RiskBadge from './RiskBadge'

interface Props {
  clause: Clause
  onUpdated?: () => void
}

type Toast = { message: string; type: 'success' | 'error' }

export default function ClauseCard({ clause, onUpdated }: Props) {
  const { canModify, hasRole } = useAuth()
  const [expanded, setExpanded] = useState(false)
  const [modifying, setModifying] = useState(false)
  const [modifiedText, setModifiedText] = useState(clause.suggested_fix ?? clause.raw_text)
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState<Toast | null>(null)

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  const handleApprove = async () => {
    setLoading(true)
    try {
      await clausesApi.approve(clause.clause_id)
      showToast('Clause approved successfully.', 'success')
      onUpdated?.()
    } catch {
      showToast('Failed to approve clause.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleReject = async () => {
    setLoading(true)
    try {
      await clausesApi.reject(clause.clause_id)
      showToast('Clause rejected.', 'success')
      onUpdated?.()
    } catch {
      showToast('Failed to reject clause.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleModify = async () => {
    setLoading(true)
    try {
      await clausesApi.modify(clause.clause_id, modifiedText)
      showToast('Clause modified successfully.', 'success')
      setModifying(false)
      onUpdated?.()
    } catch {
      showToast('Failed to modify clause.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    setLoading(true)
    try {
      await clausesApi.delete(clause.clause_id)
      showToast('Clause deleted.', 'success')
      onUpdated?.()
    } catch {
      showToast('Failed to delete clause.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const truncatedText = clause.raw_text.length > 300
    ? clause.raw_text.slice(0, 300) + '…'
    : clause.raw_text

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3 relative">
      {toast && (
        <div className={`absolute top-2 right-2 z-10 text-xs px-3 py-1.5 rounded-full font-medium shadow ${
          toast.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
        }`}>
          {toast.message}
        </div>
      )}

      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide bg-gray-100 px-2 py-0.5 rounded">
          {clause.clause_type}
        </span>
        <RiskBadge level={clause.risk_level} />
      </div>

      <div>
        <p className="text-sm text-gray-700 leading-relaxed">
          {expanded ? clause.raw_text : truncatedText}
        </p>
        {clause.raw_text.length > 300 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-indigo-600 hover:underline mt-1"
          >
            {expanded ? 'Show less' : 'Show more'}
          </button>
        )}
      </div>

      {clause.recommendation && (
        <div className="bg-blue-50 border border-blue-100 rounded-md px-3 py-2 text-xs text-blue-800">
          <span className="font-semibold">Recommendation: </span>
          {clause.recommendation}
        </div>
      )}

      {modifying && (
        <div className="space-y-2">
          <label className="text-xs font-medium text-gray-600">Modified text</label>
          <textarea
            value={modifiedText}
            onChange={(e) => setModifiedText(e.target.value)}
            rows={5}
            className="w-full border border-gray-300 rounded-md text-sm p-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-y"
          />
          <div className="flex gap-2">
            <button
              onClick={handleModify}
              disabled={loading}
              className="text-xs bg-indigo-600 text-white px-3 py-1.5 rounded-md hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              Save Changes
            </button>
            <button
              onClick={() => setModifying(false)}
              className="text-xs text-gray-600 px-3 py-1.5 rounded-md hover:bg-gray-100 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {canModify && !modifying && (
        <div className="flex gap-2 pt-1">
          <button
            onClick={handleApprove}
            disabled={loading}
            className="text-xs bg-green-600 text-white px-3 py-1.5 rounded-md hover:bg-green-700 disabled:opacity-50 transition-colors"
          >
            Approve
          </button>
          <button
            onClick={handleReject}
            disabled={loading}
            className="text-xs bg-red-600 text-white px-3 py-1.5 rounded-md hover:bg-red-700 disabled:opacity-50 transition-colors"
          >
            Reject
          </button>
          <button
            onClick={() => setModifying(true)}
            disabled={loading}
            className="text-xs border border-gray-300 text-gray-700 px-3 py-1.5 rounded-md hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            Modify
          </button>
        </div>
      )}

      {hasRole('admin') && (
        <div className="mt-2 pt-2 border-t border-gray-100">
          <button
            onClick={handleDelete}
            disabled={loading}
            className="text-xs border border-red-300 text-red-600 px-3 py-1.5 rounded-md hover:bg-red-50 disabled:opacity-50 transition-colors"
          >
            Delete
          </button>
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-gray-400 pt-1 border-t border-gray-100">
        <span>Pages {clause.start_page}–{clause.end_page}</span>
        <span>Confidence: {(clause.confidence * 100).toFixed(0)}%</span>
      </div>
    </div>
  )
}
