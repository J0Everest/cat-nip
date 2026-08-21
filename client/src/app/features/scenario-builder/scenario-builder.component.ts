import { Component, inject, signal, computed, OnInit, OnDestroy } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Subscription } from 'rxjs';
import { ScenarioApiService } from '../../core/services/scenario-api.service';
import { DatabaseConfigService } from '../../core/services/database-config.service';
import { ParsedScenario, AirTableProfile } from '../../core/models/scenario.models';
import { CandidateEvent, AnalyzeResponse, SavedScenario } from '../../core/models/event.models';
import { MatExpansionModule } from '@angular/material/expansion';
import { StepIndicatorComponent } from './components/step-indicator/step-indicator.component';
import { PromptHeroComponent } from './components/prompt-hero/prompt-hero.component';
import { ParsedEventCardComponent } from './components/parsed-event-card/parsed-event-card.component';
import { RefineFiltersComponent } from './components/refine-filters/refine-filters.component';
import { CandidateEventsTableComponent } from './components/candidate-events-table/candidate-events-table.component';
import { ScenarioAssignmentComponent } from './components/scenario-assignment/scenario-assignment.component';
import { ResultsDashboardComponent } from './components/results-dashboard/results-dashboard.component';
import { SaveScenarioDialogComponent } from './components/save-scenario-dialog/save-scenario-dialog.component';

export interface RefineState {
  peril: string;
  zone: string;
  lossLo: number;
  lossHi: number;
  filterMode: string;
  eventKeywords: string[];
  useAir: boolean;
  airTableSchema: string;
  airTableName: string;
  magLo: number;
  magHi: number;
}

@Component({
  selector: 'app-scenario-builder',
  imports: [
    MatExpansionModule, StepIndicatorComponent, PromptHeroComponent, ParsedEventCardComponent,
    RefineFiltersComponent, CandidateEventsTableComponent,
    ScenarioAssignmentComponent, ResultsDashboardComponent,
  ],
  template: `
    <app-step-indicator [steps]="steps" [currentIndex]="currentStep()" />

    <app-prompt-hero (analyze)="onAnalyzeQuery($event)" [loading]="parseLoading()" />

    @if (parsed()) {
      <app-parsed-event-card [parsed]="parsed()!" [rawQuery]="rawQuery()" />

      <app-refine-filters
        [parsed]="parsed()!"
        [airTables]="airTables()"
        [airDescriptions]="airDescriptions()"
        [recommendedTable]="recommendedTable()"
        [autoExpand]="shouldAutoExpand()"
        (filtersChanged)="onFiltersChanged($event)"
        (searchEvents)="onSearchEvents()" />
    }

    @if (candidates().length > 0) {
      <mat-expansion-panel class="candidates-panel" [expanded]="false">
        <mat-expansion-panel-header>
          <mat-panel-title>Candidate Events</mat-panel-title>
          <mat-panel-description>{{ candidates().length }} event{{ candidates().length !== 1 ? 's' : '' }} found — expand to review or change selection</mat-panel-description>
        </mat-expansion-panel-header>
        <app-candidate-events-table
          [events]="candidates()"
          [loading]="searchLoading()"
          (eventsSelected)="onEventsSelected($event)" />
      </mat-expansion-panel>

      <app-scenario-assignment
        [events]="selectedEvents().length ? selectedEvents() : candidates()"
        (runAnalysis)="onRunAnalysis($event)"
        (saveScenario)="onSaveScenario($event)" />
    }

    @if (analyzeResult()) {
      <app-results-dashboard
        [result]="analyzeResult()!"
        [generatedSql]="generatedSql()" />
    }

    @if (errorMsg()) {
      <div class="error-banner">{{ errorMsg() }}</div>
    }
  `,
  styles: [`
    :host { display: block; max-width: 1200px; margin: 0 auto; padding-bottom: 48px; }
    .candidates-panel { margin: 24px 0 0; }
    ::ng-deep .candidates-panel .mat-expansion-panel-header-description { color: #A4ABC8; font-size: 0.82rem; }
    .error-banner {
      background: #F8D7DA;
      color: #DA1E28;
      padding: 12px 16px;
      border-radius: 8px;
      margin-top: 16px;
      font-size: 0.88rem;
    }
  `],
})
export class ScenarioBuilderComponent implements OnInit, OnDestroy {
  private readonly api = inject(ScenarioApiService);
  private readonly dbConfig = inject(DatabaseConfigService);
  private readonly dialog = inject(MatDialog);
  private loadSub?: Subscription;

