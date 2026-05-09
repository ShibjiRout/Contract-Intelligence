import client from './client'
import type { Contract, Clause } from '../types'

export const contractsApi = {
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return client.post<{ contract_id: string }>('/contracts/upload', form)
  },
  getContract: (id: string) => client.get<Contract>(`/contracts/${id}`),
  getStatus: (id: string) => client.get<{ status: string; current_stage: string }>(`/contracts/${id}/status`),
  getClauses: (id: string) => client.get<Clause[]>(`/contracts/${id}/clauses`),
  list: () => client.get<Contract[]>('/contracts'),
}
