import client from './client'
import type { Explanation } from '../types'

export const clausesApi = {
  approve: (clauseId: string) => client.patch(`/clauses/${clauseId}/approve`),
  reject: (clauseId: string) => client.patch(`/clauses/${clauseId}/reject`),
  modify: (clauseId: string, modified_text: string) =>
    client.patch(`/clauses/${clauseId}/modify`, { modified_text }),
  getRecommendation: (clauseId: string) => client.get<Explanation>(`/clauses/${clauseId}/recommendation`),
  delete: (clauseId: string) => client.delete(`/clauses/${clauseId}`),
}
