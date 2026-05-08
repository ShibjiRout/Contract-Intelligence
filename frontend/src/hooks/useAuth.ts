import { useSelector } from 'react-redux'
import type { RootState } from '../store'
import type { UserRole } from '../types'

export function useAuth() {
  const user = useSelector((s: RootState) => s.auth.user)
  const hasRole = (role: UserRole) => user?.role === role
  const canModify = user?.role === 'senior_lawyer' || user?.role === 'admin'
  return { user, hasRole, canModify }
}
