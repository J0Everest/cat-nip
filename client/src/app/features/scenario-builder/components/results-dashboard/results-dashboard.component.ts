import { Component, Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { AnalyzeResponse, ScenarioSummary } from '../../../../core/models/event.models';
import { ScenarioSummaryCardsComponent } from './scenario-summary-cards/scenario-summary-cards.component';
import { ScenarioComparisonChartComponent } from './scenario-comparison-chart/scenario-comparison-chart.component';
import { LossByContractTableComponent } from './loss-by-contract-table/loss-by-contract-table.component';
import { FullOutputDetailComponent } from './full-output-detail/full-output-detail.component';

@Component({
  selector: 'app-results-dashboard',
  imports: [
    MatCardModule, MatExpansionModule, MatIconModule,
    ScenarioSummaryCardsComponent, ScenarioComparisonChartComponent,
    LossByContractTableComponent, FullOutputDetailComponent,
  ],
  template: `
    <hr class="divider">
    <div class="section-title">Portfolio Impact Dashboard</div>

    @if (narrative) {
      <div class="narrative">
        <mat-icon class="narrative-icon">summarize</mat-icon>
        <span [innerHTML]="narrative"></span>
      </div>
    }

    <app-scenario-summary-cards [summaries]="result.summary" />

    <div class="section-title">Scenario Comparison</div>
    <app-scenario-comparison-chart [summaries]="result.summary" />

    <div class="section-title">Loss by Contract <span class="subtitle">Gross &amp; Net of Logan — Low / Med / High</span></div>
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
    .narrative {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      background: #EBF0FE;
      border-left: 4px solid #235CF4;
      border-radius: 0 8px 8px 0;
      padding: 16px 20px;
      margin: 12px 0 20px;
      font-size: 0.9rem;
      line-height: 1.6;
      color: #061C49;
    }
    .narrative-icon { color: #235CF4; font-size: 20px; width: 20px; height: 20px; margin-top: 2px; flex-shrink: 0; }
    .sql-panel { margin-top: 16px; }
    .sql-code { font-size: 0.82rem; white-space: pre-wrap; word-break: break-all; }
  `],
})
export class ResultsDashboardComponent {
  @Input() result!: AnalyzeResponse;
  @Input() generatedSql = '';

  get narrative(): string {
    if (!this.result?.summary?.length) return '';

    const high = this.result.summary.find(s => s.scenario === 'High');
    const low = this.result.summary.find(s => s.scenario === 'Low');
    const totalContracts = high?.contracts ?? this.result.summary[0]?.contracts ?? 0;

    if (!high) return '';

    const parts: string[] = [];
    parts.push(`A <strong>high-severity</strong> scenario would generate <strong>$${high.gross_loss_m.toFixed(1)}M</strong> gross loss`);
    parts.push(`across <strong>${high.contracts}</strong> contract${high.contracts !== 1 ? 's' : ''}`);
    parts.push(`representing a <strong>${high.market_share_pct.toFixed(2)}%</strong> market share`);
    parts.push(`of the <strong>$${high.industry_loss_b.toFixed(1)}B</strong> industry loss.`);

    let sentence = parts.join(', ') + ' ';

    if (low) {
      const spread = high.gross_loss_m - low.gross_loss_m;
      sentence += `The low-to-high spread is <strong>$${spread.toFixed(1)}M</strong>.`;
    }

    return sentence;
  }
}
