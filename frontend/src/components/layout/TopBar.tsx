import { useDispatch } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../../api/auth'
import { clearUser } from '../../store/authSlice'
import type { AppDispatch } from '../../store'

export default function TopBar() {
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()

  const handleLogout = async () => {
    try {
      await authApi.logout()
    } finally {
      dispatch(clearUser())
      navigate('/login')
    }
  }

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 sticky top-0 z-10">
      <h2 className="text-base font-semibold text-gray-900">Contract Intelligence</h2>
      <button
        onClick={handleLogout}
        className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1 transition-colors"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
        </svg>
        Logout
      </button>
    </header>
  )
}
