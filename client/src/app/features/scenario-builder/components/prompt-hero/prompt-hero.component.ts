import { Component, Output, EventEmitter, Input } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

@Component({
  selector: 'app-prompt-hero',
  imports: [FormsModule, MatFormFieldModule, MatInputModule, MatButtonModule, MatIconModule, MatProgressSpinnerModule],
  template: `
    <div class="prompt-hero">
      <div class="hero-title-row">
        <mat-icon class="hero-icon">auto_awesome</mat-icon>
        <h2>What catastrophe event would you like to analyze?</h2>
      </div>
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

    @if (!query.trim()) {
      <div class="suggestions">
        <span class="suggestions-label">Try an example:</span>
        @for (s of suggestions; track s) {
          <button class="suggestion-chip" (click)="useSuggestion(s)">{{ s }}</button>
        }
      </div>
    }
  `,
  styles: [`
    .prompt-hero {
      background: linear-gradient(135deg, #061C49 0%, #0A3699 80%, #235CF4 100%);
      border-radius: 16px;
      padding: 36px 40px 28px;
      margin-bottom: 20px;
      color: #fff;
    }
    .hero-title-row { display: flex; align-items: center; gap: 10px; }
    .hero-icon { font-size: 24px; width: 24px; height: 24px; color: #A4ABC8; }
    .prompt-hero h2 { font-weight: 700; margin: 0 0 4px; font-size: 1.35rem; }
    .prompt-hero p { color: #A4ABC8; font-size: 0.88rem; margin: 0; }
    .prompt-row { display: flex; gap: 12px; align-items: flex-start; margin-bottom: 4px; }
    .prompt-field { flex: 1; }
    .analyze-btn { height: 56px; min-width: 100px; }

    .suggestions { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 20px; }
    .suggestions-label { font-size: 0.78rem; color: #A4ABC8; font-weight: 500; }
    .suggestion-chip {
      background: #EBF0FE;
      color: #0A3699;
      border: 1px solid #D0DBFC;
      border-radius: 20px;
      padding: 6px 16px;
      font-size: 0.78rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s;
      font-family: inherit;
    }
    .suggestion-chip:hover {
      background: #235CF4;
      color: #fff;
      border-color: #235CF4;
    }
  `],
})
export class PromptHeroComponent {
  @Input() loading = false;
  @Output() analyze = new EventEmitter<string>();

  query = '';

  readonly suggestions = [
    'Category 5 hurricane near Miami',
    'Repeat of the 1906 San Francisco earthquake',
    'Major California wildfire impacting Los Angeles',
    'Northeast winter storm, $5-20B industry loss',
    'Caribbean earthquake magnitude 7-8',
    'Southeast severe storm season',
  ];

  useSuggestion(text: string): void {
    this.query = text;
    this.analyze.emit(text);
  }

  onSubmit(event?: Event): void {
    event?.preventDefault();
    if (this.query.trim()) {
      this.analyze.emit(this.query.trim());
    }
  }
}
