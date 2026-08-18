import { Component, Input } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { ScenarioSummary } from '../../../../../core/models/event.models';
import { DESIGN_TOKENS } from '../../../../../shared/theme/design-tokens';

@Component({
  selector: 'app-scenario-summary-cards',
  imports: [DecimalPipe, MatCardModule],
  template: `
    <div class="cards-row">
      @for (s of summaries; track s.scenario) {
        <div class="scenario-card" [style.border-top-color]="colorFor(s.scenario)">
          <div class="scenario-label" [style.color]="colorFor(s.scenario)">{{ s.scenario }} Scenario</div>
          <div class="scenario-value">\${{ s.gross_loss_m | number:'1.1-1' }}M</div>
          <div class="scenario-detail">Gross Loss</div>
          <hr>
          <div class="stats-row">
            <div><strong>{{ s.contracts }}</strong><br><span class="stat-label">Contracts</span></div>
            <div><strong>{{ s.market_share_pct | number:'1.2-2' }}%</strong><br><span class="stat-label">Mkt Share</span></div>
            <div><strong>\${{ s.industry_loss_b | number:'1.1-1' }}B</strong><br><span class="stat-label">Industry</span></div>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .cards-row { display: flex; gap: 16px; margin: 16px 0; }
    .scenario-card {
      flex: 1; background: #fff; border: 2px solid #E2E8F0; border-radius: 12px;
      padding: 18px; text-align: center; border-top-width: 4px;
      transition: box-shadow 0.15s;
    }
    .scenario-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .scenario-label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 700; margin-bottom: 6px; }
    .scenario-value { font-size: 1.4rem; font-weight: 700; color: #061C49; margin-bottom: 2px; }
    .scenario-detail { font-size: 0.78rem; color: #A4ABC8; }
    hr { margin: 8px 0; border-color: #E2E8F0; }
    .stats-row { display: flex; justify-content: space-around; font-size: 0.78rem; }
    .stat-label { color: #A4ABC8; }
  `],
})
export class ScenarioSummaryCardsComponent {
  @Input() summaries: ScenarioSummary[] = [];

  colorFor(scenario: string): string {
    return DESIGN_TOKENS.scenarioColors[scenario] ?? DESIGN_TOKENS.everestBlue;
  }
}
