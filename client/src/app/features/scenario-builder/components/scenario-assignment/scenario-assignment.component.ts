import { Component, Input, Output, EventEmitter, OnChanges } from '@angular/core';
import { SlicePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { CandidateEvent } from '../../../../core/models/event.models';
import { DESIGN_TOKENS } from '../../../../shared/theme/design-tokens';

@Component({
  selector: 'app-scenario-assignment',
  imports: [SlicePipe, FormsModule, MatFormFieldModule, MatSelectModule, MatInputModule, MatButtonModule, MatIconModule],
  template: `
    <div class="section-title">Assign Scenarios <span class="subtitle">Select Low, Medium, and High severity events</span></div>

    <div class="scenario-row">
      @for (sc of scenarios; track sc.key) {
        <div class="scenario-card" [style.border-top-color]="sc.color">
          <div class="scenario-label" [style.color]="sc.color">{{ sc.label }} SCENARIO</div>
          <mat-form-field appearance="outline" class="scenario-field">
            <mat-label>Event ID</mat-label>
            <mat-select [(ngModel)]="sc.selectedId">
              <mat-option [value]="0">(none)</mat-option>
              @for (e of events; track e.event_id) {
                <mat-option [value]="e.event_id">{{ e.event_id }} &mdash; {{ e.description | slice:0:40 }}</mat-option>
              }
            </mat-select>
          </mat-form-field>
          @if (sc.selectedId === 0) {
            <mat-form-field appearance="outline" class="scenario-field">
              <mat-label>Manual Event ID</mat-label>
              <input matInput type="number" [(ngModel)]="sc.manualId" min="0">
            </mat-form-field>
          }
        </div>
      }
    </div>

    <div class="action-row">
      <button mat-flat-button color="primary" class="analyze-btn" (click)="onRun()">
        Analyze Portfolio Impact
      </button>
      <button mat-stroked-button color="primary" class="save-btn" (click)="onSave()">
        <mat-icon>bookmark_border</mat-icon> Save Scenario
      </button>
    </div>
  `,
  styles: [`
    .section-title {
      font-size: 1.05rem; font-weight: 700; color: #061C49;
      border-bottom: 2px solid #235CF4; padding-bottom: 6px; margin: 24px 0 12px;
    }
    .subtitle { font-weight: 400; color: #A4ABC8; font-size: 0.85rem; margin-left: 12px; }
    .scenario-row { display: flex; gap: 16px; margin: 16px 0; }
    .scenario-card {
      flex: 1; background: #fff; border: 2px solid #E2E8F0; border-radius: 12px;
      padding: 18px; text-align: center; border-top-width: 4px;
    }
    .scenario-label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 700; margin-bottom: 12px; }
    .scenario-field { width: 100%; }
    .action-row { display: flex; gap: 12px; margin: 16px 0; }
    .analyze-btn { flex: 1; height: 48px; font-size: 1rem; }
    .save-btn { height: 48px; font-size: 0.9rem; }
  `],
})
export class ScenarioAssignmentComponent implements OnChanges {
  @Input() events: CandidateEvent[] = [];
  @Output() runAnalysis = new EventEmitter<{ low: number; med: number; high: number }>();
  @Output() saveScenario = new EventEmitter<{ low: number; med: number; high: number }>();

  scenarios = [
    { key: 'low', label: 'LOW', color: DESIGN_TOKENS.scenarioColors['Low'], selectedId: 0, manualId: 0 },
    { key: 'med', label: 'MEDIUM', color: DESIGN_TOKENS.scenarioColors['Med'], selectedId: 0, manualId: 0 },
    { key: 'high', label: 'HIGH', color: DESIGN_TOKENS.scenarioColors['High'], selectedId: 0, manualId: 0 },
  ];

  ngOnChanges(): void {
    if (this.events.length > 0) {
      const sorted = [...this.events].sort((a, b) => a.industry_loss_b - b.industry_loss_b);
      this.scenarios[0].selectedId = sorted[0]?.event_id ?? 0;
      this.scenarios[1].selectedId = sorted[Math.floor(sorted.length / 2)]?.event_id ?? 0;
      this.scenarios[2].selectedId = sorted[sorted.length - 1]?.event_id ?? 0;
    }
  }

  onRun(): void {
    this.runAnalysis.emit({
      low: this.scenarios[0].selectedId || this.scenarios[0].manualId,
      med: this.scenarios[1].selectedId || this.scenarios[1].manualId,
      high: this.scenarios[2].selectedId || this.scenarios[2].manualId,
    });
  }

  onSave(): void {
    this.saveScenario.emit({
      low: this.scenarios[0].selectedId || this.scenarios[0].manualId,
      med: this.scenarios[1].selectedId || this.scenarios[1].manualId,
      high: this.scenarios[2].selectedId || this.scenarios[2].manualId,
    });
  }
}
