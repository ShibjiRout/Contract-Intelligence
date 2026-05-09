import client from './client'

export interface UserRecord {
  user_id: string
  email: string
  role: 'junior_lawyer' | 'senior_lawyer' | 'admin'
  tenant_id: string
  is_active: boolean
  created_at: string
}

export interface UserCreate {
  email: string
  password: string
  role: 'junior_lawyer' | 'senior_lawyer' | 'admin'
  tenant_id: string
}

export const usersApi = {
  list: () => client.get<UserRecord[]>('/users/').then(r => r.data),
  create: (data: UserCreate) => client.post<UserRecord>('/users/', data).then(r => r.data),
  update: (userId: string, data: { role?: string; is_active?: boolean }) =>
    client.patch(`/users/${userId}`, data).then(r => r.data),
}
