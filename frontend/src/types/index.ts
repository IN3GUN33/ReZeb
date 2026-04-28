export interface Session {
  id: string;
  status: "pending" | "queued" | "processing" | "completed" | "failed";
  construction_type: string | null;
  construction_type_confidence: number | null;
  verdict: Verdict | null;
  escalated: boolean;
  error_message: string | null;
  photos: Photo[];
  defects: Defect[];
}

export interface Photo {
  id: string;
  original_filename: string;
  file_size_bytes: number;
  is_blurry: boolean;
  sharpness_score: number | null;
  has_aruco_marker: boolean;
}

export interface Defect {
  id: string;
  defect_type: string;
  severity: "acceptable" | "significant" | "critical";
  description: string;
  measurement_mm: number | null;
  confidence: number;
  ntd_references: NTDReference[];
  bbox: number[] | null;
}

export interface NTDReference {
  code: string;
  clause: string;
  requirement: string;
}

export interface Verdict {
  construction_type: string;
  defects: Defect[];
  overall_assessment: string;
  requires_immediate_action: boolean;
  disclaimer: string;
}

export interface PTOQuery {
  id: string;
  raw_text: string;
  normalized_text: string | null;
  status: "pending" | "processing" | "completed" | "failed";
  match_status: "exact" | "analog" | "not_found" | null;
  confidence: number | null;
  results: RegistryCandidate[];
}

export interface RegistryCandidate {
  registry_id: string;
  name: string;
  code: string | null;
  unit: string | null;
}

export interface RegistryItem {
  id: string;
  code: string | null;
  name: string;
  unit: string | null;
  category: string | null;
  manufacturer: string | null;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  location: string | null;
  status: "active" | "completed" | "archived";
}

export type UserRole = "admin" | "engineer" | "viewer";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
}

export interface NTDDocument {
  id: string;
  code: string;
  title: string;
  doc_type: string;
  version: string | null;
}

export interface NTDClause {
  id: string;
  document_id: string;
  clause_number: string;
  content: string;
  score?: number;
}

export interface APIKey {
  id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

export interface AuditEvent {
  id: string;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  ip_address: string | null;
  created_at: string;
}

export interface BudgetStats {
  monthly_cost_rub: number;
  monthly_limit_rub: number;
  ratio: number;
  alert: boolean;
}
