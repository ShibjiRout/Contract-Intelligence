import client from './client'
import type { Contract, Clause } from '../types'

export const contractsApi = {
  upload: (file: File, jurisdiction: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('jurisdiction', jurisdiction)
    return client.post<{ contract_id: string }>('/contracts/upload', form)
  },
  getContract: (id: string) => client.get<Contract>(`/contracts/${id}`),
  getStatus: (id: string) => client.get<{ status: string; current_stage: string }>(`/contracts/${id}/status`),
  getClauses: (id: string) => client.get<Clause[]>(`/contracts/${id}/clauses`),
  complete: (id: string) => client.post<{ contract_id: string; status: string }>(`/contracts/${id}/complete`),
  deleteData: (id: string) => client.delete<{ contract_id: string; deleted: boolean }>(`/contracts/${id}/data`),
  delete: (id: string) => client.delete<{ contract_id: string; deleted: boolean }>(`/contracts/${id}`),
  list: () => client.get<Contract[]>('/contracts'),
}
