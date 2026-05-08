import client from './client'
import type { User } from '../types'

export const authApi = {
  login: (email: string, password: string) =>
    client.post('/api/auth/login', { email, password }),
  logout: () => client.post('/api/auth/logout'),
  me: () => client.get<User>('/api/auth/me'),
}
