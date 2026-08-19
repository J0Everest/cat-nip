export interface CandidateEvent {
  event_id: number;
  description: string;
  peril: string;
  industry_loss_b: number;
  air_description?: string | null;
  air_magnitude?: number | null;
  air_location?: string | null;
  selected?: boolean;
}

export interface SearchEventsResponse {
  events: CandidateEvent[];
  count: number;
}

export interface ScenarioSummary {
  scenario: string;
  gross_loss_m: number;
  contracts: number;
  industry_loss_b: number;
  market_share_pct: number;
}

export interface ContractLoss {
  layerkey: string;
  department: string;
  company: string;
  subtype: string;
  contract: string;
  terms: string;
  everest_limit: number;
  rol: number;
  share: number;
  low_gross_m: number;
  med_gross_m: number;
  high_gross_m: number;
}

export interface DetailRow {
  layerkey: string;
  scenario: string;
  department: string;
  company: string;
  contract: string;
  industry_loss_b: number;
  gross_loss_m: number;
  reins_recovery_m: number;
  net_loss_m: number;
}

export interface AnalyzeResponse {
  summary: ScenarioSummary[];
  contracts: ContractLoss[];
  detail: DetailRow[];
  generated_sql: string;
}

export interface ConfigResponse {
  peril_options: string[];
  default_server: string;
  default_database: string;
  air_events_db: string;
  design_tokens: Record<string, unknown>;
}

export interface SavedScenario {
  id: number;
  name: string;
  created_at: string;
  updated_at: string;
  query_text: string;
  peril: string;
  zone: string;
  loss_lo: number;
  loss_hi: number;
  filter_mode: string;
  event_keyword: string;
  low_event_id: number;
  med_event_id: number;
  high_event_id: number;
  database: string;
  candidate_event_ids: number[];
}
