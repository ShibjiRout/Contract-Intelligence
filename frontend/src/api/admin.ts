import client from './client'
import type { PlaybookRule, PlaybookRuleCreate } from '../types'

export interface ClearPlaybookDataResponse {
  postgres_rules_deleted: number
  qdrant_collection_cleared: boolean
  neo4j_nodes_deleted: number
}

export const adminApi = {
  listRules: (jurisdiction?: string) =>
    client
      .get<PlaybookRule[]>('/admin/playbook-rules', { params: { jurisdiction } })
      .then((r) => r.data),
  createRule: (data: PlaybookRuleCreate) =>
    client.post<PlaybookRule>('/admin/playbook-rules', data).then((r) => r.data),
  updateRule: (id: number, data: Partial<PlaybookRuleCreate & { is_active: boolean }>) =>
    client.patch<PlaybookRule>(`/admin/playbook-rules/${id}`, data).then((r) => r.data),
  deleteRule: (id: number) => client.delete(`/admin/playbook-rules/${id}`),
  uploadPdf: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return client.post<{ rules_created: number; rules: PlaybookRule[] }>(
      '/admin/playbook-rules/upload-pdf',
      form
    )
  },
  clearPlaybookData: () =>
    client
      .delete<ClearPlaybookDataResponse>('/admin/playbook-rules/clear-all')
      .then((r) => r.data),
}
