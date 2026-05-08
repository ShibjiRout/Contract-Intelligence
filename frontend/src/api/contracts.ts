import client from './client'
import type { Contract, Clause } from '../types'

export const contractsApi = {
  upload: (file: File, jurisdiction: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('jurisdiction', jurisdiction)
    return client.post<{ contract_id: string }>('/api/contracts/upload', form)
  },
  getContract: (id: string) => client.get<Contract>(`/api/contracts/${id}`),
  getStatus: (id: string) => client.get<{ status: string; current_stage: string }>(`/api/contracts/${id}/status`),
  getClauses: (id: string) => client.get<Clause[]>(`/api/contracts/${id}/clauses`),
  list: () => client.get<Contract[]>('/api/contracts'),
}
