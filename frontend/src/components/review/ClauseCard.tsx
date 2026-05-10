import { useState } from 'react'
import type { Clause } from '../../types'
import { clausesApi } from '../../api/clauses'
import { useAuth } from '../../hooks/useAuth'

interface Props {
  clause: Clause
  onUpdated?: () => void
}

type Toast = { message: string; type: 'success' | 'error' }

const RISK_STYLES: Record<string, string> = {
  RED: 'bg-red-100 text-red-700 border-red-200',
  AMBER: 'bg-amber-100 text-amber-700 border-amber-200',
  GREEN: 'bg-emerald-100 text-emerald-700 border-emerald-200',
}

const STATUS_STYLES: Record<string, string> = {
  approved: 'bg-emerald-100 text-emerald-700',
  rejected: 'bg-red-100 text-red-700',
  need_changes: 'bg-amber-100 text-amber-700',
  ai_flagged: 'bg-blue-100 text-blue-700',
}

export default function ClauseCard({ clause, onUpdated }: Props) {
  const { canModify, hasRole } = useAuth()
  const [expanded, setExpanded] = useState(false)
  const [modifying, setModifying] = useState(false)
  const [lawyerRec, setLawyerRec] = useState('')
  const [lawyerEmail, setLawyerEmail] = useState('')
  const [acceptAI, setAcceptAI] = useState(false)
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
      showToast('Clause approved.', 'success')
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
    if (!acceptAI && !lawyerRec.trim()) {
      showToast('Enter your recommendation or accept the AI suggestion.', 'error')
      return
    }
    if (!lawyerEmail.trim()) {
      showToast('Email is required.', 'error')
      return
    }
    setLoading(true)
    try {
      await clausesApi.modify(clause.clause_id, {
        lawyer_recommendation: lawyerRec,
        lawyer_mail_id: lawyerEmail,
        accept_ai_recommendation: acceptAI,
      })
      showToast('Changes submitted.', 'success')
      setModifying(false)
      onUpdated?.()
    } catch {
      showToast('Failed to submit changes.', 'error')
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

  const isDecided = ['approved', 'rejected', 'need_changes'].includes(clause.status ?? '')
  const isAiFlagged = clause.status === 'ai_flagged'
  const truncatedText = clause.raw_text.length > 300
    ? clause.raw_text.slice(0, 300) + '…'
    : clause.raw_text

  return (
    <div className="premium-card premium-card-hover p-4 space-y-3 relative soft-appear">
      {toast && (
        <div className={`absolute top-2 right-2 z-10 text-xs px-3 py-1.5 rounded-full font-medium shadow ${
          toast.type === 'success' ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
        }`}>
          {toast.message}
        </div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide bg-slate-100 px-2 py-0.5 rounded">
          {clause.clause_type}
        </span>
        {clause.risk_category && (
          <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${RISK_STYLES[clause.risk_category] ?? ''}`}>
            {clause.risk_category}
          </span>
        )}
      </div>

      {/* Raw text */}
      <div>
        <p className="text-sm text-slate-700 leading-relaxed">
          {expanded ? clause.raw_text : truncatedText}
        </p>
        {clause.raw_text.length > 300 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-teal-700 hover:underline mt-1 font-semibold"
          >
            {expanded ? 'Show less' : 'Show more'}
          </button>
        )}
      </div>

      {/* Legal intent */}
      {clause.legal_intent && (
        <div className="bg-slate-50 border border-slate-200 rounded-md px-3 py-2 text-xs text-slate-700">
          <span className="font-semibold text-slate-500 uppercase tracking-wide">Intent: </span>
          {clause.legal_intent}
        </div>
      )}

      {/* Gap summary */}
      {clause.gap_summary && (
        <div className="bg-amber-50 border border-amber-100 rounded-md px-3 py-2 text-xs text-amber-900">
          <span className="font-semibold">Gap from Gold Standard: </span>
          {clause.gap_summary}
        </div>
      )}

      {/* Violation */}
      {clause.violation_message && (
        <div className="bg-red-50 border border-red-100 rounded-md px-3 py-2 text-xs text-red-800">
          <span className="font-semibold">Policy Violation: </span>
          {clause.violation_message}
        </div>
      )}

      {/* Precedent */}
      {clause.precedent && (
        <div className="bg-indigo-50 border border-indigo-100 rounded-md px-3 py-2 text-xs text-indigo-800">
          <span className="font-semibold">Precedent: </span>
          Accepted for <strong>{clause.precedent.party}</strong> on {clause.precedent.date}
        </div>
      )}

      {/* AI Recommendation */}
      {clause.ai_recommendation && (
        <div className="bg-teal-50 border border-teal-100 rounded-md px-3 py-2 text-xs text-teal-900 whitespace-pre-line">
          <span className="font-semibold">AI Recommendation: </span>
          {clause.ai_recommendation}
        </div>
      )}

      {/* Modify form */}
      {modifying && (
        <div className="space-y-3 pt-2 border-t border-slate-100">
          {clause.ai_recommendation && (
            <label className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
              <input
                type="checkbox"
                checked={acceptAI}
                onChange={(e) => setAcceptAI(e.target.checked)}
                className="rounded"
              />
              Accept AI recommendation as-is
            </label>
          )}
          {!acceptAI && (
            <>
              <div>
                <label className="text-xs font-medium text-slate-600 block mb-1">Your recommendation</label>
                <textarea
                  value={lawyerRec}
                  onChange={(e) => setLawyerRec(e.target.value)}
                  rows={4}
                  className="field resize-y w-full"
                  placeholder="Write your recommended changes..."
                />
              </div>
            </>
          )}
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Your email</label>
            <input
              type="email"
              value={lawyerEmail}
              onChange={(e) => setLawyerEmail(e.target.value)}
              className="field w-full"
              placeholder="you@firm.com"
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleModify}
              disabled={loading}
              className="btn-primary px-3 py-1.5 text-xs"
            >
              Submit
            </button>
            <button
              onClick={() => setModifying(false)}
              className="text-xs text-slate-600 px-3 py-1.5 rounded-md hover:bg-slate-100 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Action buttons */}
      {canModify && !modifying && (!isDecided || isAiFlagged) && (
        <div className="flex gap-2 pt-1">
          <button
            onClick={handleApprove}
            disabled={loading}
            className="text-xs bg-emerald-600 text-white px-3 py-1.5 rounded-md hover:bg-emerald-700 disabled:opacity-50 transition-colors"
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
            className="text-xs border border-slate-300 text-slate-700 px-3 py-1.5 rounded-md hover:bg-slate-50 disabled:opacity-50 transition-colors"
          >
            Request Changes
          </button>
        </div>
      )}

      {/* Status badge */}
      {isDecided && (
        <div className={`text-xs font-medium px-2 py-1 rounded-md inline-block ${STATUS_STYLES[clause.status!] ?? ''}`}>
          {clause.status === 'need_changes' ? 'Changes Requested' : clause.status!.charAt(0).toUpperCase() + clause.status!.slice(1)}
        </div>
      )}

      {/* Admin delete */}
      {hasRole('admin') && (
        <div className="mt-2 pt-2 border-t border-slate-100">
          <button
            onClick={handleDelete}
            disabled={loading}
            className="text-xs border border-red-300 text-red-600 px-3 py-1.5 rounded-md hover:bg-red-50 disabled:opacity-50 transition-colors"
          >
            Delete
          </button>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-slate-400 pt-1 border-t border-slate-100">
        <span>Pages {clause.start_page}–{clause.end_page}</span>
        <span>Confidence: {(clause.confidence * 100).toFixed(0)}%</span>
      </div>
    </div>
  )
}