  readonly steps = ['Describe Event', 'Refine Filters', 'Select Events', 'Assign Scenarios', 'View Results'];

  readonly parsed = signal<ParsedScenario | null>(null);
  readonly rawQuery = signal('');
  readonly parseLoading = signal(false);

  readonly airTables = signal<AirTableProfile[]>([]);
  readonly airDescriptions = signal<string[]>([]);
  readonly recommendedTable = signal<string | null>(null);
  readonly refineState = signal<RefineState | null>(null);

  readonly candidates = signal<CandidateEvent[]>([]);
  readonly selectedEvents = signal<CandidateEvent[]>([]);
  readonly searchLoading = signal(false);

  readonly analyzeResult = signal<AnalyzeResponse | null>(null);
  readonly generatedSql = signal('');

  readonly errorMsg = signal('');

  private lastAirTablesKey = '';
  private lastDescriptionsKey = '';

  readonly currentStep = computed(() => {
    if (this.analyzeResult()) return 4;
    if (this.selectedEvents().length > 0) return 3;
    if (this.candidates().length > 0) return 2;
    if (this.parsed()) return 1;
    return 0;
  });

  readonly shouldAutoExpand = computed(() => {
    const p = this.parsed();
    return p?.confidence === 'needs_refinement';
  });

  onAnalyzeQuery(query: string): void {
    this.parseLoading.set(true);
    this.errorMsg.set('');
    this.candidates.set([]);
    this.analyzeResult.set(null);
    this.lastAirTablesKey = '';
    this.lastDescriptionsKey = '';

    this.api.parseQuery(query).subscribe({
      next: (parsed) => {
        this.parsed.set(parsed);
        this.rawQuery.set(query);
        this.parseLoading.set(false);
        if (parsed.peril && parsed.peril !== 'All') {
          this.loadAirTables(parsed.peril, parsed.zone ?? '', query);
        }
      },
      error: (err) => {
        this.errorMsg.set(err?.error?.detail ?? 'Failed to parse query');
        this.parseLoading.set(false);
      },
    });
  }

  private loadAirTables(peril: string, zone: string, scenarioText: string): void {
    const key = `${peril}|${zone}`;
    if (key === this.lastAirTablesKey) return;
    this.lastAirTablesKey = key;
    this.api.getAirTables(peril, scenarioText, zone).subscribe({
      next: (res) => {
        this.airTables.set(res.tables);
        this.recommendedTable.set(res.recommended_table);
      },
    });
  }

  onFiltersChanged(state: RefineState): void {
    this.refineState.set(state);
    if (state.peril && state.peril !== this.parsed()?.peril) {
      this.loadAirTables(state.peril, state.zone, this.rawQuery());
    }
    if (state.airTableSchema && state.airTableName) {
      const descKey = `${state.peril}|${state.zone}|${state.airTableSchema}|${state.airTableName}`;
      if (descKey !== this.lastDescriptionsKey) {
        this.lastDescriptionsKey = descKey;
        this.api.getAirDescriptions(state.peril, state.zone, state.airTableSchema, state.airTableName).subscribe({
          next: (res) => this.airDescriptions.set(res.descriptions),
        });
      }
    }
  }

