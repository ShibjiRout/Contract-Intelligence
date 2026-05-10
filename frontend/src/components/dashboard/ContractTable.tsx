import { useNavigate } from 'react-router-dom'
import type { Contract } from '../../types'
import { contractsApi } from '../../api/contracts'
import { useAuth } from '../../hooks/useAuth'
import RiskBadge from '../review/RiskBadge'

const STATUS_CONFIG: Record<Contract['status'], { label: string; classes: string }> = {
  UPLOADED:            { label: 'Uploaded',           classes: 'bg-gray-100 text-gray-600' },
  PROCESSING:          { label: 'Processing',          classes: 'bg-blue-100 text-blue-700' },
  OCR_COMPLETE:        { label: 'OCR Complete',        classes: 'bg-blue-100 text-blue-700' },
  EXTRACTION_COMPLETE: { label: 'Extracting',          classes: 'bg-blue-100 text-blue-700' },
  REVIEW_READY:        { label: 'Review Ready',        classes: 'bg-amber-100 text-amber-700' },
  COMPLETED:           { label: 'Completed',           classes: 'bg-green-100 text-green-700' },
  APPROVED:            { label: 'Approved',            classes: 'bg-green-100 text-green-700' },
  REJECTED:            { label: 'Rejected',            classes: 'bg-red-100 text-red-700' },
  ERROR:               { label: 'Error',               classes: 'bg-red-100 text-red-700' },
}

const STAGE_LABELS: Record<string, string> = {
  ocr: 'OCR',
  clause_extraction: 'Extracting Clauses',
  risk_analysis: 'Risk Analysis',
  recommendation: 'Generating Recommendations',
  cleanup: 'Finalising',
  post_decision: 'Recording Decision',
}

interface Props {
  contracts: Contract[]
  onDeleted?: () => void
}

export default function ContractTable({ contracts, onDeleted }: Props) {
  const navigate = useNavigate()
  const { canModify } = useAuth()

  const handleDelete = async (contractId: string) => {
    const confirmed = window.confirm('Permanently delete this contract from all contract stores?')
    if (!confirmed) return
    await contractsApi.delete(contractId)
    onDeleted?.()
  }

  if (contracts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <svg className="w-12 h-12 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <p className="text-sm text-gray-500">No contracts yet.</p>
        <button
          onClick={() => navigate('/upload')}
          className="text-sm text-indigo-600 font-medium hover:underline"
        >
          Upload your first contract
        </button>
      </div>
    )
  }

  return (
    <div className="table-shell">
      <table className="w-full text-sm">
        <thead className="table-head">
          <tr>
            <th className="table-th">File Name</th>
            <th className="table-th">Status</th>
            <th className="table-th">Risk</th>
            <th className="table-th">Stage</th>
            <th className="table-th">Uploaded</th>
            {canModify && <th className="px-5 py-3.5" />}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {contracts.map((contract) => {
            const statusCfg = STATUS_CONFIG[contract.status] ?? { label: contract.status, classes: 'bg-gray-100 text-gray-600' }
            const stageLabel = contract.current_stage
              ? (STAGE_LABELS[contract.current_stage] ?? contract.current_stage)
              : '—'
            const isProcessing = ['PROCESSING', 'OCR_COMPLETE', 'EXTRACTION_COMPLETE'].includes(contract.status)

            return (
              <tr
                key={contract.contract_id}
                onClick={() => navigate(`/review/${contract.contract_id}`)}
                className="table-row group"
              >
                <td className="px-5 py-3.5 font-semibold text-slate-900 max-w-xs truncate group-hover:text-teal-800 transition-colors">
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    {contract.filename}
                  </div>
                </td>
                <td className="px-5 py-3.5">
                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${statusCfg.classes}`}>
                    {isProcessing && (
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                    )}
                    {statusCfg.label}
                  </span>
                </td>
                <td className="px-5 py-3.5">
                  <RiskBadge level={contract.final_risk ?? 'UNKNOWN'} />
                </td>
                <td className="px-5 py-3.5 text-slate-500 text-xs">{stageLabel}</td>
                <td className="px-5 py-3.5 text-slate-400 text-xs">
                  {new Date(contract.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
                </td>
                {canModify && (
                  <td className="px-5 py-3.5 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDelete(contract.contract_id)
                      }}
                      className="text-xs text-red-600 hover:text-red-800 font-medium transition-colors"
                    >
                      Delete
                    </button>
                  </td>
                )}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
