import client from './client'
import type { ClauseRecommendation } from '../types'

export const clausesApi = {
  approve: (clauseId: string) =>
    client.patch(`/clauses/${clauseId}/approve`),

  reject: (clauseId: string) =>
    client.patch(`/clauses/${clauseId}/reject`),

  modify: (clauseId: string, body: {
    lawyer_recommendation: string
    lawyer_mail_id: string
    accept_ai_recommendation?: boolean
  }) => client.patch(`/clauses/${clauseId}/modify`, body),

  addClause: (body: {
    contract_id: string
    clause_type: string
    raw_text: string
  }) => client.post('/clauses/new', body),

  getRecommendation: (clauseId: string) =>
    client.get<ClauseRecommendation>(`/clauses/${clauseId}/recommendation`),

  delete: (clauseId: string) =>
    client.delete(`/clauses/${clauseId}`),
}
