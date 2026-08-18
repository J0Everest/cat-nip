import { Component, Output, EventEmitter, Input } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

@Component({
  selector: 'app-prompt-hero',
  imports: [FormsModule, MatFormFieldModule, MatInputModule, MatButtonModule, MatProgressSpinnerModule],
  template: `
    <div class="prompt-hero">
      <h2>What catastrophe event would you like to analyze?</h2>
      <p>Describe a natural disaster scenario and CAT-NIP will find matching events and estimate portfolio impact.</p>
    </div>
    <div class="prompt-row">
      <mat-form-field appearance="outline" class="prompt-field">
        <textarea matInput
          [(ngModel)]="query"
          rows="3"
          placeholder='e.g. "Category 5 hurricane makes landfall near Miami, $5-15B industry loss"'
          (keydown.enter)="onSubmit($event)">
        </textarea>
      </mat-form-field>
      <button mat-flat-button color="primary" class="analyze-btn" [disabled]="loading || !query.trim()" (click)="onSubmit()">
        @if (loading) {
          <mat-spinner diameter="20" />
        } @else {
          Analyze
        }
      </button>
    </div>
  `,
  styles: [`
    .prompt-hero {
      background: linear-gradient(135deg, #061C49 0%, #0A3699 100%);
      border-radius: 16px;
      padding: 32px 36px 24px;
      margin-bottom: 20px;
      color: #fff;
    }
    .prompt-hero h2 { font-weight: 700; margin: 0 0 4px; font-size: 1.35rem; }
    .prompt-hero p { color: #A4ABC8; font-size: 0.88rem; margin: 0; }
    .prompt-row { display: flex; gap: 12px; align-items: flex-start; margin-bottom: 16px; }
    .prompt-field { flex: 1; }
    .analyze-btn { height: 56px; min-width: 100px; }
  `],
})
export class PromptHeroComponent {
  @Input() loading = false;
  @Output() analyze = new EventEmitter<string>();

  query = '';

  onSubmit(event?: Event): void {
    event?.preventDefault();
    if (this.query.trim()) {
      this.analyze.emit(this.query.trim());
    }
  }
}
