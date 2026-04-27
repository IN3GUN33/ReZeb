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
