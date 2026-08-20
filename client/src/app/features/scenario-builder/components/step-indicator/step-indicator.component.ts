import { Component, Input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-step-indicator',
  imports: [MatIconModule],
  template: `
    <div class="step-header">
      <div class="step-bar">
        @for (step of steps; track step; let i = $index) {
          <div class="step-item" [class.active]="i === currentIndex" [class.done]="i < currentIndex" [class.first]="i === 0">
            <span class="step-num">
              @if (i < currentIndex) {
                <mat-icon class="check-icon">check</mat-icon>
              } @else {
                {{ i + 1 }}
              }
            </span>
            {{ step }}
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    .step-header {
      position: sticky;
      top: 0;
      z-index: 100;
      background: #F5F5F5;
      margin: -24px -32px 16px;
      padding: 12px 32px 0;
      box-shadow: 0 2px 4px rgba(0,0,0,0.06);
    }
    .step-bar { display: flex; gap: 0; }
    .step-item {
      flex: 1; text-align: center; padding: 10px 6px;
      font-size: 0.75rem; font-weight: 600;
      border-bottom: 3px solid #E2E8F0; color: #A4ABC8;
      transition: all 0.2s; cursor: default;
      position: relative;
    }
    .step-item::before {
      content: '';
      position: absolute;
      top: 50%;
      left: 0;
      right: 50%;
      height: 2px;
      background: #E2E8F0;
      transform: translateY(-50%);
      z-index: -1;
    }
    .step-item.first::before { display: none; }
    .step-item.done::before { background: #198038; }
    .step-item.active::before { background: #235CF4; }
    .step-num {
      display: inline-flex; align-items: center; justify-content: center;
      width: 22px; height: 22px; border-radius: 50%;
      background: #E2E8F0; color: #A4ABC8;
      font-size: 0.65rem; font-weight: 700;
      margin-right: 6px; vertical-align: middle;
    }
    .check-icon { font-size: 14px; width: 14px; height: 14px; }
    .step-item.active { border-bottom-color: #235CF4; color: #235CF4; }
    .step-item.active .step-num { background: #235CF4; color: #fff; }
    .step-item.done { border-bottom-color: #198038; color: #198038; }
    .step-item.done .step-num { background: #198038; color: #fff; }
  `],
})
export class StepIndicatorComponent {
  @Input() steps: string[] = [];
  @Input() currentIndex = 0;
}
