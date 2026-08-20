import { Component, Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { ParsedScenario } from '../../../../core/models/scenario.models';

@Component({
  selector: 'app-parsed-event-card',
  imports: [MatCardModule, MatChipsModule],
  template: `
    <mat-card class="parsed-card">
      <div class="card-header">
        <span class="card-title">Parsed Event</span>
        <span class="catnip-badge" [class]="badgeClass">{{ badgeText }}</span>
      </div>
      <p class="raw-query">&ldquo;{{ rawQuery }}&rdquo;</p>
      <div class="pills">
        <span [class]="parsed.peril ? 'catnip-pill' : 'catnip-pill catnip-pill-muted'">
          <strong>Peril:</strong> {{ parsed.peril ?? 'Not detected' }}
        </span>
        <span [class]="parsed.zone ? 'catnip-pill' : 'catnip-pill catnip-pill-muted'">
          <strong>Region:</strong> {{ parsed.zone ?? 'Not detected' }}
        </span>
        @if (parsed.loss_lo !== null && parsed.loss_hi !== null) {
          <span class="catnip-pill">
            <strong>Industry Loss:</strong> {{ '$' + parsed.loss_lo }}B &ndash; {{ '$' + parsed.loss_hi }}B
          </span>
        } @else {
          <span class="catnip-pill catnip-pill-muted"><strong>Industry Loss:</strong> Full range</span>
        }
        @if (parsed.event_keyword) {
          <span class="catnip-pill"><strong>Keyword:</strong> {{ parsed.event_keyword }}</span>
        }
        @if (parsed.mag_lo !== null && parsed.mag_hi !== null) {
          <span class="catnip-pill"><strong>Magnitude:</strong> {{ parsed.mag_lo }} &ndash; {{ parsed.mag_hi }}</span>
        }
        @if (parsed.model_no) {
          <span class="catnip-pill"><strong>Model #:</strong> {{ parsed.model_no }}</span>
        }
      </div>
    </mat-card>
  `,
  styles: [`
    .parsed-card {
      border-left: 4px solid #235CF4;
      margin-bottom: 16px;
      padding: 20px 24px;
    }
    .card-header {
      display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;
    }
    .card-title { font-weight: 700; color: #061C49; font-size: 0.95rem; }
    .raw-query { color: #A4ABC8; font-size: 0.82rem; font-style: italic; margin-bottom: 8px; }
    .pills { display: flex; flex-wrap: wrap; gap: 4px; }
  `],
})
export class ParsedEventCardComponent {
  @Input() parsed!: ParsedScenario;
  @Input() rawQuery = '';

  get badgeClass(): string {
    const map: Record<string, string> = { high: 'catnip-badge-high', partial: 'catnip-badge-med', needs_refinement: 'catnip-badge-low' };
    return map[this.parsed.confidence] ?? 'catnip-badge-med';
  }

  get badgeText(): string {
    const map: Record<string, string> = { high: 'HIGH CONFIDENCE', partial: 'PARTIAL MATCH', needs_refinement: 'NEEDS REFINEMENT' };
    return map[this.parsed.confidence] ?? 'PARTIAL MATCH';
  }
}
