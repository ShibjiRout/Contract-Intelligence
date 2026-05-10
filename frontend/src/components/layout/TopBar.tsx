import { useDispatch } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../../api/auth'
import { clearUser } from '../../store/authSlice'
import { useAuth } from '../../hooks/useAuth'
import type { AppDispatch } from '../../store'
import type { UserRole } from '../../types'

const ROLE_BADGE: Record<UserRole, string> = {
  admin: 'bg-amber-100 text-amber-800 ring-1 ring-amber-200',
  senior_lawyer: 'bg-teal-100 text-teal-800 ring-1 ring-teal-200',
  junior_lawyer: 'bg-slate-100 text-slate-600 ring-1 ring-slate-200',
}

const ROLE_LABEL: Record<UserRole, string> = {
  admin: 'Admin',
  senior_lawyer: 'Senior Lawyer',
  junior_lawyer: 'Junior Lawyer',
}

export default function TopBar() {
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()
  const { user } = useAuth()

  const handleLogout = async () => {
    try {
      await authApi.logout()
    } finally {
      dispatch(clearUser())
      navigate('/login')
    }
  }

  return (
    <header className="h-16 bg-white/82 border-b border-slate-200/80 flex items-center justify-between px-6 sticky top-0 z-10 backdrop-blur-xl">
      <div>
        <h2 className="text-base font-semibold text-slate-950 tracking-tight">Contract Intelligence</h2>
        <p className="text-xs text-slate-500">Risk review and legal operations</p>
      </div>
      <div className="flex items-center gap-4">
        {user && (
          <div className="flex items-center gap-3 rounded-full border border-slate-200 bg-white/80 py-1 pl-3 pr-1 shadow-sm">
            <span className="text-sm font-semibold text-slate-900">{user.full_name}</span>
            <span
              className={`px-2.5 py-1 rounded-full text-xs font-semibold ${ROLE_BADGE[user.role]}`}
            >
              {ROLE_LABEL[user.role]}
            </span>
          </div>
        )}
        <button
          onClick={handleLogout}
          className="text-sm text-slate-500 hover:text-slate-950 flex items-center gap-1 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
            />
          </svg>
          Logout
        </button>
      </div>
    </header>
  )
}
