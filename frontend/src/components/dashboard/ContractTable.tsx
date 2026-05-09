import { useNavigate } from 'react-router-dom'
import type { Contract } from '../../types'
import RiskBadge from '../review/RiskBadge'

const STATUS_LABELS: Record<Contract['status'], string> = {
  UPLOADED: 'Uploaded',
  PROCESSING: 'Processing',
  OCR_COMPLETE: 'OCR Complete',
  EXTRACTION_COMPLETE: 'Extraction Complete',
  REVIEW_READY: 'Review Ready',
  APPROVED: 'Approved',
  REJECTED: 'Rejected',
  ERROR: 'Error',
}

interface Props {
  contracts: Contract[]
}

export default function ContractTable({ contracts }: Props) {
  const navigate = useNavigate()

  if (contracts.length === 0) {
    return (
      <div className="text-center py-16 text-sm text-gray-500">
        No contracts uploaded yet.{' '}
        <button
          onClick={() => navigate('/upload')}
          className="text-indigo-600 hover:underline"
        >
          Upload your first contract
        </button>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="text-left px-4 py-3 font-medium text-gray-600">File Name</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Risk</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Stage</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Created</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {contracts.map((contract) => (
            <tr
              key={contract.contract_id}
              onClick={() => navigate(`/review/${contract.contract_id}`)}
              className="cursor-pointer hover:bg-gray-50 transition-colors"
            >
              <td className="px-4 py-3 font-medium text-gray-900 max-w-xs truncate">
                {contract.filename}
              </td>
              <td className="px-4 py-3 text-gray-600">
                {STATUS_LABELS[contract.status]}
              </td>
              <td className="px-4 py-3">
                <RiskBadge level={contract.final_risk ?? 'UNKNOWN'} />
              </td>
              <td className="px-4 py-3 text-gray-600">{contract.current_stage ?? '—'}</td>
              <td className="px-4 py-3 text-gray-500">
                {new Date(contract.created_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
