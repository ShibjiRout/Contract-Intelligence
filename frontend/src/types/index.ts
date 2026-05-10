export type RiskCategory = 'GREEN' | 'AMBER' | 'RED'
export type ClauseStatus = 'approved' | 'rejected' | 'need_changes' | 'pending'
export type ContractStatus = 'UPLOADED' | 'PROCESSING' | 'OCR_COMPLETE' | 'EXTRACTION_COMPLETE' | 'REVIEW_READY' | 'COMPLETED' | 'ERROR'
export type UserRole = 'junior_lawyer' | 'senior_lawyer' | 'admin'

export interface User {
  user_id: string
  email: string
  full_name: string
  role: UserRole
  tenant_id: string
}

export interface Contract {
  contract_id: string
  filename: string
  status: ContractStatus
  current_stage: string | null
  final_risk: RiskCategory | null
  created_at: string
  updated_at: string
}

export interface Precedent {
  party: string
  date: string
  contract_id: string
}

export interface Clause {
  clause_id: string
  contract_id?: string
  clause_type: string
  raw_text: string
  start_page: number
  end_page: number
  parties_mentioned: string[]
  confidence: number
  status?: ClauseStatus
  risk_category?: RiskCategory
  legal_intent?: string
  gap_summary?: string
  violation_message?: string
  precedent?: Precedent | null
  ai_recommendation?: string
  lawyer_recommendation?: string
  lawyer_mail_id?: string
  reviewed_by?: string
  tenant_id?: string
}

export interface ClauseRecommendation {
  clause_id: string
  ai_recommendation: string
  legal_intent?: string
  gap_summary?: string
  violation_message?: string
  precedent?: Precedent | null
}

export interface ProgressEvent {
  stage: string
  percent: number
  message: string
}

export interface PlaybookRule {
  id: number
  clause_type: string
  jurisdiction: string
  rule_type: 'REQUIRED' | 'FORBIDDEN'
  description: string
  weight: number
  is_active: boolean
  violation_message?: string
}

export interface PlaybookRuleCreate {
  clause_type: string
  jurisdiction: string
  rule_type: 'REQUIRED' | 'FORBIDDEN'
  description: string
  weight: number
  violation_message?: string
}
