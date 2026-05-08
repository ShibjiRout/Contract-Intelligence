import client from './client'
import type { Explanation } from '../types'

export const clausesApi = {
  approve: (clauseId: string) => client.patch(`/api/clauses/${clauseId}/approve`),
  reject: (clauseId: string) => client.patch(`/api/clauses/${clauseId}/reject`),
  modify: (clauseId: string, modified_text: string) =>
    client.patch(`/api/clauses/${clauseId}/modify`, { modified_text }),
  getExplanation: (clauseId: string) => client.get<Explanation>(`/api/clauses/${clauseId}/explanation`),
}
