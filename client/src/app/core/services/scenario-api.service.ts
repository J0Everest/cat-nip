import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ParsedScenario, AirTablesResponse, AirDescriptionsResponse, ModelInfoResponse } from '../models/scenario.models';
import { SearchEventsResponse, AnalyzeResponse, ConfigResponse, SavedScenario } from '../models/event.models';

@Injectable({ providedIn: 'root' })
export class ScenarioApiService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api/v1';

  getConfig(): Observable<ConfigResponse> {
    return this.http.get<ConfigResponse>(`${this.base}/config/`);
  }

  nextQuarter(database: string): Observable<{ database: string }> {
    return this.http.post<{ database: string }>(`${this.base}/config/next-quarter/`, { database });
  }

  healthCheck(): Observable<{ status: string; db_reachable: boolean; server: string; database: string }> {
    return this.http.get<{ status: string; db_reachable: boolean; server: string; database: string }>(`${this.base}/health/`);
  }

  parseQuery(query: string): Observable<ParsedScenario> {
    return this.http.post<ParsedScenario>(`${this.base}/scenario/parse/`, { query });
  }

  getAirTables(peril: string, scenarioText: string, zoneFilter: string): Observable<AirTablesResponse> {
    let params = new HttpParams()
      .set('peril', peril)
      .set('scenario_text', scenarioText)
      .set('zone_filter', zoneFilter);
    return this.http.get<AirTablesResponse>(`${this.base}/scenario/air-tables/`, { params });
  }

  getAirDescriptions(peril: string, zoneFilter: string, tableSchema: string, tableName: string): Observable<AirDescriptionsResponse> {
    let params = new HttpParams()
      .set('peril', peril)
      .set('zone_filter', zoneFilter)
      .set('table_schema', tableSchema)
      .set('table_name', tableName);
    return this.http.get<AirDescriptionsResponse>(`${this.base}/scenario/air-descriptions/`, { params });
  }

  searchEvents(body: {
    peril: string;
    zone_filter: string;
    loss_lo: number;
    loss_hi: number;
    filter_mode: string;
    event_keyword: string;
    air_enrichment?: {
      enabled: boolean;
      table_schema: string;
      table_name: string;
      mag_lo: number;
      mag_hi: number;
    };
  }): Observable<SearchEventsResponse> {
    return this.http.post<SearchEventsResponse>(`${this.base}/scenario/search-events/`, body);
  }

  analyze(lowEventId: number, medEventId: number, highEventId: number): Observable<AnalyzeResponse> {
    return this.http.post<AnalyzeResponse>(`${this.base}/scenario/analyze/`, {
      low_event_id: lowEventId,
      med_event_id: medEventId,
      high_event_id: highEventId,
    });
  }

  previewSql(body: Record<string, unknown>): Observable<{ sql: string }> {
    return this.http.post<{ sql: string }>(`${this.base}/scenario/preview-sql/`, body);
  }

  listSavedScenarios(): Observable<SavedScenario[]> {
    return this.http.get<SavedScenario[]>(`${this.base}/scenario/saved/`);
  }

  saveScenario(scenario: Omit<SavedScenario, 'id' | 'created_at' | 'updated_at'>): Observable<SavedScenario> {
    return this.http.post<SavedScenario>(`${this.base}/scenario/saved/`, scenario);
  }

  deleteSavedScenario(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/scenario/saved/${id}/`);
  }

  getModelInfo(): Observable<ModelInfoResponse> {
    return this.http.get<ModelInfoResponse>(`${this.base}/scenario/model-info/`);
  }
}
