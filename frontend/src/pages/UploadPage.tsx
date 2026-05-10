import { useSelector } from 'react-redux'
import Sidebar from '../components/layout/Sidebar'
import TopBar from '../components/layout/TopBar'
import DropZone from '../components/upload/DropZone'
import UploadProgress from '../components/upload/UploadProgress'
import type { RootState } from '../store'

export default function UploadPage() {
  // contractId may be set after upload redirects back; progress is keyed by contractId
  const activeContractId = useSelector((s: RootState) => s.contracts.activeContractId)

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="workspace">
        <TopBar />
        <main className="premium-main">
          <div className="max-w-2xl mx-auto space-y-6">
            <div className="soft-appear">
              <h1 className="text-2xl font-bold tracking-tight text-slate-950">Upload Contract</h1>
              <p className="text-sm text-slate-500 mt-1">
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
