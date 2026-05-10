import { useSelector } from 'react-redux'
import type { RootState } from '../../store'

const STAGES = ['UPLOADED', 'OCR', 'EXTRACTION', 'ANALYSIS', 'REVIEW_READY'] as const
type Stage = typeof STAGES[number]

const STAGE_LABELS: Record<Stage, string> = {
  UPLOADED: 'Uploaded',
  OCR: 'OCR Processing',
  EXTRACTION: 'Clause Extraction',
  ANALYSIS: 'Risk Analysis',
  REVIEW_READY: 'Ready for Review',
}

interface Props {
  contractId: string
}

export default function UploadProgress({ contractId }: Props) {
  const progressEvent = useSelector((s: RootState) => s.contracts.progress[contractId])

  if (!progressEvent) return null

  const currentStageIndex = STAGES.findIndex(
    (s) => s === progressEvent.stage.toUpperCase()
  )

  return (
    <div className="premium-panel p-6 space-y-4 soft-appear">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-950">Processing Contract</h3>
        <span className="text-sm font-semibold text-teal-700">{progressEvent.percent}%</span>
      </div>

      <div className="w-full bg-gray-100 rounded-full h-2">
        <div
          className="bg-teal-600 h-2 rounded-full transition-all duration-500"
          style={{ width: `${progressEvent.percent}%` }}
        />
      </div>

      <p className="text-sm text-slate-600">{progressEvent.message}</p>

      <div className="flex items-center gap-1">
        {STAGES.map((stage, idx) => (
          <div key={stage} className="flex items-center">
            <div
              className={`flex items-center gap-1 text-xs px-2 py-1 rounded-full ${
                idx < currentStageIndex
                  ? 'bg-green-100 text-green-700'
                  : idx === currentStageIndex
                  ? 'bg-teal-100 text-teal-700 font-medium'
                  : 'bg-gray-100 text-gray-400'
              }`}
            >
              {idx < currentStageIndex && (
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
              {STAGE_LABELS[stage]}
            </div>
            {idx < STAGES.length - 1 && (
              <div className="w-4 h-px bg-gray-300 mx-1" />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
