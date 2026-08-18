import { Component, Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatExpansionModule } from '@angular/material/expansion';
import { AnalyzeResponse } from '../../../../core/models/event.models';
import { ScenarioSummaryCardsComponent } from './scenario-summary-cards/scenario-summary-cards.component';
import { ScenarioComparisonChartComponent } from './scenario-comparison-chart/scenario-comparison-chart.component';
import { LossByContractTableComponent } from './loss-by-contract-table/loss-by-contract-table.component';
import { FullOutputDetailComponent } from './full-output-detail/full-output-detail.component';

@Component({
  selector: 'app-results-dashboard',
  imports: [
    MatCardModule, MatExpansionModule,
    ScenarioSummaryCardsComponent, ScenarioComparisonChartComponent,
    LossByContractTableComponent, FullOutputDetailComponent,
  ],
  template: `
    <hr class="divider">
    <div class="section-title">Portfolio Impact Dashboard</div>

    <app-scenario-summary-cards [summaries]="result.summary" />

    <div class="section-title">Scenario Comparison</div>
    <app-scenario-comparison-chart [summaries]="result.summary" />

    <div class="section-title">Loss by Contract <span class="subtitle">Low / Med / High</span></div>
    <app-loss-by-contract-table [contracts]="result.contracts" />

    <mat-expansion-panel>
      <mat-expansion-panel-header>
        <mat-panel-title>Full Output Detail</mat-panel-title>
      </mat-expansion-panel-header>
      <app-full-output-detail [detail]="result.detail" />
    </mat-expansion-panel>

    @if (generatedSql) {
      <mat-expansion-panel class="sql-panel">
        <mat-expansion-panel-header>
          <mat-panel-title>Generated SQL</mat-panel-title>
        </mat-expansion-panel-header>
        <pre class="sql-code">{{ generatedSql }}</pre>
      </mat-expansion-panel>
    }
  `,
  styles: [`
    .divider { border: none; border-top: 1px solid #E2E8F0; margin: 24px 0; }
    .section-title {
      font-size: 1.05rem; font-weight: 700; color: #061C49;
      border-bottom: 2px solid #235CF4; padding-bottom: 6px; margin: 24px 0 12px;
    }
    .subtitle { font-weight: 400; color: #A4ABC8; font-size: 0.85rem; margin-left: 12px; }
    .sql-panel { margin-top: 16px; }
    .sql-code { font-size: 0.82rem; white-space: pre-wrap; word-break: break-all; }
  `],
})
export class ResultsDashboardComponent {
  @Input() result!: AnalyzeResponse;
  @Input() generatedSql = '';
}
