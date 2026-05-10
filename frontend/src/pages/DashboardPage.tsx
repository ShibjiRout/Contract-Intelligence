import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { contractsApi } from '../api/contracts'
import Sidebar from '../components/layout/Sidebar'
import TopBar from '../components/layout/TopBar'
import ContractTable from '../components/dashboard/ContractTable'

export default function DashboardPage() {
  const navigate = useNavigate()

  const { data: contracts = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['contracts'],
    queryFn: () => contractsApi.list().then((r) => r.data),
  })

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="workspace">
        <TopBar />
        <main className="premium-main space-y-6 soft-appear">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-950">Dashboard</h1>
              <p className="text-sm text-slate-500 mt-1">
                {contracts.length} contract{contracts.length !== 1 ? 's' : ''} total
              </p>
            </div>
            <button
              onClick={() => navigate('/upload')}
              className="btn-primary"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Upload Contract
            </button>
          </div>

          {isError && (
            <div className="premium-card border-red-200 bg-red-50/90 px-4 py-3 text-sm text-red-700">
              Failed to load contracts. Please refresh the page.
            </div>
          )}

          {!isLoading && !isError && (
            <>
              <div>
                <h2 className="text-base font-semibold text-slate-800 mb-3">All Contracts</h2>
                <ContractTable contracts={contracts} onDeleted={() => refetch()} />
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
