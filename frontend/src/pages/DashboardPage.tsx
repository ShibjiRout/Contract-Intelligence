import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { contractsApi } from '../api/contracts'
import Sidebar from '../components/layout/Sidebar'
import TopBar from '../components/layout/TopBar'
import ContractTable from '../components/dashboard/ContractTable'
import RiskSummaryChart from '../components/dashboard/RiskSummaryChart'

export default function DashboardPage() {
  const navigate = useNavigate()

  const { data: contracts = [], isLoading, isError } = useQuery({
    queryKey: ['contracts'],
    queryFn: () => contractsApi.list().then((r) => r.data),
  })

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Dashboard</h1>
              <p className="text-sm text-gray-500 mt-0.5">
                {contracts.length} contract{contracts.length !== 1 ? 's' : ''} total
              </p>
            </div>
            <button
              onClick={() => navigate('/upload')}
              className="bg-indigo-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Upload Contract
            </button>
          </div>

          {isError && (
            <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
              Failed to load contracts. Please refresh the page.
            </div>
          )}

          {!isLoading && !isError && (
            <>
              <RiskSummaryChart contracts={contracts} />
              <div>
                <h2 className="text-base font-medium text-gray-800 mb-3">All Contracts</h2>
                <ContractTable contracts={contracts} />
              </div>
            </>
          )}

          {isLoading && (
            <div className="flex items-center justify-center h-48">
              <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
