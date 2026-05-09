export type RiskLevel = 'GREEN' | 'AMBER' | 'RED' | 'UNKNOWN'
export type ContractStatus = 'UPLOADED' | 'PROCESSING' | 'OCR_COMPLETE' | 'EXTRACTION_COMPLETE' | 'REVIEW_READY' | 'APPROVED' | 'REJECTED' | 'ERROR'
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
  file_name: string
  status: ContractStatus
  final_risk: RiskLevel
  jurisdiction: string
  clause_count: number
  missing_clauses: string[]
  created_at: string
  updated_at: string
}

export interface Clause {
  clause_id: string
  contract_id: string
  clause_type: string
  raw_text: string
  start_page: number
  end_page: number
  parties_mentioned: string[]
  key_obligations: string[]
  risk_indicators: string[]
  confidence: number
  risk_level: RiskLevel
  recommendation?: string
  suggested_fix?: string
}

export interface ContributingFactor {
  source: string
  finding: string
  weight: number
  impact: 'HIGH' | 'MEDIUM' | 'LOW'
}

export interface Explanation {
  overall_risk: RiskLevel
  score: number
  contributing_factors: ContributingFactor[]
  missing_clauses: string[]
  conflicts: string[]
  degraded_mode: boolean
  failed_sources: string[]
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
  rule_type: 'REQUIRED' | 'FORBIDDEN' | 'CONDITIONAL'
  description: string
  weight: number
  is_active: boolean
}

export interface PlaybookRuleCreate {
  clause_type: string
  jurisdiction: string
  rule_type: 'REQUIRED' | 'FORBIDDEN' | 'CONDITIONAL'
  description: string
  weight: number
}
