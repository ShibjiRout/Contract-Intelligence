import { useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { fetchMe } from '../store/authSlice'
import type { AppDispatch, RootState } from '../store'

interface Props {
  children: React.ReactNode
}

export default function ProtectedRoute({ children }: Props) {
  const dispatch = useDispatch<AppDispatch>()
  const user = useSelector((s: RootState) => s.auth.user)
  const loading = useSelector((s: RootState) => s.auth.loading)
  const checked = useSelector((s: RootState) => s.auth.checked)

  useEffect(() => {
    if (!checked) {
      dispatch(fetchMe())
    }
  }, [checked, dispatch])

  if (!checked || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}
