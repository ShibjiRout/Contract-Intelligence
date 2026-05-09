import client from './client'
import type { User } from '../types'

export const authApi = {
  login: (email: string, password: string) =>
    client.post('/auth/login', { email, password }),
  logout: () => client.post('/auth/logout'),
  me: () => client.get<User>('/auth/me'),
}
