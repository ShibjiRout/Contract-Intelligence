import { useSelector } from 'react-redux'
import { useParams } from 'react-router-dom'
import Sidebar from '../components/layout/Sidebar'
import TopBar from '../components/layout/TopBar'
import DropZone from '../components/upload/DropZone'
import UploadProgress from '../components/upload/UploadProgress'
import type { RootState } from '../store'

export default function UploadPage() {
  // contractId may be set after upload redirects back; progress is keyed by contractId
  const activeContractId = useSelector((s: RootState) => s.contracts.activeContractId)

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-2xl mx-auto space-y-6">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Upload Contract</h1>
              <p className="text-sm text-gray-500 mt-0.5">
                Upload a PDF or DOCX contract for AI-powered risk analysis.
              </p>
            </div>

            <DropZone />

            {activeContractId && (
              <UploadProgress contractId={activeContractId} />
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
