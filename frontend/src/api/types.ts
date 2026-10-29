export type JobStatus = "received" | "analyzing" | "generating_report" | "done" | "failed"

export interface PredictionResult {
  module: string
  module_name: string
  model_architecture: string
  report_id: string
  timestamp: string
  filename: string
  inference_time_ms: number
  prediction?: string
  confidence?: number
  low_confidence?: boolean
  decision_threshold?: number
  probabilities?: Record<string, number>
  all_probabilities?: Record<string, number>
  probability_abnormal?: number
  flagged_findings?: Array<{
    pathology: string
    probability: number
    threshold: number
  }>
  findings_count?: number
  derived_no_finding?: boolean
  derived_status?: string
  primary_finding?: string
  top2?: Array<{
    grade: string
    probability: number
  }>
  reference_description?: string
  notices?: string[]
  interpretation_note?: string
  analysis_mode?: string
  roi_box?: number[]
  user_id?: string
}

export interface JobResponse {
  job_id: string
  status: JobStatus
  progress_stage: number
  result?: PredictionResult
  error?: string
}

export interface UserProfile {
  id?: string
  name: string
  age: string | number
  sex: string
  phone?: string
  contact?: string
  email: string
  avatar?: string
  avatar_url?: string
  created_at?: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: UserProfile
}