  onSearchEvents(): void {
    const s = this.refineState();
    const p = this.parsed();
    if (!s && !p) return;

    this.searchLoading.set(true);
    this.errorMsg.set('');
    this.analyzeResult.set(null);

    const peril = s?.peril ?? p?.peril ?? 'All';
    const zone = s?.zone ?? p?.zone ?? '';
    const lossLo = s?.lossLo ?? p?.loss_lo ?? 0;
    const lossHi = s?.lossHi ?? p?.loss_hi ?? 300;

    const body: Parameters<ScenarioApiService['searchEvents']>[0] = {
      peril,
      zone_filter: zone,
      loss_lo: lossLo,
      loss_hi: lossHi,
      filter_mode: s?.filterMode ?? 'Both',
      event_keywords: s?.eventKeywords ?? (p?.event_keyword ? [p.event_keyword] : []),
    };

    if (s?.airTableSchema && s.airTableName) {
      body.air_enrichment = {
        enabled: true,
        table_schema: s.airTableSchema,
        table_name: s.airTableName,
        mag_lo: s.magLo,
        mag_hi: s.magHi,
      };
    }

    this.api.searchEvents(body).subscribe({
      next: (res) => {
        const events = res.events.map(e => ({ ...e, selected: false }));
        this.candidates.set(events);
        this.searchLoading.set(false);
        if (events.length > 0) {
          this.onRunAnalysis(this.autoSelectIds(events));
        }
      },
      error: (err) => {
        this.errorMsg.set(err?.error?.error ?? 'Search failed');
        this.searchLoading.set(false);
      },
    });
  }

  private autoSelectIds(events: CandidateEvent[]): { low: number; med: number; high: number } {
    const sorted = [...events].sort((a, b) => a.industry_loss_b - b.industry_loss_b);
    return {
      low: sorted[0]?.event_id ?? 0,
      med: sorted[Math.floor(sorted.length / 2)]?.event_id ?? 0,
      high: sorted[sorted.length - 1]?.event_id ?? 0,
    };
  }

  onEventsSelected(events: CandidateEvent[]): void {
    this.selectedEvents.set(events);
  }

  onRunAnalysis(ids: { low: number; med: number; high: number }): void {
    this.errorMsg.set('');
    this.api.analyze(ids.low, ids.med, ids.high).subscribe({
      next: (res) => {
        this.analyzeResult.set(res);
        this.generatedSql.set(res.generated_sql);
      },
      error: (err) => {
        this.errorMsg.set(err?.error?.error ?? 'Analysis failed');
      },
    });
  }

  ngOnInit(): void {
    this.loadSub = this.dbConfig.loadScenario$.subscribe(sc => this.onLoadScenario(sc));
  }

  ngOnDestroy(): void {
    this.loadSub?.unsubscribe();
  }

  onSaveScenario(ids: { low: number; med: number; high: number }): void {
    const dialogRef = this.dialog.open(SaveScenarioDialogComponent);
    dialogRef.afterClosed().subscribe((name: string | undefined) => {
      if (!name) return;
      const s = this.refineState();
      const p = this.parsed();
      this.api.saveScenario({
        name,
        query_text: this.rawQuery(),
        peril: s?.peril ?? p?.peril ?? '',
        zone: s?.zone ?? p?.zone ?? '',
        loss_lo: s?.lossLo ?? p?.loss_lo ?? 0,
        loss_hi: s?.lossHi ?? p?.loss_hi ?? 300,
        filter_mode: s?.filterMode ?? 'Industry Loss',
        event_keyword: (s?.eventKeywords ?? []).join('|') || p?.event_keyword || '',
        low_event_id: ids.low,
        med_event_id: ids.med,
        high_event_id: ids.high,
        database: this.dbConfig.database(),
        candidate_event_ids: this.candidates().map(e => e.event_id),
      }).subscribe({
        next: () => this.dbConfig.scenarioSaved$.next(),
      });
    });
  }

  private onLoadScenario(sc: SavedScenario): void {
    this.analyzeResult.set(null);
    this.candidates.set([]);
    this.selectedEvents.set([]);

    const parsed: ParsedScenario = {
      peril: sc.peril || null,
      zone: sc.zone || null,
      model_no: null,
      loss_lo: sc.loss_lo,
      loss_hi: sc.loss_hi,
      mag_lo: null,
      mag_hi: null,
      event_keyword: sc.event_keyword || '',
      confidence: 'partial',
      confidence_parts: 0,
      confidence_total: 0,
    };
    this.parsed.set(parsed);
    this.rawQuery.set(sc.query_text);

    if (sc.peril && sc.peril !== 'All') {
      this.loadAirTables(sc.peril, sc.zone, sc.query_text);
    }
  }
}
