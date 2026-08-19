export interface ParsedScenario {
  peril: string | null;
  zone: string | null;
  model_no: number | null;
  loss_lo: number | null;
  loss_hi: number | null;
  mag_lo: number | null;
  mag_hi: number | null;
  event_keyword: string;
  confidence: 'high' | 'partial' | 'needs_refinement';
  confidence_parts: number;
  confidence_total: number;
}

export interface AirTableProfile {
  schema: string;
  table: string;
  label: string;
  event_id_col: string;
  desc_col: string | null;
  mag_col: string | null;
  loc_col: string | null;
}

export interface AirTablesResponse {
  tables: AirTableProfile[];
  prefiltered: boolean;
  recommended_table: string | null;
}

export interface AirDescriptionsResponse {
  descriptions: string[];
}

export interface ModelEntry {
  model_no: number;
  label: string;
}

export type ModelInfoResponse = Record<string, Record<string, ModelEntry[]>>;
